"""Generate leakage-safe labelled SkyGuard fault datasets."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.faults.injector import LABEL_FIELDS, FaultInjector  # noqa: E402
from skyguard.faults.models import Episode, FAULT_TYPES  # noqa: E402


SOURCE = ROOT / "data" / "processed" / "aws_observations_2022_2024.csv"
OUTPUT_DIR = ROOT / "data" / "labelled"
EPISODES_FILE = OUTPUT_DIR / "episodes.csv"
MANIFEST_FILE = OUTPUT_DIR / "manifest.csv"
REPORT_JSON = ROOT / "reports" / "fault_injection.json"
REPORT_MD = ROOT / "reports" / "fault_injection.md"
GLOBAL_SEED = 26073

SPLITS = (
    {"name": "train", "year": "2022", "role": "development", "episodes_per_fault": 15, "weather_events": 5, "seed": GLOBAL_SEED + 101},
    {"name": "validation", "year": "2023", "role": "development", "episodes_per_fault": 10, "weather_events": 4, "seed": GLOBAL_SEED + 202},
    {"name": "time_test", "year": "2024", "role": "development", "episodes_per_fault": 12, "weather_events": 4, "seed": GLOBAL_SEED + 303},
    {"name": "station_test", "year": "2024", "role": "station_holdout", "episodes_per_fault": 5, "weather_events": 0, "seed": GLOBAL_SEED + 404},
)


def load_rows(year: str, role: str) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    with SOURCE.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        source_fields = list(reader.fieldnames or [])
        for row in reader:
            if row["year"] == year and row["evaluation_role"] == role:
                rows.append(row)
    return rows, source_fields


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_split(name: str, rows: list[dict[str, str]], source_fields: list[str]) -> Path:
    output = OUTPUT_DIR / f"{name}.csv"
    fields = source_fields + [field for field in LABEL_FIELDS if field not in source_fields]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return output


def write_episode_manifest(episodes: list[Episode]) -> None:
    fields = [
        "split", "episode_id", "label_category", "anomaly_type", "sensors", "stations",
        "start_utc", "end_utc", "severity", "affected_rows", "stream_action", "random_seed", "description",
    ]
    with EPISODES_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(episode.to_dict() for episode in episodes)


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard labelled fault dataset",
        "",
        f"- Global seed: {report['global_seed']}",
        f"- Output splits: {len(report['splits'])}",
        f"- Fault types: {len(FAULT_TYPES)}",
        f"- Total fault episodes: {report['total_fault_episodes']:,}",
        f"- Total genuine-weather scenarios: {report['total_weather_episodes']:,}",
        f"- Total labelled fault rows: {report['total_anomaly_rows']:,}",
        "",
        "## Split summary",
        "",
        "| Split | Rows | Fault episodes | Weather scenarios | Anomaly rows | Anomaly % |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, values in report["splits"].items():
        lines.append(
            f"| {name} | {values['rows']:,} | {values['fault_episodes']:,} | "
            f"{values['weather_episodes']:,} | {values['anomaly_rows']:,} | {values['anomaly_percent']:.4f}% |"
        )
    lines.extend(["", "## Fault episodes by type", "", "| Fault type | Episodes |", "|---|---:|"])
    for fault_type, count in report["episodes_by_type"].items():
        lines.append(f"| {fault_type} | {count:,} |")
    lines.extend([
        "",
        "## Label meaning",
        "",
        "- `is_anomaly=1`: synthetic sensor, record, timestamp, unit, or communication fault.",
        "- `is_weather_event=1`: coherent synthetic regional weather scenario and therefore a non-fault hard negative.",
        "- `stream_action=drop|duplicate|timestamp_shift`: instruction for the later replay engine.",
        "- Original values and timestamps are retained in dedicated columns for correction and audit.",
        "",
        "No generated episode crosses a split boundary. The station-holdout test contains only the four stations excluded from development.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    all_episodes: list[Episode] = []
    outputs: list[Path] = []
    split_reports: dict[str, dict[str, object]] = {}
    episodes_by_type: Counter[str] = Counter()

    for spec in SPLITS:
        rows, source_fields = load_rows(spec["year"], spec["role"])
        injector = FaultInjector(rows, spec["name"], spec["seed"])
        episodes = injector.inject_suite(spec["episodes_per_fault"], spec["weather_events"])
        output = write_split(spec["name"], rows, source_fields)
        outputs.append(output)
        all_episodes.extend(episodes)

        fault_episodes = [episode for episode in episodes if episode.label_category == "sensor_fault"]
        weather_episodes = [episode for episode in episodes if episode.label_category == "genuine_weather_scenario"]
        anomaly_rows = sum(row["is_anomaly"] == "1" for row in rows)
        weather_rows = sum(row["is_weather_event"] == "1" for row in rows)
        episodes_by_type.update(episode.anomaly_type for episode in fault_episodes)
        split_reports[spec["name"]] = {
            "year": spec["year"],
            "evaluation_role": spec["role"],
            "seed": spec["seed"],
            "rows": len(rows),
            "fault_episodes": len(fault_episodes),
            "weather_episodes": len(weather_episodes),
            "anomaly_rows": anomaly_rows,
            "anomaly_percent": round(100.0 * anomaly_rows / len(rows), 4),
            "weather_rows": weather_rows,
            "output": output.relative_to(ROOT).as_posix(),
        }
        print(f"{spec['name']}: {len(rows):,} rows, {len(fault_episodes)} faults, {len(weather_episodes)} weather scenarios")

    write_episode_manifest(all_episodes)
    outputs.append(EPISODES_FILE)
    with MANIFEST_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256", "global_seed"])
        writer.writeheader()
        for output in outputs:
            writer.writerow({
                "relative_path": output.relative_to(ROOT).as_posix(),
                "bytes": output.stat().st_size,
                "sha256": sha256(output),
                "global_seed": GLOBAL_SEED,
            })

    report = {
        "global_seed": GLOBAL_SEED,
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "splits": split_reports,
        "total_fault_episodes": sum(episode.label_category == "sensor_fault" for episode in all_episodes),
        "total_weather_episodes": sum(episode.label_category == "genuine_weather_scenario" for episode in all_episodes),
        "total_anomaly_rows": sum(values["anomaly_rows"] for values in split_reports.values()),
        "episodes_by_type": dict(sorted(episodes_by_type.items())),
        "episode_manifest": EPISODES_FILE.relative_to(ROOT).as_posix(),
        "checksum_manifest": MANIFEST_FILE.relative_to(ROOT).as_posix(),
        "generation_seconds": round(time.perf_counter() - started, 4),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

"""Package compact, deterministic Phase 7 replay scenarios from the benchmark."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data" / "features" / "time_test_features.csv.gz"
PREDICTIONS = ROOT / "data" / "predictions" / "time_test_phase5_predictions.csv.gz"
OUTPUT_DIR = ROOT / "data" / "demo"
MANIFEST = OUTPUT_DIR / "manifest.csv"
REPORT = ROOT / "reports" / "replay_scenarios.json"
OUTPUT_COLUMNS = [
    "row_id", "station_id", "timestamp_utc", "emitted_timestamp_utc", "cluster",
    "temperature_value", "pressure_value", "humidity_value", "stream_action", "available_to_detector",
    "is_anomaly", "is_weather_event", "anomaly_type", "episode_id", "fault_probability",
    "weather_probability", "event_decision", "root_cause_prediction",
    "packet_id",
]


def parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(PREDICTIONS, "rt", encoding="utf-8", newline="") as handle:
        predictions = {row["row_id"]: row for row in csv.DictReader(handle)}
    with gzip.open(FEATURES, "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        prediction = predictions.get(row["row_id"], {})
        for key in ("fault_probability", "weather_probability", "event_decision", "root_cause_prediction"):
            row[key] = prediction.get(key, "")
        row["packet_id"] = (
            "SIM-PACKET-" + row["episode_id"]
            if row.get("stream_action") == "duplicate" and row.get("episode_id")
            else "SIM-PACKET-" + row["row_id"]
        )

    definitions = {
        "pressure_drift": {
            "start": "2024-09-19T15:00:00Z", "end": "2024-09-23T09:00:00Z",
            "stations": None, "cluster": "delhi",
            "description": "Pressure drift at Station 42181099999 with causal neighbouring-station context.",
        },
        "regional_weather": {
            "start": "2024-07-17T15:00:00Z", "end": "2024-07-19T20:00:00Z",
            "stations": None, "cluster": "bengaluru",
            "description": "Coherent regional temperature event across four Bengaluru-cluster stations.",
        },
        "dropout": {
            "start": "2024-08-15T10:00:00Z", "end": "2024-08-16T19:00:00Z",
            "stations": {"43302599999"}, "cluster": None,
            "description": "Twenty-one-hour station dropout followed by a stateful communication-gap alert.",
        },
        "packet_errors": {
            "windows": [
                ("2024-02-18T08:30:00Z", "2024-02-18T12:00:00Z", {"42705699999"}),
                ("2024-03-11T14:00:00Z", "2024-03-11T17:00:00Z", {"42361099999"}),
            ],
            "description": "Repeated packets and an out-of-order emitted timestamp.",
        },
    }
    outputs: list[Path] = []
    scenario_report: dict[str, object] = {}
    for name, definition in definitions.items():
        selected: list[dict[str, str]] = []
        windows = definition.get("windows") or [(definition["start"], definition["end"], definition.get("stations"))]
        for start_text, end_text, station_filter in windows:
            start, end = parsed(start_text), parsed(end_text)
            for row in rows:
                timestamp = parsed(row["timestamp_utc"])
                if not start <= timestamp <= end:
                    continue
                if station_filter and row["station_id"] not in station_filter:
                    continue
                if definition.get("cluster") and row["cluster"].lower() != definition["cluster"]:
                    continue
                selected.append(row)
        selected.sort(key=lambda row: (row["timestamp_utc"], row["station_id"], row["row_id"]))
        output = OUTPUT_DIR / f"{name}.csv.gz"
        with gzip.open(output, "wt", encoding="utf-8", newline="", compresslevel=6) as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for row in selected:
                writer.writerow({column: row.get(column, "") for column in OUTPUT_COLUMNS})
        outputs.append(output)
        scenario_report[name] = {
            "description": definition["description"], "rows": len(selected),
            "stations": len({row["station_id"] for row in selected}),
            "fault_rows": sum(int(row["is_anomaly"]) for row in selected),
            "weather_rows": sum(int(row["is_weather_event"]) for row in selected),
            "file": output.relative_to(ROOT).as_posix(), "sha256": sha256(output),
        }

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
        writer.writeheader()
        for output in outputs:
            writer.writerow({"relative_path": output.relative_to(ROOT).as_posix(), "bytes": output.stat().st_size, "sha256": sha256(output)})
    REPORT.write_text(json.dumps({"status": "complete", "scenarios": scenario_report}, indent=2), encoding="utf-8")
    print(json.dumps(scenario_report, indent=2))


if __name__ == "__main__":
    main()

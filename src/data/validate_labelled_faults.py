"""Validate SkyGuard labelled split integrity and episode ground truth."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "stations.csv"
SOURCE = ROOT / "data" / "processed" / "aws_observations_2022_2024.csv"
LABELLED = ROOT / "data" / "labelled"
EPISODES = LABELLED / "episodes.csv"
MANIFEST = LABELLED / "manifest.csv"
REPORT_JSON = ROOT / "reports" / "labelled_validation.json"
REPORT_MD = ROOT / "reports" / "labelled_validation.md"

SPLITS = {
    "train": ("2022", "development"),
    "validation": ("2023", "development"),
    "time_test": ("2024", "development"),
    "station_test": ("2024", "station_holdout"),
}
FAULT_TYPES = {
    "spike", "sudden_drop", "bias", "drift", "noise", "frozen_sensor",
    "dropout", "duplicate_packet", "timestamp_error", "unit_error", "scaling_error",
    "communication_corruption", "multi_sensor_failure",
}
REQUIRED_COLUMNS = {
    "station_id", "timestamp_utc", "year", "evaluation_role", "temperature_c", "pressure_hpa",
    "relative_humidity_pct", "split", "label_category", "is_anomaly", "is_weather_event",
    "episode_id", "anomaly_type", "anomaly_sensor", "anomaly_severity", "label_source",
    "injection_seed", "stream_action", "timestamp_offset_seconds", "original_timestamp_utc",
    "original_temperature_c", "original_pressure_hpa", "original_relative_humidity_pct",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_source_counts() -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    with SOURCE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            counts[(row["year"], row["evaluation_role"])] += 1
    return counts


def validate() -> dict[str, object]:
    errors: list[str] = []
    manifest_rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline="")))
    for item in manifest_rows:
        path = ROOT / item["relative_path"]
        if not path.exists():
            errors.append(f"Missing generated file: {item['relative_path']}")
            continue
        if path.stat().st_size != int(item["bytes"]):
            errors.append(f"Size mismatch: {item['relative_path']}")
        if sha256(path) != item["sha256"]:
            errors.append(f"SHA-256 mismatch: {item['relative_path']}")

    episodes = list(csv.DictReader(EPISODES.open("r", encoding="utf-8", newline="")))
    episode_ids = [row["episode_id"] for row in episodes]
    if len(episode_ids) != len(set(episode_ids)):
        errors.append("Episode IDs are not globally unique.")
    unknown_faults = {
        row["anomaly_type"] for row in episodes
        if row["label_category"] == "sensor_fault" and row["anomaly_type"] not in FAULT_TYPES
    }
    if unknown_faults:
        errors.append(f"Unknown fault types: {sorted(unknown_faults)}")

    expected_counts = expected_source_counts()
    episode_row_counts: Counter[str] = Counter()
    split_summary: dict[str, dict[str, object]] = {}
    all_row_keys: dict[tuple[str, str], str] = {}

    with CONFIG.open("r", encoding="utf-8", newline="") as handle:
        holdouts = {row["station_id"] for row in csv.DictReader(handle) if row["evaluation_role"] == "station_holdout"}

    for split, (expected_year, expected_role) in SPLITS.items():
        path = LABELLED / f"{split}.csv"
        rows = 0
        anomalies = 0
        weather = 0
        by_type: Counter[str] = Counter()
        station_ids: set[str] = set()
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing_columns:
                errors.append(f"{split}: missing columns {sorted(missing_columns)}")
            for row in reader:
                rows += 1
                station_ids.add(row["station_id"])
                if row["split"] != split:
                    errors.append(f"{split}: row carries split {row['split']}")
                if row["year"] != expected_year or row["evaluation_role"] != expected_role:
                    errors.append(f"{split}: invalid year/role at {row['station_id']} {row['timestamp_utc']}")
                key = (row["station_id"], row["timestamp_utc"])
                prior_split = all_row_keys.get(key)
                if prior_split is not None:
                    errors.append(f"Row leakage between {prior_split} and {split}: {key}")
                all_row_keys[key] = split

                is_anomaly = row["is_anomaly"] == "1"
                is_weather = row["is_weather_event"] == "1"
                if is_anomaly and is_weather:
                    errors.append(f"{split}: row is both fault and weather event: {key}")
                if is_anomaly:
                    anomalies += 1
                    by_type[row["anomaly_type"]] += 1
                    if row["label_category"] != "sensor_fault" or not row["episode_id"]:
                        errors.append(f"{split}: incomplete fault label: {key}")
                    if not all(row[field] for field in ("original_temperature_c", "original_pressure_hpa", "original_relative_humidity_pct")):
                        errors.append(f"{split}: fault lacks original values: {key}")
                elif is_weather:
                    weather += 1
                    if row["label_category"] != "genuine_weather_scenario" or row["anomaly_type"] != "regional_temperature_event":
                        errors.append(f"{split}: invalid weather-scenario label: {key}")
                elif row["episode_id"] or row["label_category"] != "normal":
                    errors.append(f"{split}: normal row contains episode metadata: {key}")

                expected_action = {
                    "dropout": "drop",
                    "duplicate_packet": "duplicate",
                    "timestamp_error": "timestamp_shift",
                }.get(row["anomaly_type"], "emit")
                if row["stream_action"] != expected_action:
                    errors.append(f"{split}: incorrect stream action for {row['anomaly_type']}: {key}")
                if row["anomaly_type"] == "timestamp_error" and int(row["timestamp_offset_seconds"]) == 0:
                    errors.append(f"{split}: timestamp error has zero offset: {key}")
                if row["anomaly_type"] != "timestamp_error" and row["timestamp_offset_seconds"] != "0":
                    errors.append(f"{split}: non-timestamp fault changes timestamp offset: {key}")
                if row["original_timestamp_utc"] != row["timestamp_utc"]:
                    errors.append(f"{split}: source timestamp was not preserved: {key}")
                if row["episode_id"]:
                    episode_row_counts[row["episode_id"]] += 1

        expected_rows = expected_counts[(expected_year, expected_role)]
        if rows != expected_rows:
            errors.append(f"{split}: {rows} rows, expected {expected_rows}")
        if split == "station_test" and station_ids != holdouts:
            errors.append(f"station_test stations {sorted(station_ids)} do not equal holdouts {sorted(holdouts)}")
        split_summary[split] = {
            "rows": rows,
            "anomaly_rows": anomalies,
            "weather_rows": weather,
            "anomaly_percent": round(100.0 * anomalies / rows, 4),
            "stations": len(station_ids),
            "anomaly_rows_by_type": dict(sorted(by_type.items())),
        }

    for episode in episodes:
        expected = int(episode["affected_rows"])
        actual = episode_row_counts[episode["episode_id"]]
        if expected != actual:
            errors.append(f"{episode['episode_id']}: manifest rows {expected}, labelled rows {actual}")

    episode_splits: defaultdict[str, set[str]] = defaultdict(set)
    for episode in episodes:
        episode_splits[episode["episode_id"]].add(episode["split"])
    if any(len(splits) != 1 for splits in episode_splits.values()):
        errors.append("At least one episode crosses split boundaries.")

    fault_episode_counts = Counter(
        row["anomaly_type"] for row in episodes if row["label_category"] == "sensor_fault"
    )
    missing_fault_types = FAULT_TYPES - set(fault_episode_counts)
    if missing_fault_types:
        errors.append(f"Fault types absent from episode manifest: {sorted(missing_fault_types)}")

    checks = {
        "generated_file_hashes_match": not any("mismatch" in error.lower() or "missing generated" in error.lower() for error in errors),
        "episode_ids_globally_unique": len(episode_ids) == len(set(episode_ids)),
        "all_fault_types_present": not missing_fault_types,
        "split_year_and_role_rules_hold": not any("invalid year/role" in error for error in errors),
        "no_row_leakage_between_splits": not any("Row leakage" in error for error in errors),
        "station_test_contains_only_holdouts": not any("do not equal holdouts" in error for error in errors),
        "episode_manifest_counts_match_rows": not any("manifest rows" in error for error in errors),
        "original_values_and_timestamps_preserved": not any("original values" in error or "source timestamp" in error for error in errors),
        "stream_actions_match_fault_types": not any("stream action" in error or "timestamp error has zero" in error for error in errors),
        "fault_and_weather_labels_are_exclusive": not any("both fault and weather" in error for error in errors),
    }
    return {
        "ready_for_feature_engineering": not errors and all(checks.values()),
        "checks": checks,
        "errors": errors[:100],
        "error_count": len(errors),
        "episode_count": len(episodes),
        "fault_episode_counts": dict(sorted(fault_episode_counts.items())),
        "split_summary": split_summary,
        "manifest_entries": len(manifest_rows),
    }


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard labelled dataset validation",
        "",
        f"**Ready for feature engineering: {'YES' if report['ready_for_feature_engineering'] else 'NO'}**",
        "",
        f"- Episodes: {report['episode_count']:,}",
        f"- Generated files covered by checksum manifest: {report['manifest_entries']}",
        f"- Validation errors: {report['error_count']}",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for check, passed in report["checks"].items():
        lines.append(f"| {check.replace('_', ' ')} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(["", "## Splits", "", "| Split | Rows | Fault rows | Weather rows | Fault % | Stations |", "|---|---:|---:|---:|---:|---:|"])
    for split, values in report["split_summary"].items():
        lines.append(
            f"| {split} | {values['rows']:,} | {values['anomaly_rows']:,} | {values['weather_rows']:,} | "
            f"{values['anomaly_percent']:.4f}% | {values['stations']} |"
        )
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = validate()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)
    print(json.dumps(report, indent=2))
    if not report["ready_for_feature_engineering"]:
        raise SystemExit("Labelled dataset validation failed.")


if __name__ == "__main__":
    main()

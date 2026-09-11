"""Validate feature-table integrity, label preservation, and leakage guards."""

from __future__ import annotations

import csv
import gzip
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LABELLED = ROOT / "data" / "labelled"
FEATURES = ROOT / "data" / "features"
MANIFEST = FEATURES / "manifest.csv"
SPEC = FEATURES / "feature_spec.json"
REPORT_JSON = ROOT / "reports" / "feature_validation.json"
REPORT_MD = ROOT / "reports" / "feature_validation.md"
SPLITS = ("train", "validation", "time_test", "station_test")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate() -> dict[str, object]:
    errors: list[str] = []
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    feature_columns = spec["model_feature_columns"]
    label_columns = spec["label_columns"]
    audit_columns = spec["audit_columns"]
    overlap = sorted(set(feature_columns) & set(label_columns + audit_columns))
    if overlap:
        errors.append(f"Model feature contract overlaps labels/audit fields: {overlap}")

    manifest_rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline="")))
    for item in manifest_rows:
        path = ROOT / item["relative_path"]
        if not path.exists():
            errors.append(f"Missing feature artifact: {item['relative_path']}")
            continue
        if path.stat().st_size != int(item["bytes"]):
            errors.append(f"Size mismatch: {item['relative_path']}")
        if sha256(path) != item["sha256"]:
            errors.append(f"SHA-256 mismatch: {item['relative_path']}")

    split_summary: dict[str, dict[str, object]] = {}
    total_rows = 0
    total_neighbor_rows = 0
    total_available_rows = 0

    for split in SPLITS:
        labelled_path = LABELLED / f"{split}.csv"
        feature_path = FEATURES / f"{split}_features.csv.gz"
        row_ids: set[str] = set()
        rows = 0
        available = 0
        neighbor_rows = 0
        robust_z_rows = 0
        missing_features: Counter[str] = Counter()
        first_available_seen: set[str] = set()

        with labelled_path.open("r", encoding="utf-8", newline="") as labelled_handle, gzip.open(
            feature_path, "rt", encoding="utf-8", newline=""
        ) as feature_handle:
            source_reader = csv.DictReader(labelled_handle)
            feature_reader = csv.DictReader(feature_handle)
            missing_columns = set(spec["output_columns"]) - set(feature_reader.fieldnames or [])
            extra_columns = set(feature_reader.fieldnames or []) - set(spec["output_columns"])
            if missing_columns or extra_columns:
                errors.append(f"{split}: feature schema mismatch; missing={sorted(missing_columns)}, extra={sorted(extra_columns)}")

            for source, feature in itertools.zip_longest(source_reader, feature_reader):
                if source is None or feature is None:
                    errors.append(f"{split}: labelled and feature row counts differ")
                    break
                rows += 1
                if feature["row_id"] in row_ids:
                    errors.append(f"{split}: duplicate row_id {feature['row_id']}")
                row_ids.add(feature["row_id"])
                for column in ("station_id", "timestamp_utc", "split") + tuple(label_columns) + tuple(audit_columns[:-1]):
                    if feature[column] != source.get(column, ""):
                        errors.append(f"{split}: {column} not preserved at {source['station_id']} {source['timestamp_utc']}")
                        break

                expected_available = "0" if source["stream_action"] == "drop" else "1"
                if feature["available_to_detector"] != expected_available:
                    errors.append(f"{split}: incorrect detector availability at {source['station_id']} {source['timestamp_utc']}")
                if expected_available == "1":
                    available += 1
                    if source["station_id"] not in first_available_seen:
                        first_available_seen.add(source["station_id"])
                        if feature["temperature_lag1"] or feature["pressure_lag1"] or feature["humidity_lag1"]:
                            errors.append(f"{split}: first available row for {source['station_id']} has non-causal lag")
                else:
                    for column in ("temperature_value", "pressure_value", "humidity_value", "temperature_lag1", "pressure_lag1", "humidity_lag1"):
                        if feature[column]:
                            errors.append(f"{split}: dropped row exposes detector value {column}")

                for column in feature_columns:
                    value = feature[column]
                    if not value:
                        missing_features[column] += 1
                        continue
                    try:
                        numeric = float(value)
                    except ValueError:
                        errors.append(f"{split}: non-numeric model feature {column}={value}")
                        continue
                    if not math.isfinite(numeric):
                        errors.append(f"{split}: non-finite model feature {column}={value}")

                if feature["neighbor_station_count"] and float(feature["neighbor_station_count"]) > 0:
                    neighbor_rows += 1
                    minimum_age = float(feature["neighbor_min_age_minutes"])
                    maximum_age = float(feature["neighbor_max_age_minutes"])
                    if minimum_age < 0 or maximum_age < minimum_age or maximum_age > 180.0:
                        errors.append(f"{split}: invalid neighbour ages {minimum_age}, {maximum_age}")
                if feature["temperature_robust_z_24h"] or feature["pressure_robust_z_24h"] or feature["humidity_robust_z_24h"]:
                    robust_z_rows += 1

        total_rows += rows
        total_available_rows += available
        total_neighbor_rows += neighbor_rows
        split_summary[split] = {
            "rows": rows,
            "available_to_detector_rows": available,
            "neighbor_rows": neighbor_rows,
            "neighbor_coverage_percent": round(100.0 * neighbor_rows / max(available, 1), 4),
            "robust_z_rows": robust_z_rows,
            "robust_z_coverage_percent": round(100.0 * robust_z_rows / max(available, 1), 4),
            "selected_feature_missing_percent": {
                column: round(100.0 * missing_features[column] / max(rows, 1), 4)
                for column in (
                    "temperature_value", "pressure_value", "humidity_value",
                    "temperature_lag1", "temperature_rolling_median_24h", "neighbor_temperature_median",
                )
            },
        }

    checks = {
        "feature_hashes_match_manifest": not any("mismatch" in error.lower() or "missing feature" in error.lower() for error in errors),
        "model_features_exclude_labels_and_audit": not overlap,
        "source_rows_and_labels_preserved": not any("not preserved" in error or "row counts differ" in error for error in errors),
        "row_ids_unique": not any("duplicate row_id" in error for error in errors),
        "all_model_features_numeric_and_finite": not any("non-numeric" in error or "non-finite" in error for error in errors),
        "dropped_rows_hidden_from_detector": not any("dropped row exposes" in error for error in errors),
        "first_lags_are_causal": not any("non-causal lag" in error for error in errors),
        "neighbor_alignment_is_backward_only": not any("invalid neighbour ages" in error for error in errors),
        "neighbor_coverage_above_70_percent": total_neighbor_rows / max(total_available_rows, 1) > 0.70,
    }
    return {
        "ready_for_baseline_models": not errors and all(checks.values()),
        "checks": checks,
        "errors": errors[:100],
        "error_count": len(errors),
        "model_feature_count": len(feature_columns),
        "total_rows": total_rows,
        "overall_neighbor_coverage_percent": round(100.0 * total_neighbor_rows / max(total_available_rows, 1), 4),
        "splits": split_summary,
        "manifest_entries": len(manifest_rows),
    }


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard feature validation",
        "",
        f"**Ready for baseline models: {'YES' if report['ready_for_baseline_models'] else 'NO'}**",
        "",
        f"- Rows: {report['total_rows']:,}",
        f"- Model features: {report['model_feature_count']}",
        f"- Overall neighbour coverage: {report['overall_neighbor_coverage_percent']:.4f}%",
        f"- Validation errors: {report['error_count']}",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for check, passed in report["checks"].items():
        lines.append(f"| {check.replace('_', ' ')} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(["", "## Split coverage", "", "| Split | Rows | Detector rows | Neighbour coverage | Robust-z coverage |", "|---|---:|---:|---:|---:|"])
    for split, values in report["splits"].items():
        lines.append(
            f"| {split} | {values['rows']:,} | {values['available_to_detector_rows']:,} | "
            f"{values['neighbor_coverage_percent']:.4f}% | {values['robust_z_coverage_percent']:.4f}% |"
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
    if not report["ready_for_baseline_models"]:
        raise SystemExit("Feature validation failed.")


if __name__ == "__main__":
    main()

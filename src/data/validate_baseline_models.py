"""Validate the frozen Phase 4 model, thresholds, reports, and predictions."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

import joblib


ROOT = Path(__file__).resolve().parents[2]
PREDICTION_DIR = ROOT / "data" / "predictions"
FEATURE_REPORT = ROOT / "reports" / "feature_generation.json"
BASELINE_REPORT = ROOT / "reports" / "baseline_models.json"
THRESHOLDS = ROOT / "models" / "baseline_thresholds.json"
MODEL = ROOT / "models" / "isolation_forest.joblib"
MANIFEST = PREDICTION_DIR / "manifest.csv"
REPORT_JSON = ROOT / "reports" / "baseline_validation.json"
REPORT_MD = ROOT / "reports" / "baseline_validation.md"
SPLITS = ("validation", "time_test", "station_test")
DETECTORS = ("qc_rules", "hampel", "ewma", "neighbor", "combined", "isolation_forest")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    errors: list[str] = []
    feature_report = json.loads(FEATURE_REPORT.read_text(encoding="utf-8"))
    baseline_report = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    manifest_rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline="")))
    manifest = {row["relative_path"]: row for row in manifest_rows}

    if thresholds.get("status") != "frozen_before_test_evaluation":
        errors.append("Threshold document is not marked frozen before test evaluation.")
    if thresholds.get("selection_split") != "validation (2023)":
        errors.append("Threshold selection split is not 2023 validation.")
    if set(thresholds.get("detectors", {})) != set(DETECTORS):
        errors.append("Threshold document does not contain exactly the expected detectors.")
    for detector in DETECTORS:
        value = thresholds.get("detectors", {}).get(detector, {}).get("threshold")
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"Invalid threshold for {detector}.")

    artifact = joblib.load(MODEL)
    if not artifact.get("feature_columns") or "pipeline" not in artifact:
        errors.append("Saved Isolation Forest artifact is incomplete.")
    if baseline_report.get("phase") != 4 or baseline_report.get("status") != "complete":
        errors.append("Baseline report is not marked Phase 4 complete.")

    split_report: dict[str, dict[str, object]] = {}
    for split in SPLITS:
        path = PREDICTION_DIR / f"{split}_baseline_scores.csv.gz"
        relative = path.relative_to(ROOT).as_posix()
        if relative not in manifest:
            errors.append(f"Missing manifest entry for {relative}.")
            continue
        actual_hash = sha256(path)
        if actual_hash != manifest[relative]["sha256"]:
            errors.append(f"Checksum mismatch for {relative}.")
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {f"{name}_score" for name in DETECTORS} | {f"{name}_prediction" for name in DETECTORS}
            if not required.issubset(set(reader.fieldnames or [])):
                errors.append(f"Prediction columns are incomplete for {split}.")
            row_count = sum(1 for _ in reader)
        expected = feature_report["splits"][split]["rows"]
        if row_count != expected:
            errors.append(f"{split} has {row_count} predictions; expected {expected}.")
        split_report[split] = {"rows": row_count, "expected_rows": expected, "sha256": actual_hash}

    report = {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "thresholds_frozen_on_validation": thresholds.get("status") == "frozen_before_test_evaluation",
        "saved_model_feature_count": len(artifact.get("feature_columns", [])),
        "splits": split_report,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# SkyGuard Phase 4 artifact validation", "",
        f"**Status: {report['status']}**", "",
        f"- Errors: {report['error_count']}",
        f"- Frozen 2023 validation thresholds: {report['thresholds_frozen_on_validation']}",
        f"- Saved Isolation Forest features: {report['saved_model_feature_count']}",
        "", "| Split | Prediction rows | Expected rows | Checksum |", "|---|---:|---:|---|",
    ]
    for split, values in split_report.items():
        lines.append(f"| {split} | {values['rows']:,} | {values['expected_rows']:,} | `{values['sha256']}` |")
    if errors:
        lines.extend(["", "## Errors", ""] + [f"- {error}" for error in errors])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

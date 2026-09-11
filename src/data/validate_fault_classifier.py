"""Validate Phase 5 model policy, prediction files, and benchmark improvement."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

import joblib


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "phase5_classifiers.joblib"
POLICY = ROOT / "models" / "phase5_policy.json"
REPORT = ROOT / "reports" / "fault_classifier.json"
BASELINE_REPORT = ROOT / "reports" / "baseline_models.json"
MANIFEST = ROOT / "data" / "predictions" / "phase5_manifest.csv"
OUTPUT_JSON = ROOT / "reports" / "fault_classifier_validation.json"
OUTPUT_MD = ROOT / "reports" / "fault_classifier_validation.md"
SPLITS = ("validation", "time_test", "station_test")
FORBIDDEN = {"hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    errors: list[str] = []
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
    artifact = joblib.load(MODEL)
    manifest = {
        row["relative_path"]: row
        for row in csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline=""))
    }

    if policy.get("status") != "frozen_before_2024_evaluation":
        errors.append("Phase 5 policy is not marked frozen before 2024 evaluation.")
    if policy.get("selection_split") != "validation (2023)":
        errors.append("Phase 5 policy was not selected on 2023 validation.")
    for key in ("fault_probability_threshold", "weather_probability_threshold", "event_abstain_threshold", "root_abstain_threshold"):
        value = policy.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"Invalid policy value: {key}.")
    if not {"event_classifier", "root_cause_classifier", "feature_columns", "policy"}.issubset(artifact):
        errors.append("Saved classifier bundle is incomplete.")
    feature_columns = set(artifact.get("feature_columns", []))
    if feature_columns & FORBIDDEN:
        errors.append("Leakage-prone absolute calendar features remain in the classifier.")
    if report.get("phase") != 5 or report.get("status") != "complete":
        errors.append("Classifier report is not marked Phase 5 complete.")

    split_results: dict[str, dict[str, object]] = {}
    for split in SPLITS:
        path = ROOT / "data" / "predictions" / f"{split}_phase5_predictions.csv.gz"
        relative = path.relative_to(ROOT).as_posix()
        if relative not in manifest:
            errors.append(f"Missing prediction manifest row for {split}.")
            continue
        actual_hash = sha256(path)
        if actual_hash != manifest[relative]["sha256"]:
            errors.append(f"Prediction checksum mismatch for {split}.")
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            expected_columns = {"fault_probability", "weather_probability", "event_decision", "root_cause_prediction"}
            if not expected_columns.issubset(set(reader.fieldnames or [])):
                errors.append(f"Prediction schema is incomplete for {split}.")
            rows = sum(1 for _ in reader)
        expected_rows = report["evaluation"][split]["rows"]
        if rows != expected_rows:
            errors.append(f"{split} prediction row count differs from the report.")
        split_results[split] = {"rows": rows, "expected_rows": expected_rows, "sha256": actual_hash}

    improvement: dict[str, dict[str, float | bool]] = {}
    for split in ("time_test", "station_test"):
        baseline_best = max(item["f1"] for item in baseline["evaluation"][split].values())
        phase5_f1 = report["evaluation"][split]["binary_fault_detection"]["f1"]
        improved = phase5_f1 > baseline_best
        if not improved:
            errors.append(f"Phase 5 did not improve the best Phase 4 F1 on {split}.")
        improvement[split] = {
            "phase4_best_f1": baseline_best,
            "phase5_f1": phase5_f1,
            "absolute_gain": phase5_f1 - baseline_best,
            "improved": improved,
        }

    validation = {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors), "errors": errors,
        "policy_frozen_on_2023": policy.get("status") == "frozen_before_2024_evaluation",
        "feature_count": len(feature_columns),
        "calendar_shortcuts_excluded": not bool(feature_columns & FORBIDDEN),
        "splits": split_results,
        "f1_improvement": improvement,
    }
    OUTPUT_JSON.write_text(json.dumps(validation, indent=2), encoding="utf-8")
    lines = [
        "# SkyGuard Phase 5 artifact validation", "", f"**Status: {validation['status']}**", "",
        f"- Errors: {validation['error_count']}",
        f"- Policy frozen using 2023: {validation['policy_frozen_on_2023']}",
        f"- Classifier features: {validation['feature_count']}",
        f"- Absolute calendar shortcuts excluded: {validation['calendar_shortcuts_excluded']}",
        "", "| Test | Phase 4 best F1 | Phase 5 F1 | Absolute gain |", "|---|---:|---:|---:|",
    ]
    for split, item in improvement.items():
        lines.append(f"| {split} | {item['phase4_best_f1']:.4f} | {item['phase5_f1']:.4f} | +{item['absolute_gain']:.4f} |")
    lines.extend(["", "| Split | Rows | Expected | Checksum |", "|---|---:|---:|---|"])
    for split, item in split_results.items():
        lines.append(f"| {split} | {item['rows']:,} | {item['expected_rows']:,} | `{item['sha256']}` |")
    if errors:
        lines.extend(["", "## Errors", ""] + [f"- {error}" for error in errors])
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

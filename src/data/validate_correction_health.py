"""Validate Phase 6 policies, incidents, corrections, health, and checksums."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "models" / "correction_policy.json"
REPORT = ROOT / "reports" / "correction_health.json"
MANIFEST = ROOT / "data" / "incidents" / "manifest.csv"
OUTPUT_JSON = ROOT / "reports" / "correction_health_validation.json"
OUTPUT_MD = ROOT / "reports" / "correction_health_validation.md"
SPLITS = ("validation", "time_test", "station_test")
REQUIRED_INCIDENT_FIELDS = {
    "incident_id", "row_id", "station_id", "timestamp_utc", "decision", "fault_probability",
    "root_cause", "affected_sensors", "severity", "explanation", "evidence",
    "model_feature_contributions", "corrections", "sensor_health_after_incident", "recommended_action",
}


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
    manifest = {
        row["relative_path"]: row
        for row in csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline=""))
    }
    if policy.get("status") != "frozen_before_2024_evaluation" or policy.get("selection_split") != "validation (2023)":
        errors.append("Correction policy is not marked frozen from 2023 before 2024 evaluation.")
    if report.get("phase") != 6 or report.get("status") != "complete":
        errors.append("Correction report is not marked Phase 6 complete.")

    split_results: dict[str, dict[str, object]] = {}
    for split in SPLITS:
        incident_path = ROOT / "data" / "incidents" / f"{split}_incidents.jsonl.gz"
        health_path = ROOT / "data" / "incidents" / f"{split}_sensor_health.csv"
        for path in (incident_path, health_path):
            relative = path.relative_to(ROOT).as_posix()
            if relative not in manifest:
                errors.append(f"Missing manifest entry for {relative}.")
            elif sha256(path) != manifest[relative]["sha256"]:
                errors.append(f"Checksum mismatch for {relative}.")

        incidents = 0
        corrections = 0
        with gzip.open(incident_path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if '"original_' in line:
                    errors.append(f"Audit-only original value leaked into {split} incident {line_number}.")
                incident = json.loads(line)
                incidents += 1
                if not REQUIRED_INCIDENT_FIELDS.issubset(incident):
                    errors.append(f"Incomplete incident schema in {split} line {line_number}.")
                if not incident.get("explanation") or not incident.get("recommended_action"):
                    errors.append(f"Missing explanation/action in {split} line {line_number}.")
                for correction in incident.get("corrections", []):
                    corrections += 1
                    estimate = correction["estimate"]
                    if not correction["interval_lower"] <= estimate <= correction["interval_upper"]:
                        errors.append(f"Invalid uncertainty interval in {split} line {line_number}.")
                for score in incident.get("sensor_health_after_incident", {}).values():
                    if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
                        errors.append(f"Invalid incident health score in {split} line {line_number}.")
        if incidents != report["outputs"][split]["incidents"]:
            errors.append(f"Incident count mismatch for {split}.")

        health_rows = list(csv.DictReader(health_path.open("r", encoding="utf-8", newline="")))
        if len(health_rows) % 3 != 0:
            errors.append(f"Health output for {split} does not have three sensors per station.")
        for row in health_rows:
            score = float(row["health_score"])
            if not 0 <= score <= 100:
                errors.append(f"Health score outside 0-100 in {split}.")
        split_results[split] = {
            "incidents": incidents, "corrections": corrections, "health_rows": len(health_rows),
            "incident_sha256": sha256(incident_path), "health_sha256": sha256(health_path),
        }

    improvement: dict[str, dict[str, bool]] = {}
    for split in ("time_test", "station_test"):
        improvement[split] = {}
        for sensor, item in report["evaluation"][split]["operational"].items():
            improved = (
                item["corrected_points"] > 0
                and item["corrected_value_mae"] < item["reported_value_mae"]
            )
            improvement[split][sensor] = improved
            if not improved:
                errors.append(f"Operational correction did not improve {sensor} MAE on {split}.")

    validation = {
        "status": "PASS" if not errors else "FAIL", "error_count": len(errors), "errors": errors,
        "policy_frozen_on_2023": policy.get("status") == "frozen_before_2024_evaluation",
        "audit_values_absent_from_incidents": not any("leaked" in error for error in errors),
        "splits": split_results, "operational_mae_improved": improvement,
    }
    OUTPUT_JSON.write_text(json.dumps(validation, indent=2), encoding="utf-8")
    lines = [
        "# SkyGuard Phase 6 artifact validation", "", f"**Status: {validation['status']}**", "",
        f"- Errors: {validation['error_count']}",
        f"- Policy frozen using 2023: {validation['policy_frozen_on_2023']}",
        f"- Audit-only original values absent from incidents: {validation['audit_values_absent_from_incidents']}",
        "", "| Split | Incidents | Corrections | Health rows |", "|---|---:|---:|---:|",
    ]
    for split, item in split_results.items():
        lines.append(f"| {split} | {item['incidents']:,} | {item['corrections']:,} | {item['health_rows']:,} |")
    lines.extend(["", "All operational sensor/test combinations reduce MAE relative to the corrupted reported values."])
    if errors:
        lines.extend(["", "## Errors", ""] + [f"- {error}" for error in errors])
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

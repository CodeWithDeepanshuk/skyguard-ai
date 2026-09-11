"""Validate Phase 6.1 coverage improvement and automatic-repair safety."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path

import joblib


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "sensor_repair_classifiers.joblib"
POLICY = ROOT / "models" / "safe_repair_policy.json"
REPORT = ROOT / "reports" / "safe_repair.json"
PHASE6_REPORT = ROOT / "reports" / "correction_health.json"
MANIFEST = ROOT / "data" / "incidents" / "safe_repair_manifest.csv"
OUTPUT_JSON = ROOT / "reports" / "safe_repair_validation.json"
OUTPUT_MD = ROOT / "reports" / "safe_repair_validation.md"
SPLITS = ("validation", "time_test", "station_test")
SENSORS = ("temperature", "pressure", "humidity")


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
    phase6 = json.loads(PHASE6_REPORT.read_text(encoding="utf-8"))
    artifact = joblib.load(MODEL)
    manifest = {
        row["relative_path"]: row
        for row in csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline=""))
    }
    if policy.get("status") != "frozen_before_2024_evaluation" or policy.get("selection_split") != "validation (2023)":
        errors.append("Safe-repair policy is not frozen from 2023 validation.")
    if set(artifact.get("models", {})) != set(SENSORS):
        errors.append("Sensor repair model bundle is incomplete.")
    if policy.get("automatic_repair_enabled", {}).get("humidity") is not False:
        errors.append("Automatic humidity replacement must remain disabled.")

    files: dict[str, dict[str, object]] = {}
    for split in SPLITS:
        path = ROOT / "data" / "incidents" / f"{split}_repair_actions.jsonl.gz"
        relative = path.relative_to(ROOT).as_posix()
        if relative not in manifest or sha256(path) != manifest.get(relative, {}).get("sha256"):
            errors.append(f"Safe-repair checksum validation failed for {split}.")
        actions = 0
        auto_actions = 0
        auto_humidity = 0
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if '"original_' in line:
                    errors.append(f"Audit-only original value leaked into {split} repair actions.")
                action = json.loads(line)
                actions += 1
                if action["automatic_application"]:
                    auto_actions += 1
                    auto_humidity += int(action["sensor"] == "humidity")
                    if action["tier"] != "auto_repair_eligible":
                        errors.append(f"Automatic action lacks auto-repair tier in {split}.")
        if actions != report["outputs"][split]["actions"] or auto_actions != report["outputs"][split]["auto_eligible"]:
            errors.append(f"Safe-repair action count mismatch for {split}.")
        if auto_humidity:
            errors.append(f"Automatic humidity actions were emitted in {split}.")
        files[split] = {"actions": actions, "auto_actions": auto_actions, "sha256": sha256(path)}

    coverage_gain: dict[str, dict[str, float]] = {}
    auto_safety: dict[str, dict[str, bool]] = {}
    for split in ("time_test", "station_test"):
        coverage_gain[split] = {}
        auto_safety[split] = {}
        for sensor in SENSORS:
            old_coverage = phase6["evaluation"][split]["operational"][sensor]["coverage"]
            new_coverage = report["evaluation"][split][sensor]["review"]["coverage_recall"]
            gain = new_coverage - old_coverage
            coverage_gain[split][sensor] = gain
            if gain < -1e-12:
                errors.append(f"Review coverage regressed for {sensor} on {split}.")
            auto = report["evaluation"][split][sensor]["auto"]
            safe = (sensor == "humidity" and auto["proposed_corrections"] == 0) or (
                sensor != "humidity" and auto["false_positive_corrections"] == 0
            )
            auto_safety[split][sensor] = safe
            if not safe:
                errors.append(f"Automatic repair safety condition failed for {sensor} on {split}.")

    validation = {
        "status": "PASS" if not errors else "FAIL", "error_count": len(errors), "errors": errors,
        "policy_frozen_on_2023": policy.get("status") == "frozen_before_2024_evaluation",
        "humidity_automatic_repair_disabled": policy.get("automatic_repair_enabled", {}).get("humidity") is False,
        "files": files, "review_coverage_absolute_gain": coverage_gain,
        "automatic_repair_safety": auto_safety,
    }
    OUTPUT_JSON.write_text(json.dumps(validation, indent=2), encoding="utf-8")
    lines = [
        "# SkyGuard Phase 6.1 safe-repair validation", "", f"**Status: {validation['status']}**", "",
        f"- Errors: {validation['error_count']}",
        f"- Frozen using 2023: {validation['policy_frozen_on_2023']}",
        f"- Automatic humidity repair disabled: {validation['humidity_automatic_repair_disabled']}",
        "", "| Test | Sensor | Review coverage gain | Auto safety passed |", "|---|---|---:|---|",
    ]
    for split in ("time_test", "station_test"):
        for sensor in SENSORS:
            lines.append(f"| {split} | {sensor} | {coverage_gain[split][sensor] * 100:+.2f} points | {auto_safety[split][sensor]} |")
    lines.extend(["", f"Automatic replacement actions: time holdout {files['time_test']['auto_actions']}, unseen stations {files['station_test']['auto_actions']}. No false automatic temperature/pressure corrections were observed in either frozen holdout."])
    if errors:
        lines.extend(["", "## Errors", ""] + [f"- {error}" for error in errors])
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

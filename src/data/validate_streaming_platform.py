"""Validate Phase 7 scenarios, profile evidence, and API checks."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_REPORT = ROOT / "reports" / "replay_scenarios.json"
PLATFORM_REPORT = ROOT / "reports" / "streaming_platform.json"
MANIFEST = ROOT / "data" / "demo" / "manifest.csv"
OUTPUT_JSON = ROOT / "reports" / "streaming_validation.json"
OUTPUT_MD = ROOT / "reports" / "streaming_validation.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    errors: list[str] = []
    scenarios = json.loads(SCENARIO_REPORT.read_text(encoding="utf-8"))["scenarios"]
    platform = json.loads(PLATFORM_REPORT.read_text(encoding="utf-8"))
    manifest = {row["relative_path"]: row for row in csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline=""))}
    required = {"pressure_drift", "regional_weather", "dropout", "packet_errors"}
    if set(scenarios) != required:
        errors.append("Replay scenario set is incomplete.")
    for name, item in scenarios.items():
        path = ROOT / item["file"]
        relative = path.relative_to(ROOT).as_posix()
        if relative not in manifest or sha256(path) != manifest.get(relative, {}).get("sha256"):
            errors.append(f"Scenario checksum failed: {name}.")
    for key, detected in platform.get("communication_evidence", {}).items():
        if not detected:
            errors.append(f"Communication check failed: {key}.")
    for path, result in platform.get("api_checks", {}).items():
        if result.get("status_code") != 200:
            errors.append(f"API smoke check failed: {path}.")
    for name, profile in platform.get("profiles", {}).items():
        if profile["throughput_rows_per_second"] <= 0 or profile["mean_processing_latency_ms"] <= 0:
            errors.append(f"Invalid performance profile for {name}.")

    validation = {
        "status": "PASS" if not errors else "FAIL", "error_count": len(errors), "errors": errors,
        "scenario_count": len(scenarios), "all_api_checks_pass": all(item.get("status_code") == 200 for item in platform["api_checks"].values()),
        "communication_evidence": platform["communication_evidence"],
    }
    OUTPUT_JSON.write_text(json.dumps(validation, indent=2), encoding="utf-8")
    lines = [
        "# SkyGuard Phase 7 validation", "", f"**Status: {validation['status']}**", "",
        f"- Errors: {validation['error_count']}", f"- Packaged scenarios: {validation['scenario_count']}",
        f"- All API checks passed: {validation['all_api_checks_pass']}",
        f"- Dropout, duplicate, timestamp evidence: {all(validation['communication_evidence'].values())}",
    ]
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

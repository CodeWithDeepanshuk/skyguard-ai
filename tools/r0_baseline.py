"""Freeze/verify existing model and data bytes; never train or score a holdout.

Usage: python tools/r0_baseline.py capture | manifest | verify
Generated receipts are intentionally written only under reports/r0_baseline;
the release manifest is config/active_model_manifest.json. Existing snapshots
cannot be silently re-created. Live caches and runtime databases are mutable.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "reports/r0_baseline"
BEFORE = RECEIPTS / "immutable_before.json"
MANIFEST = ROOT / "config/active_model_manifest.json"
ACTIVE_MODELS = ("models/phase10_final.joblib", "models/phase10_climatology.joblib")
RUNTIME_FILES = (
    "src/skyguard/live/metar.py", "src/skyguard/features/builder.py",
    "src/skyguard/features/temporal.py", "src/skyguard/features/neighbors.py",
    "src/skyguard/features/phase10.py", "src/skyguard/models/phase10.py",
    "src/data/run_api.py", "requirements.txt", "reports/phase10_final.json",
    "reports/qc_baseline.json", "config/stations.csv",
    "dashboard/app.js", "dashboard/index.html", "dashboard/styles.css",
    "dashboard/station-map.js", "dashboard/sensor-trace.js", "dashboard/live-qc.js",
    "verify_skyguard.ps1", "tools/verification_helpers.ps1", "tools/r0_baseline.py",
)


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fingerprint(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def protected_inventory(root: Path = ROOT):
    records = {}
    for directory in ("models", "data"):
        for path in sorted((root / directory).rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if relative.parts[:2] in (("data", "live"), ("data", "runtime")):
                continue
            if "__pycache__" not in relative.parts:
                records[relative.as_posix()] = fingerprint(path)
    return records


def changes(expected, actual):
    return {
        "missing": sorted(expected.keys() - actual.keys()),
        "added": sorted(actual.keys() - expected.keys()),
        "changed": sorted(key for key in expected.keys() & actual.keys() if expected[key] != actual[key]),
    }


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_protected():
    before = json.loads(BEFORE.read_text(encoding="utf-8"))
    current = protected_inventory()
    differences = changes(before["files"], current)
    if any(differences.values()):
        raise RuntimeError("R0 immutable baseline mismatch: " + json.dumps(differences))
    return before, current


def capture():
    if BEFORE.exists():
        raise FileExistsError(f"Refusing to replace the original baseline: {BEFORE}")
    files = protected_inventory()
    write_json(BEFORE, {
        "captured_at_utc": stamp(), "scope": "All existing models and data, byte hashes only",
        "exclusions": ["data/live/**", "data/runtime/**", "**/__pycache__/**"],
        "not_evidence_of": "Data correctness, absence of leakage, or model accuracy",
        "file_count": len(files), "total_bytes": sum(x["bytes"] for x in files.values()), "files": files,
    })
    print(f"Captured {len(files)} immutable files; no data contents evaluated.")


def manifest():
    before, _ = verify_protected()
    # Only the two existing, locally deployed artifacts are trusted here.
    # Uploaded candidate pickles are NOT loaded by this utility.
    import joblib
    bundle = joblib.load(ROOT / ACTIVE_MODELS[0])
    report = json.loads((ROOT / "reports/phase10_final.json").read_text(encoding="utf-8"))
    spec = json.loads((ROOT / "data/features_phase10/feature_spec.json").read_text(encoding="utf-8"))
    if bundle["policy"] != report["policy"]:
        raise RuntimeError("Deployed bundle policy does not match the historical report")
    features = list(bundle["event_features"])
    if features != spec["model_features"]:
        raise RuntimeError("Deployed feature order does not match the feature specification")
    versions = {}
    for package in ("numpy", "pandas", "scikit-learn", "joblib", "lightgbm", "catboost", "fastapi", "uvicorn", "httpx"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    model_roles = {name: {
        **value, "role": "deployed_live" if name in ACTIVE_MODELS else "not_loaded_by_live_service; historical_or_candidate",
    } for name, value in before["files"].items() if name.startswith("models/")}
    write_json(MANIFEST, {
        "schema_version": 1, "release": "R0-reliable-baseline", "generated_at_utc": stamp(),
        "model_version": report["model_version"], "model_changed": False,
        "status": "Frozen research comparator; not certified operational IMD deployment",
        "startup": "python src/data/run_api.py", "verification": "powershell -NoProfile -ExecutionPolicy Bypass -File verify_skyguard.ps1",
        "deployed_artifacts": {name: fingerprint(ROOT / name) for name in ACTIVE_MODELS},
        "all_model_roles": model_roles,
        "event_model_class": type(bundle["event_model"]).__module__ + "." + type(bundle["event_model"]).__name__,
        "root_model_class": type(bundle["root_model"]).__module__ + "." + type(bundle["root_model"]).__name__,
        "feature_count": len(features), "event_features_in_order": features,
        "root_features_in_order": list(bundle["phase10_features"]),
        "training_stations": list(bundle["training_stations"]), "thresholds_and_policy": bundle["policy"],
        "preprocessing_contract": {
            "detector_inputs": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
            "live_source": "AviationWeather.gov METAR; periodic terminal observations, not raw IMD AWS telemetry",
            "relative_humidity": "Derived upstream from temperature/dew point; dew point excluded from detector features",
            "live_pressure": "METAR QNH hPa; historical pressure compatibility remains an R1 audit item",
            "temporal_and_spatial": "Existing feature implementations preserved; causal and source-contract audit remains open",
            "tcn": "Not executed by current live service; no automatic promotion of later notebooks",
        },
        "runtime_source_hashes": {name: fingerprint(ROOT / name) for name in RUNTIME_FILES},
        "dependencies_observed": {"python": platform.python_version(), "packages": versions},
        "dependency_note": "Observed local versions, not a portable dependency lock or rebuild guarantee",
        "dataset_version_record": {"path": BEFORE.relative_to(ROOT).as_posix(), **fingerprint(BEFORE), "file_count": before["file_count"]},
        "historical_benchmark": {
            "source": "reports/phase10_final.json", "evaluation": report["evaluation"],
            "provenance": "2024 historical injected-anomaly evaluations, previously inspected; not a fresh blind test",
            "no_new_scoring": True, "live_accuracy": "Not measured; live reports lack verified sensor-fault labels",
            "2025": "Previously opened blind evaluation is historical evidence, not a new untouched holdout",
        },
        "remaining_limitations": [
            "No alert does not prove sensor health; diagnosis/correction/maintenance are advisory.",
            "R0 fixes display and verification correctness, not recall, calibration or training leakage.",
            "India/DWD cadence, pressure datum, reported/derived humidity and neighbour support require R1 audit.",
        ],
    })
    print(f"Release manifest written: {len(features)} features; policy verified against deployed bundle.")


def verify():
    before, current = verify_protected()
    release = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, expected in {**release["deployed_artifacts"], **release["runtime_source_hashes"]}.items():
        if fingerprint(ROOT / name) != expected:
            raise RuntimeError(f"Release manifest mismatch: {name}")
    if fingerprint(BEFORE) != {key: release["dataset_version_record"][key] for key in ("sha256", "bytes")}:
        raise RuntimeError("Baseline snapshot was replaced")
    write_json(RECEIPTS / "immutable_after.json", {
        "verified_at_utc": stamp(), "baseline_at_utc": before["captured_at_utc"],
        "status": "pass", "file_count": len(current), "all_protected_bytes_unchanged": True,
        "manifest": {"path": MANIFEST.relative_to(ROOT).as_posix(), **fingerprint(MANIFEST)},
        "files": current,
    })
    print(f"PASS: {len(current)} protected files unchanged; deployed model and runtime manifest match.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "manifest", "verify"))
    globals()[parser.parse_args().action]()

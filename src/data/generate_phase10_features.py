"""Generate additive SIH-compliant Phase 10 feature tables."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.features.phase10 import (  # noqa: E402
    FORBIDDEN_PHASE10_INPUTS, PHASE10_FEATURES, add_phase10_features,
    assert_phase10_compliance, fit_climatology,
)


SOURCE = ROOT / "data" / "features"
OUTPUT = ROOT / "data" / "features_phase10"
MODEL_DIR = ROOT / "models"
REPORT = ROOT / "reports" / "phase10_features.json"
SPLITS = ("train", "validation", "time_test", "station_test")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    started = time.perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    assert_phase10_compliance()
    print("Loading 2022 features and fitting three-parameter climatology...")
    train = pd.read_csv(SOURCE / "train_features.csv.gz", low_memory=False)
    profiles = fit_climatology(train)
    profile_path = MODEL_DIR / "phase10_climatology.joblib"
    joblib.dump(profiles, profile_path, compress=3)

    split_report: dict[str, object] = {}
    for split in SPLITS:
        print(f"Generating Phase 10 trend features: {split}")
        frame = train if split == "train" else pd.read_csv(SOURCE / f"{split}_features.csv.gz", low_memory=False)
        enhanced = add_phase10_features(frame, profiles)
        output = OUTPUT / f"{split}_features.csv.gz"
        enhanced.to_csv(output, index=False, compression={"method": "gzip", "compresslevel": 6})
        split_report[split] = {
            "rows": int(enhanced.shape[0]),
            "columns": int(enhanced.shape[1]),
            "bytes": output.stat().st_size,
            "sha256": sha256(output),
        }
        if split == "train":
            del train
        del frame, enhanced

    spec = {
        "phase": 10,
        "status": "complete",
        "input_contract": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
        "model_feature_count": len(PHASE10_FEATURES),
        "model_features": list(PHASE10_FEATURES),
        "forbidden_inputs": sorted(FORBIDDEN_PHASE10_INPUTS),
        "dew_point_used_by_model": False,
        "climatology": "2022 clean station month-hour medians; cluster/global fallback for unseen stations",
        "causality": "trend features use the current and previously emitted observations only",
        "splits": split_report,
        "profile": profile_path.relative_to(ROOT).as_posix(),
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    (OUTPUT / "feature_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    REPORT.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(json.dumps({"status": "complete", "features": len(PHASE10_FEATURES), "splits": split_report}, indent=2))


if __name__ == "__main__":
    main()


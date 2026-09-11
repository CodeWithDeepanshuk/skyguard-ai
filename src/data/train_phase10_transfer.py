"""Train a station-invariant compliant detector for unseen AWS stations."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.refine_phase10_event import evaluate, probability, values  # noqa: E402
from data.run_phase10_models import load_split  # noqa: E402
from skyguard.evaluation.classification import episode_balanced_weights  # noqa: E402
from skyguard.evaluation.metrics import choose_threshold  # noqa: E402
from skyguard.features.phase10 import PHASE10_FEATURES  # noqa: E402
from skyguard.models.phase10 import choose_persistence_policy  # noqa: E402


ABSOLUTE_PARTS = (
    "_value", "_lag1", "_rolling_median", "_ewma_prior", "_climatology_residual",
    "_weighted_mean", "neighbor_temperature_median", "neighbor_pressure_median", "neighbor_humidity_median",
)
ABSOLUTE_NAMES = {"temperature_humidity_interaction", "pressure_temperature_ratio", "nearest_neighbor_km"}
TRANSFER_FEATURES = tuple(
    feature for feature in PHASE10_FEATURES
    if feature not in ABSOLUTE_NAMES and not any(part in feature for part in ABSOLUTE_PARTS)
)
MODEL_FILE = ROOT / "models" / "phase10_transfer_event.joblib"
REPORT_FILE = ROOT / "reports" / "phase10_transfer_event.json"


def main() -> None:
    started = time.perf_counter()
    train = load_split("train")
    validation = load_split("validation")
    labels = train["event_label"].astype(str).to_numpy()
    weights = episode_balanced_weights(labels, train["episode_id"].fillna("").astype(str).to_numpy())
    print(f"Training station-transfer model with {len(TRANSFER_FEATURES)} invariant features...")
    base = LGBMClassifier(
        objective="multiclass", n_estimators=620, learning_rate=0.025, num_leaves=31,
        max_depth=9, min_child_samples=30, subsample=0.90, colsample_bytree=0.90,
        reg_alpha=0.75, reg_lambda=6.0, random_state=26074, n_jobs=-1, verbosity=-1,
    )
    base.fit(values(train, TRANSFER_FEATURES), labels, sample_weight=weights)
    model = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    model.fit(values(validation, TRANSFER_FEATURES), validation["event_label"].astype(str).to_numpy())
    validation_fault = probability(model, validation, TRANSFER_FEATURES, "sensor_fault")
    validation_weather = probability(model, validation, TRANSFER_FEATURES, "genuine_weather")
    fault_labels = (validation["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather_labels = (validation["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    fault_policy, _ = choose_persistence_policy(validation, fault_labels, validation_fault, weather_labels)
    weather_policy = choose_threshold(weather_labels, validation_weather)
    policy = {"fault": fault_policy, "weather": weather_policy, "dew_point_used": False, "station_invariant": True}
    evaluation = {"validation": evaluate(validation, validation_fault, fault_policy)}
    for split in ("time_test", "station_test"):
        frame = load_split(split)
        scores = probability(model, frame, TRANSFER_FEATURES, "sensor_fault")
        evaluation[split] = evaluate(frame, scores, fault_policy)
    joblib.dump({
        "event_model": model, "features": list(TRANSFER_FEATURES), "policy": policy,
        "training_stations": sorted(train["station_id"].astype(str).unique().tolist()),
    }, MODEL_FILE, compress=3)
    report = {"phase": "10-transfer", "status": "complete", "feature_count": len(TRANSFER_FEATURES), "policy": policy, "evaluation": evaluation, "runtime_seconds": round(time.perf_counter() - started, 3)}
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

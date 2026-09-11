"""Train the final compliant neighbour-consensus genuine-weather gate."""

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

from data.refine_phase10_event import values  # noqa: E402
from data.run_phase10_models import load_split  # noqa: E402
from skyguard.evaluation.metrics import choose_threshold  # noqa: E402
from skyguard.features.phase10 import PHASE10_FEATURES  # noqa: E402


WEATHER_FEATURES = tuple(feature for feature in PHASE10_FEATURES if (
    feature.startswith("neighbor_") or feature.startswith("regional_")
    or "climatology_residual" in feature or "slope_" in feature
    or "cusum_" in feature or feature in {"temperature_robust_z_24h", "pressure_robust_z_24h", "humidity_robust_z_24h"}
))
MODEL_FILE = ROOT / "models" / "phase10_weather_gate.joblib"
REPORT_FILE = ROOT / "reports" / "phase10_weather_gate.json"


def class_weights(labels: np.ndarray) -> np.ndarray:
    positives = int(np.sum(labels == 1))
    negatives = int(np.sum(labels == 0))
    result = np.empty(labels.size, dtype=np.float64)
    result[labels == 1] = labels.size / max(2 * positives, 1)
    result[labels == 0] = labels.size / max(2 * negatives, 1)
    return result


def scores(model: object, frame) -> np.ndarray:
    return model.predict_proba(values(frame, WEATHER_FEATURES))[:, 1]


def metrics(frame, probabilities: np.ndarray, threshold: float) -> dict[str, float]:
    labels = (frame["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    prediction = probabilities >= threshold
    tp = int(np.sum(prediction & (labels == 1)))
    fp = int(np.sum(prediction & (labels == 0)))
    fn = int(np.sum(~prediction & (labels == 1)))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / max(precision + recall, 1e-12)}


def main() -> None:
    started = time.perf_counter()
    train = load_split("train")
    validation = load_split("validation")
    train_labels = (train["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    print(f"Training weather gate on all {train.shape[0]:,} rows and {len(WEATHER_FEATURES)} spatial/trend features...")
    base = LGBMClassifier(
        objective="binary", n_estimators=600, learning_rate=0.025, num_leaves=31,
        max_depth=8, min_child_samples=25, subsample=0.90, colsample_bytree=0.90,
        reg_alpha=0.5, reg_lambda=5.0, random_state=26075, n_jobs=-1, verbosity=-1,
    )
    base.fit(values(train, WEATHER_FEATURES), train_labels, sample_weight=class_weights(train_labels))
    model = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    validation_labels = (validation["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    model.fit(values(validation, WEATHER_FEATURES), validation_labels)
    validation_scores = scores(model, validation)
    policy = choose_threshold(validation_labels, validation_scores)
    evaluation = {"validation": metrics(validation, validation_scores, policy["threshold"])}
    for split in ("time_test", "station_test"):
        frame = load_split(split)
        evaluation[split] = metrics(frame, scores(model, frame), policy["threshold"])
    joblib.dump({"weather_model": model, "features": list(WEATHER_FEATURES), "policy": policy, "dew_point_used": False}, MODEL_FILE, compress=3)
    report = {"phase": "10-weather-gate", "status": "complete", "feature_count": len(WEATHER_FEATURES), "policy": policy, "evaluation": evaluation, "runtime_seconds": round(time.perf_counter() - started, 3)}
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

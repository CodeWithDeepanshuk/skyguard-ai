"""Refine Phase 10 with the proven multiclass event formulation."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.run_phase10_models import load_split, sampled_indices  # noqa: E402
from skyguard.evaluation.classification import episode_balanced_weights  # noqa: E402
from skyguard.evaluation.metrics import choose_threshold, episode_metrics, point_metrics  # noqa: E402
from skyguard.features.phase10 import PHASE10_BASE_FEATURES, PHASE10_FEATURES, assert_phase10_compliance  # noqa: E402
from skyguard.models.phase10 import choose_persistence_policy, causal_persistence_scores  # noqa: E402


MODEL_FILE = ROOT / "models" / "phase10_refined_event.joblib"
REPORT_FILE = ROOT / "reports" / "phase10_refined_event.json"
RANDOM_SEED = 26073


def values(frame: pd.DataFrame, features: tuple[str, ...]) -> np.ndarray:
    return frame.loc[:, features].to_numpy(dtype=np.float32, copy=True)


def probability(model: object, frame: pd.DataFrame, features: tuple[str, ...], label: str) -> np.ndarray:
    classes = np.asarray(model.classes_, dtype=str)
    index = int(np.flatnonzero(classes == label)[0])
    return model.predict_proba(values(frame, features))[:, index]


def build(name: str) -> LGBMClassifier:
    if name == "regularized":
        return LGBMClassifier(
            objective="multiclass", n_estimators=480, learning_rate=0.035, num_leaves=31,
            max_depth=8, min_child_samples=35, subsample=0.85, colsample_bytree=0.80,
            reg_alpha=0.5, reg_lambda=5.0, random_state=RANDOM_SEED, n_jobs=-1, verbosity=-1,
        )
    return LGBMClassifier(
        objective="multiclass", n_estimators=360, learning_rate=0.04, num_leaves=31,
        min_child_samples=20, subsample=0.85, colsample_bytree=0.80,
        reg_alpha=0.1, reg_lambda=1.0, random_state=RANDOM_SEED, n_jobs=-1, verbosity=-1,
    )


def evaluate(frame: pd.DataFrame, fault_scores: np.ndarray, policy: dict[str, float]) -> dict[str, object]:
    labels = (frame["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (frame["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    adjusted = causal_persistence_scores(frame, fault_scores, policy["persistence_decay"])
    result = point_metrics(
        labels, adjusted, policy["threshold"], frame["station_id"].astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), weather,
    )
    result["episode_detection"] = episode_metrics(
        labels, adjusted >= policy["threshold"], frame["episode_id"].fillna("").astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), frame["anomaly_type"].astype(str).tolist(),
    )
    return result


def main() -> None:
    started = time.perf_counter()
    assert_phase10_compliance()
    train = load_split("train")
    validation = load_split("validation")
    selected_rows = sampled_indices(train, 30000)
    labels = train["event_label"].astype(str).to_numpy()
    weights = episode_balanced_weights(
        labels[selected_rows], train.iloc[selected_rows]["episode_id"].fillna("").astype(str).to_numpy(),
    )
    feature_sets = {
        "base67": tuple(PHASE10_BASE_FEATURES),
        "trend_no_climatology": tuple(column for column in PHASE10_FEATURES if not column.endswith("_climatology_residual")),
        "all108": tuple(PHASE10_FEATURES),
    }
    candidates = []
    for feature_name, features in feature_sets.items():
        for model_name in ("phase5_shape", "regularized"):
            print(f"Training {feature_name}/{model_name}...")
            model = build(model_name)
            model.fit(values(train.iloc[selected_rows], features), labels[selected_rows], sample_weight=weights)
            scores = probability(model, validation, features, "sensor_fault")
            aucpr = float(average_precision_score((validation["event_label"] == "sensor_fault").astype(int), scores))
            candidates.append({"feature_name": feature_name, "model_name": model_name, "features": features, "model": model, "validation_aucpr": aucpr})
    selected = max(candidates, key=lambda item: item["validation_aucpr"])
    print(f"Selected {selected['feature_name']}/{selected['model_name']} AUCPR={selected['validation_aucpr']:.5f}")
    calibrated = CalibratedClassifierCV(FrozenEstimator(selected["model"]), method="sigmoid")
    calibrated.fit(values(validation, selected["features"]), validation["event_label"].astype(str).to_numpy())
    validation_fault = probability(calibrated, validation, selected["features"], "sensor_fault")
    validation_weather = probability(calibrated, validation, selected["features"], "genuine_weather")
    fault_labels = (validation["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather_labels = (validation["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    fault_policy, _ = choose_persistence_policy(validation, fault_labels, validation_fault, weather_labels)
    weather_policy = choose_threshold(weather_labels, validation_weather)
    policy = {
        "status": "selected_on_full_2023_validation",
        "fault": fault_policy, "weather": weather_policy,
        "feature_name": selected["feature_name"], "model_name": selected["model_name"],
        "dew_point_used": False,
    }
    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"event_model": calibrated, "features": list(selected["features"]), "policy": policy}, MODEL_FILE, compress=3)
    evaluation = {"validation": evaluate(validation, validation_fault, fault_policy)}
    for split in ("time_test", "station_test"):
        print(f"Evaluating {split}...")
        frame = load_split(split)
        scores = probability(calibrated, frame, selected["features"], "sensor_fault")
        evaluation[split] = evaluate(frame, scores, fault_policy)
    report = {
        "phase": "10-refined", "status": "complete", "policy": policy,
        "candidates": [
            {key: value for key, value in item.items() if key not in {"model", "features"}} | {"feature_count": len(item["features"])}
            for item in candidates
        ],
        "evaluation": evaluation,
        "artifact": MODEL_FILE.relative_to(ROOT).as_posix(), "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"selected": policy, "evaluation": evaluation, "runtime_seconds": report["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()

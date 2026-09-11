"""Train compliant fault-family specialists and select their fusion on 2023."""

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


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.refine_phase10_event import probability  # noqa: E402
from data.run_phase10_models import load_split, model_values  # noqa: E402
from skyguard.evaluation.metrics import episode_metrics, point_metrics  # noqa: E402
from skyguard.features.phase10 import PHASE10_FEATURES  # noqa: E402
from skyguard.models.phase10 import causal_persistence_scores, choose_persistence_policy  # noqa: E402


MODEL_FILE = ROOT / "models" / "phase10_specialists.joblib"
REPORT_FILE = ROOT / "reports" / "phase10_specialists.json"
RANDOM_SEED = 26073
FAMILIES = {
    "slow_fault": {"bias", "drift", "frozen_sensor"},
    "drift_bias": {"bias", "drift"},
    "frozen": {"frozen_sensor"},
    "noise": {"noise"},
    "abrupt": {"communication_corruption", "multi_sensor_failure", "scaling_error", "spike", "sudden_drop", "unit_error"},
}


def binary_weights(labels: np.ndarray, episodes: np.ndarray) -> np.ndarray:
    weights = np.zeros(labels.size, dtype=np.float64)
    negative = np.flatnonzero(labels == 0)
    positive = np.flatnonzero(labels == 1)
    weights[negative] = 0.5 / max(negative.size, 1)
    groups: dict[str, list[int]] = {}
    for index in positive:
        groups.setdefault(str(episodes[index]), []).append(int(index))
    for indices in groups.values():
        weights[indices] = 0.5 / max(len(groups), 1) / len(indices)
    return weights * labels.size / max(weights.sum(), 1e-12)


def train_specialist(train: pd.DataFrame, validation: pd.DataFrame, family: set[str], seed: int) -> object:
    event = train["event_label"].astype(str).to_numpy()
    anomaly = train["anomaly_type"].astype(str).to_numpy()
    positive = np.isin(anomaly, list(family)) & (event == "sensor_fault")
    nonfault = event != "sensor_fault"
    rng = np.random.default_rng(seed)
    negative_indices = np.flatnonzero(nonfault)
    selected_negative = rng.choice(negative_indices, size=min(35000, negative_indices.size), replace=False)
    selected = np.sort(np.r_[selected_negative, np.flatnonzero(positive)])
    labels = positive[selected].astype(np.int8)
    weights = binary_weights(labels, train.iloc[selected]["episode_id"].fillna("").astype(str).to_numpy())
    base = LGBMClassifier(
        objective="binary", n_estimators=520, learning_rate=0.03, num_leaves=31, max_depth=8,
        min_child_samples=15, subsample=0.90, colsample_bytree=0.85, reg_alpha=0.5,
        reg_lambda=5.0, random_state=seed, n_jobs=-1, verbosity=-1,
    )
    base.fit(model_values(train.iloc[selected]), labels, sample_weight=weights)
    validation_event = validation["event_label"].astype(str).to_numpy()
    validation_anomaly = validation["anomaly_type"].astype(str).to_numpy()
    calibration_mask = (validation_event != "sensor_fault") | np.isin(validation_anomaly, list(family))
    calibration_labels = (np.isin(validation_anomaly, list(family)) & (validation_event == "sensor_fault")).astype(np.int8)
    model = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    model.fit(model_values(validation.loc[calibration_mask]), calibration_labels[calibration_mask])
    return model


def specialist_score(model: object, frame: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(model_values(frame))[:, 1]


def combinations(general: np.ndarray, specialist_scores: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    stacked = np.column_stack(list(specialist_scores.values()))
    maximum = np.max(stacked, axis=1)
    slow_max = np.max(np.column_stack([specialist_scores["slow_fault"], specialist_scores["drift_bias"], specialist_scores["frozen"]]), axis=1)
    return {
        "general": general,
        "general_plus_40": np.maximum(general, 0.40 * maximum),
        "general_plus_55": np.maximum(general, 0.55 * maximum),
        "general_plus_70": np.maximum(general, 0.70 * maximum),
        "general_plus_slow55": np.maximum(general, 0.55 * slow_max),
        "general_plus_slow70": np.maximum(general, 0.70 * slow_max),
    }


def metrics(frame: pd.DataFrame, raw: np.ndarray, policy: dict[str, float]) -> dict[str, object]:
    labels = (frame["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (frame["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    scores = causal_persistence_scores(frame, raw, policy["persistence_decay"])
    result = point_metrics(
        labels, scores, policy["threshold"], frame["station_id"].astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), weather,
    )
    result["episode_detection"] = episode_metrics(
        labels, scores >= policy["threshold"], frame["episode_id"].fillna("").astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), frame["anomaly_type"].astype(str).tolist(),
    )
    return result


def main() -> None:
    started = time.perf_counter()
    refined = joblib.load(ROOT / "models" / "phase10_refined_event.joblib")
    event_model = refined["event_model"]
    event_features = tuple(refined["features"])
    train = load_split("train")
    validation = load_split("validation")
    models = {}
    for offset, (name, family) in enumerate(FAMILIES.items()):
        print(f"Training specialist: {name}")
        models[name] = train_specialist(train, validation, family, RANDOM_SEED + 10 + offset)
    validation_general = probability(event_model, validation, event_features, "sensor_fault")
    validation_specialists = {name: specialist_score(model, validation) for name, model in models.items()}
    validation_combinations = combinations(validation_general, validation_specialists)
    labels = (validation["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (validation["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    policies = {}
    evaluation = {"validation": {}}
    for name, scores in validation_combinations.items():
        policy, _ = choose_persistence_policy(validation, labels, scores, weather)
        policies[name] = policy
        evaluation["validation"][name] = metrics(validation, scores, policy)
    selected = max(policies, key=lambda name: (evaluation["validation"][name]["f1"], evaluation["validation"][name]["recall"]))
    frozen_policy = policies[selected]
    print(f"Selected fusion: {selected}")
    for split in ("time_test", "station_test"):
        frame = load_split(split)
        general = probability(event_model, frame, event_features, "sensor_fault")
        specialist_values = {name: specialist_score(model, frame) for name, model in models.items()}
        split_combinations = combinations(general, specialist_values)
        evaluation[split] = {name: metrics(frame, scores, policies[name]) for name, scores in split_combinations.items()}
    joblib.dump({
        "event_model": event_model, "event_features": list(event_features), "specialists": models,
        "families": {key: sorted(value) for key, value in FAMILIES.items()},
        "selected_fusion": selected, "policy": frozen_policy, "dew_point_used": False,
    }, MODEL_FILE, compress=3)
    report = {
        "phase": "10-specialists", "status": "complete", "selected": selected,
        "policy": frozen_policy, "evaluation": evaluation,
        "artifact": MODEL_FILE.relative_to(ROOT).as_posix(), "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "selected": selected, "policy": frozen_policy,
        "validation": evaluation["validation"][selected],
        "time_test": evaluation["time_test"][selected],
        "station_test": evaluation["station_test"][selected],
        "runtime_seconds": report["runtime_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()

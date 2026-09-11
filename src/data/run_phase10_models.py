"""Train and evaluate the compliant Phase 10 LightGBM + causal TCN ensemble."""

from __future__ import annotations

import copy
import gzip
import json
import os
import random
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from torch.utils.data import DataLoader


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.evaluation.classification import (  # noqa: E402
    choose_selective_threshold, classification_report, episode_balanced_weights,
    expected_calibration_error, multiclass_brier_score,
)
from skyguard.evaluation.metrics import choose_threshold, episode_metrics, point_metrics  # noqa: E402
from skyguard.features.phase10 import PHASE10_FEATURES, assert_phase10_compliance  # noqa: E402
from skyguard.models.phase10 import (  # noqa: E402
    aggregate_incident_roots, causal_persistence_scores, choose_persistence_policy,
)
from skyguard.models.tcn import (  # noqa: E402
    TCN_FEATURES, CausalTCN, SequenceDataset, WeightedFocalLoss, sequence_index,
)


FEATURE_DIR = ROOT / "data" / "features_phase10"
MODEL_DIR = ROOT / "models"
PREDICTION_DIR = ROOT / "data" / "predictions_phase10"
REPORT_JSON = ROOT / "reports" / "phase10_models.json"
REPORT_MD = ROOT / "reports" / "phase10_models.md"
BUNDLE_FILE = MODEL_DIR / "phase10_ensemble.joblib"
TCN_FILE = MODEL_DIR / "phase10_tcn.pt"
POLICY_FILE = MODEL_DIR / "phase10_policy.json"
RANDOM_SEED = 26073
SEQUENCE_LENGTH = 24
META_COLUMNS = (
    "row_id", "station_id", "emitted_timestamp_utc", "cluster", "is_anomaly", "is_weather_event",
    "anomaly_type", "episode_id", "available_to_detector",
)


def seed_everything() -> None:
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))


def load_split(split: str) -> pd.DataFrame:
    columns = list(dict.fromkeys(list(PHASE10_FEATURES) + list(META_COLUMNS)))
    frame = pd.read_csv(FEATURE_DIR / f"{split}_features.csv.gz", usecols=columns, low_memory=False)
    frame = frame.loc[frame["available_to_detector"] == 1].reset_index(drop=True)
    frame["event_label"] = np.where(
        frame["is_weather_event"] == 1, "genuine_weather",
        np.where(frame["is_anomaly"] == 1, "sensor_fault", "normal"),
    )
    return frame


def model_values(frame: pd.DataFrame) -> np.ndarray:
    return frame.loc[:, PHASE10_FEATURES].to_numpy(dtype=np.float32, copy=True)


def temporal_masks(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    month = pd.to_datetime(frame["emitted_timestamp_utc"], utc=True).dt.month.to_numpy()
    calibration = month <= 6
    return calibration, ~calibration


def sampled_indices(frame: pd.DataFrame, normal_limit: int) -> np.ndarray:
    rng = np.random.default_rng(RANDOM_SEED)
    normal = np.flatnonzero(frame["event_label"].to_numpy() == "normal")
    nonnormal = np.flatnonzero(frame["event_label"].to_numpy() != "normal")
    chosen = rng.choice(normal, size=min(normal_limit, normal.size), replace=False)
    return np.sort(np.r_[chosen, nonnormal]).astype(np.int64)


def binary_episode_weights(labels: np.ndarray, episodes: np.ndarray) -> np.ndarray:
    """Equal class mass; equal episode mass inside the positive class."""

    labels = labels.astype(np.int8)
    weights = np.zeros(labels.size, dtype=np.float64)
    negative = np.flatnonzero(labels == 0)
    positive = np.flatnonzero(labels == 1)
    if negative.size:
        weights[negative] = 0.5 / negative.size
    groups: dict[str, list[int]] = {}
    for index in positive:
        episode = str(episodes[index])
        groups.setdefault(episode if episode and episode != "nan" else f"row-{index}", []).append(int(index))
    if groups:
        group_mass = 0.5 / len(groups)
        for indices in groups.values():
            weights[indices] = group_mass / len(indices)
    weights *= labels.size / max(weights.sum(), 1e-12)
    return weights


def lgbm_candidates(objective: str, classes: int | None = None) -> list[tuple[str, LGBMClassifier]]:
    common = dict(
        objective=objective, n_estimators=480, learning_rate=0.035, subsample=0.85,
        colsample_bytree=0.80, random_state=RANDOM_SEED, n_jobs=-1, verbosity=-1,
    )
    if classes is not None:
        common["num_class"] = classes
    return [
        ("balanced-31", LGBMClassifier(**common, num_leaves=31, min_child_samples=20, reg_alpha=0.1, reg_lambda=1.0)),
        ("regularized-31", LGBMClassifier(**common, num_leaves=31, max_depth=8, min_child_samples=35, reg_alpha=0.5, reg_lambda=5.0)),
        ("trend-63", LGBMClassifier(**common, num_leaves=63, max_depth=10, min_child_samples=18, reg_alpha=0.25, reg_lambda=3.0)),
    ]


def train_binary_specialist(
    train: pd.DataFrame, validation: pd.DataFrame, target_name: str,
) -> tuple[object, dict[str, object]]:
    selected = sampled_indices(train, 40000)
    labels = (train[target_name].to_numpy() == 1).astype(np.int8)
    weights = binary_episode_weights(labels[selected], train.iloc[selected]["episode_id"].fillna("").astype(str).to_numpy())
    calibration_mask, policy_mask = temporal_masks(validation)
    validation_labels = (validation[target_name].to_numpy() == 1).astype(np.int8)
    reports = []
    fitted: list[tuple[str, LGBMClassifier, float]] = []
    for name, model in lgbm_candidates("binary"):
        model.fit(model_values(train.iloc[selected]), labels[selected], sample_weight=weights)
        scores = model.predict_proba(model_values(validation.loc[policy_mask]))[:, 1]
        aucpr = float(average_precision_score(validation_labels[policy_mask], scores))
        reports.append({"name": name, "policy_half_aucpr": aucpr})
        fitted.append((name, model, aucpr))
    name, base, _ = max(fitted, key=lambda item: item[2])
    calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    calibrated.fit(model_values(validation.loc[calibration_mask]), validation_labels[calibration_mask])
    return calibrated, {"selected": name, "candidates": reports, "training_rows": int(selected.size)}


def tcn_matrix(frame: pd.DataFrame, center: np.ndarray, scale: np.ndarray) -> np.ndarray:
    values = frame.loc[:, TCN_FEATURES].to_numpy(dtype=np.float32, copy=True)
    values = (values - center) / scale
    return np.nan_to_num(values, nan=0.0, posinf=12.0, neginf=-12.0).clip(-12.0, 12.0).astype(np.float32)


def histories(frame: pd.DataFrame) -> np.ndarray:
    station_ids = frame["station_id"].astype(str).to_numpy()
    timestamps = pd.to_datetime(frame["emitted_timestamp_utc"], utc=True).astype("int64").to_numpy()
    return sequence_index(station_ids, timestamps, SEQUENCE_LENGTH)


def predict_tcn(model: CausalTCN, matrix: np.ndarray, history: np.ndarray, targets: np.ndarray, batch_size: int = 1024) -> np.ndarray:
    dataset = SequenceDataset(matrix, history, targets)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    result = np.empty(targets.size, dtype=np.float64)
    position = 0
    model.eval()
    with torch.no_grad():
        for (values,) in loader:
            probabilities = torch.sigmoid(model(values)).cpu().numpy()
            result[position: position + probabilities.size] = probabilities
            position += probabilities.size
    return result


def train_tcn(train: pd.DataFrame, validation: pd.DataFrame) -> tuple[CausalTCN, np.ndarray, np.ndarray, dict[str, object]]:
    raw = train.loc[:, TCN_FEATURES].to_numpy(dtype=np.float32, copy=True)
    center = np.nanmedian(raw, axis=0).astype(np.float32)
    q25 = np.nanpercentile(raw, 25, axis=0).astype(np.float32)
    q75 = np.nanpercentile(raw, 75, axis=0).astype(np.float32)
    scale = (q75 - q25).astype(np.float32)
    scale[~np.isfinite(scale) | (scale < 1e-4)] = 1.0
    center[~np.isfinite(center)] = 0.0

    train_matrix = tcn_matrix(train, center, scale)
    validation_matrix = tcn_matrix(validation, center, scale)
    train_history = histories(train)
    validation_history = histories(validation)
    selected = sampled_indices(train, 40000)
    validation_selected = sampled_indices(validation, 20000)
    labels = (train["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    validation_labels = (validation["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    selected_weights = binary_episode_weights(
        labels[selected], train.iloc[selected]["episode_id"].fillna("").astype(str).to_numpy(),
    )
    weights = np.ones(train.shape[0], dtype=np.float32)
    weights[selected] = selected_weights.astype(np.float32)
    dataset = SequenceDataset(train_matrix, train_history, selected, labels, weights)
    loader = DataLoader(dataset, batch_size=256, shuffle=True, num_workers=0)
    model = CausalTCN(input_channels=len(TCN_FEATURES) + 1, hidden_channels=32, dropout=0.15)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=2e-4)
    loss_function = WeightedFocalLoss(gamma=2.0)
    best_state = copy.deepcopy(model.state_dict())
    best_aucpr = -1.0
    patience = 0
    epochs: list[dict[str, float]] = []
    for epoch in range(1, 11):
        model.train()
        running = 0.0
        batches = 0
        for values, target, weight in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(values), target, weight)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            running += float(loss.detach())
            batches += 1
        scores = predict_tcn(model, validation_matrix, validation_history, validation_selected)
        aucpr = float(average_precision_score(validation_labels[validation_selected], scores))
        epochs.append({"epoch": epoch, "loss": running / max(batches, 1), "validation_sample_aucpr": aucpr})
        print(f"TCN epoch {epoch}: loss={epochs[-1]['loss']:.5f} validation AUCPR={aucpr:.5f}")
        if aucpr > best_aucpr + 1e-4:
            best_aucpr = aucpr
            best_state = copy.deepcopy(model.state_dict())
            patience = 0
        else:
            patience += 1
            if patience >= 3:
                break
    model.load_state_dict(best_state)
    report = {
        "sequence_length": SEQUENCE_LENGTH, "channels": len(TCN_FEATURES) + 1,
        "parameters": int(sum(parameter.numel() for parameter in model.parameters())),
        "training_rows": int(selected.size), "best_validation_sample_aucpr": best_aucpr, "epochs": epochs,
    }
    return model, center, scale, report


def fusion_values(frame: pd.DataFrame, lightgbm: np.ndarray, tcn: np.ndarray, weather: np.ndarray) -> np.ndarray:
    agreement = pd.to_numeric(frame["regional_agreement_mean"], errors="coerce").fillna(0.0).to_numpy()
    disagreement = pd.to_numeric(frame["regional_standardized_disagreement_max"], errors="coerce").fillna(0.0).clip(0, 20).to_numpy()
    neighbors = pd.to_numeric(frame["neighbor_station_count"], errors="coerce").fillna(0.0).to_numpy()
    return np.column_stack([
        lightgbm, tcn, 0.5 * (lightgbm + tcn), np.maximum(lightgbm, tcn), lightgbm * tcn,
        weather, agreement, disagreement, neighbors,
    ]).astype(np.float64)


def event_labels(frame: pd.DataFrame) -> np.ndarray:
    return frame["event_label"].to_numpy(dtype=str)


def fit_root_model(train: pd.DataFrame, validation: pd.DataFrame) -> tuple[object, dict[str, object]]:
    train_fault = train.loc[train["event_label"] == "sensor_fault"].reset_index(drop=True)
    validation_fault = validation.loc[validation["event_label"] == "sensor_fault"].reset_index(drop=True)
    labels = train_fault["anomaly_type"].astype(str).to_numpy()
    weights = episode_balanced_weights(labels, train_fault["episode_id"].fillna("").astype(str).to_numpy())
    model = LGBMClassifier(
        objective="multiclass", n_estimators=520, learning_rate=0.035, num_leaves=31,
        max_depth=8, min_child_samples=12, subsample=0.90, colsample_bytree=0.85,
        reg_alpha=0.5, reg_lambda=5.0, random_state=RANDOM_SEED + 2, n_jobs=-1, verbosity=-1,
    )
    model.fit(model_values(train_fault), labels, sample_weight=weights)
    calibration_mask, _ = temporal_masks(validation_fault)
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
    calibrated.fit(
        model_values(validation_fault.loc[calibration_mask]),
        validation_fault.loc[calibration_mask, "anomaly_type"].astype(str).to_numpy(),
    )
    return calibrated, {
        "training_rows": int(train_fault.shape[0]), "classes": calibrated.classes_.tolist(),
        "hierarchy": "packet/order rules before incident-aggregated physical root probabilities",
    }


def root_results(
    frame: pd.DataFrame, detected: np.ndarray, fault_scores: np.ndarray, root_model: object,
    root_threshold: float,
) -> tuple[dict[str, object], np.ndarray, np.ndarray, np.ndarray]:
    probabilities = root_model.predict_proba(model_values(frame))
    classes = np.asarray(root_model.classes_, dtype=str)
    raw_predictions = classes[np.argmax(probabilities, axis=1)]
    actual_fault = frame["event_label"].to_numpy() == "sensor_fault"
    oracle = classification_report(
        frame.loc[actual_fault, "anomaly_type"].astype(str).to_numpy(), raw_predictions[actual_fault], classes.tolist(),
    )
    predicted, confidence, incident_ids = aggregate_incident_roots(
        frame, detected, fault_scores, probabilities, classes,
    )
    low_confidence = detected & (confidence < root_threshold)
    predicted[low_confidence] = "unknown_fault"
    true_root = frame.loc[actual_fault, "anomaly_type"].astype(str).to_numpy()
    operational = predicted[actual_fault]
    diagnosed = ~np.isin(operational, ["not_a_fault", "unknown_fault"])
    end_to_end = {
        "fault_rows": int(actual_fault.sum()),
        "exact_accuracy": float(np.mean(operational == true_root)),
        "diagnostic_coverage": float(np.mean(diagnosed)),
        "accepted_root_accuracy": float(np.mean(operational[diagnosed] == true_root[diagnosed])) if diagnosed.any() else 0.0,
        "missed_detection_rows": int(np.sum(operational == "not_a_fault")),
        "unknown_fault_rows": int(np.sum(operational == "unknown_fault")),
    }

    episode_rows = frame.loc[actual_fault, ["episode_id", "anomaly_type"]].copy()
    episode_rows["prediction"] = operational
    detected_episodes = 0
    correct_episodes = 0
    diagnosed_episodes = 0
    for _, group in episode_rows.groupby("episode_id", dropna=True):
        options = group.loc[~group["prediction"].isin(["not_a_fault", "unknown_fault"]), "prediction"]
        any_detection = np.any(group["prediction"] != "not_a_fault")
        detected_episodes += int(any_detection)
        if not options.empty:
            diagnosed_episodes += 1
            majority = str(options.value_counts().index[0])
            correct_episodes += int(majority == str(group["anomaly_type"].iloc[0]))
    episodes = int(episode_rows["episode_id"].nunique())
    end_to_end["episode_root"] = {
        "episodes": episodes, "detected": detected_episodes,
        "diagnosed": diagnosed_episodes, "correct": correct_episodes,
        "diagnosed_accuracy": correct_episodes / max(diagnosed_episodes, 1),
    }
    return {"oracle_root_cause": oracle, "end_to_end_root_cause": end_to_end}, predicted, confidence, incident_ids


def evaluate(
    frame: pd.DataFrame, fault_model: object, weather_model: object, tcn: CausalTCN,
    center: np.ndarray, scale: np.ndarray, fusion: LogisticRegression, root_model: object,
    policy: dict[str, object],
) -> tuple[dict[str, object], pd.DataFrame]:
    values = model_values(frame)
    lightgbm_scores = fault_model.predict_proba(values)[:, 1]
    weather_scores = weather_model.predict_proba(values)[:, 1]
    matrix = tcn_matrix(frame, center, scale)
    history = histories(frame)
    tcn_scores = predict_tcn(tcn, matrix, history, np.arange(frame.shape[0], dtype=np.int64))
    base_scores = fusion.predict_proba(fusion_values(frame, lightgbm_scores, tcn_scores, weather_scores))[:, 1]
    fault_scores = causal_persistence_scores(frame, base_scores, float(policy["persistence_decay"]))
    detected = fault_scores >= float(policy["fault_threshold"])
    actual_events = event_labels(frame)
    labels = (actual_events == "sensor_fault").astype(np.int8)
    weather_flags = (actual_events == "genuine_weather").astype(np.int8)
    binary = point_metrics(
        labels, fault_scores, float(policy["fault_threshold"]),
        frame["station_id"].astype(str).tolist(), frame["emitted_timestamp_utc"].astype(str).tolist(), weather_flags,
    )
    binary["episode_detection"] = episode_metrics(
        labels, detected, frame["episode_id"].fillna("").astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), frame["anomaly_type"].astype(str).tolist(),
    )
    decisions = np.full(frame.shape[0], "normal", dtype=object)
    decisions[weather_scores >= float(policy["weather_threshold"])] = "genuine_weather"
    decisions[detected] = "sensor_fault"
    event = classification_report(actual_events, decisions.astype(str), ["normal", "genuine_weather", "sensor_fault"])
    root, root_prediction, root_confidence, incident_ids = root_results(
        frame, detected, fault_scores, root_model, float(policy["root_threshold"]),
    )
    output = frame.loc[:, ["row_id", "station_id", "emitted_timestamp_utc", "event_label", "anomaly_type", "episode_id"]].copy()
    output["lightgbm_fault_probability"] = lightgbm_scores
    output["tcn_fault_probability"] = tcn_scores
    output["weather_probability"] = weather_scores
    output["fault_probability"] = fault_scores
    output["event_decision"] = decisions
    output["root_cause_prediction"] = root_prediction
    output["root_cause_confidence"] = root_confidence
    output["predicted_incident_id"] = incident_ids
    result = {"rows": int(frame.shape[0]), "binary_fault_detection": binary, "event_decision": event, **root}
    return result, output


def markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard Phase 10 compliant ensemble", "",
        "The Phase 10 detector uses only temperature, pressure, relative humidity, causal history, and same-parameter neighbour evidence. Dew point is excluded.", "",
        "| Split | Precision | Recall | F1 | AUCPR | Episode recall | False alarms/station-day | Root coverage | Accepted root accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("time_test", "station_test"):
        values = report["evaluation"][split]
        binary = values["binary_fault_detection"]
        root = values["end_to_end_root_cause"]
        lines.append(
            f"| {split} | {binary['precision']:.2%} | {binary['recall']:.2%} | {binary['f1']:.2%} | "
            f"{binary['aucpr']:.2%} | {binary['episode_detection']['recall']:.2%} | "
            f"{binary['false_alarms_per_station_day']:.4f} | {root['diagnostic_coverage']:.2%} | {root['accepted_root_accuracy']:.2%} |"
        )
    lines.extend(["", "All model and policy choices were frozen using 2023 before either 2024 comparison split was loaded."])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    started = time.perf_counter()
    seed_everything()
    assert_phase10_compliance()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    PREDICTION_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading 2022 training and 2023 validation only...")
    train = load_split("train")
    validation = load_split("validation")
    print("Training tuned binary LightGBM fault specialist...")
    fault_model, fault_training = train_binary_specialist(train, validation, "is_anomaly")
    print("Training neighbour-aware genuine-weather gate...")
    weather_model, weather_training = train_binary_specialist(train, validation, "is_weather_event")
    print("Training causal TCN...")
    tcn, center, scale, tcn_training = train_tcn(train, validation)
    print("Training incident root-cause hierarchy...")
    root_model, root_training = fit_root_model(train, validation)

    calibration_mask, policy_mask = temporal_masks(validation)
    validation_values = model_values(validation)
    lgbm_validation = fault_model.predict_proba(validation_values)[:, 1]
    weather_validation = weather_model.predict_proba(validation_values)[:, 1]
    validation_tcn_matrix = tcn_matrix(validation, center, scale)
    validation_history = histories(validation)
    tcn_validation = predict_tcn(tcn, validation_tcn_matrix, validation_history, np.arange(validation.shape[0]))
    fusion = LogisticRegression(C=0.5, class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED)
    fault_labels = (validation["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    fusion.fit(
        fusion_values(validation.loc[calibration_mask], lgbm_validation[calibration_mask], tcn_validation[calibration_mask], weather_validation[calibration_mask]),
        fault_labels[calibration_mask],
    )
    base_validation = fusion.predict_proba(fusion_values(validation, lgbm_validation, tcn_validation, weather_validation))[:, 1]
    weather_flags = (validation["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    persistence_policy, _ = choose_persistence_policy(
        validation.loc[policy_mask].reset_index(drop=True), fault_labels[policy_mask], base_validation[policy_mask], weather_flags[policy_mask],
    )
    weather_policy = choose_threshold(weather_flags[policy_mask], weather_validation[policy_mask])

    validation_fault_scores = causal_persistence_scores(validation, base_validation, float(persistence_policy["persistence_decay"]))
    validation_detected = validation_fault_scores >= float(persistence_policy["threshold"])
    root_probabilities = root_model.predict_proba(validation_values)
    root_classes = np.asarray(root_model.classes_, dtype=str)
    aggregated_root, aggregated_confidence, _ = aggregate_incident_roots(
        validation, validation_detected, validation_fault_scores, root_probabilities, root_classes,
    )
    root_selection = policy_mask & validation_detected & (validation["event_label"].to_numpy() == "sensor_fault")
    if np.any(root_selection):
        root_abstention = choose_selective_threshold(
            validation.loc[root_selection, "anomaly_type"].astype(str).to_numpy(),
            aggregated_root[root_selection], aggregated_confidence[root_selection], target_accuracy=0.80,
        )
    else:
        root_abstention = {"threshold": 1.0, "coverage": 0.0, "accepted_accuracy": 0.0}
    policy = {
        "status": "frozen_on_2023_before_2024_loading",
        "input_contract": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
        "dew_point_used": False,
        "fault_threshold": persistence_policy["threshold"],
        "persistence_decay": persistence_policy["persistence_decay"],
        "weather_threshold": weather_policy["threshold"],
        "root_threshold": root_abstention["threshold"],
        "validation_policy_half": {"fault": persistence_policy, "weather": weather_policy, "root": root_abstention},
    }
    POLICY_FILE.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    torch.save({
        "state_dict": tcn.state_dict(), "input_channels": len(TCN_FEATURES) + 1,
        "hidden_channels": 32, "sequence_length": SEQUENCE_LENGTH,
        "features": list(TCN_FEATURES), "center": center, "scale": scale,
    }, TCN_FILE)
    joblib.dump({
        "fault_model": fault_model, "weather_model": weather_model, "fusion_model": fusion,
        "root_model": root_model, "phase10_features": list(PHASE10_FEATURES),
        "tcn_features": list(TCN_FEATURES), "tcn_file": TCN_FILE.name,
        "tcn_center": center, "tcn_scale": scale, "policy": policy,
    }, BUNDLE_FILE, compress=3)

    # The two 2024 comparison files are not loaded until every model and threshold is frozen above.
    evaluation: dict[str, object] = {}
    validation_result, _ = evaluate(
        validation, fault_model, weather_model, tcn, center, scale, fusion, root_model, policy,
    )
    evaluation["validation"] = validation_result
    del train, validation, validation_values, validation_tcn_matrix, validation_history
    for split in ("time_test", "station_test"):
        print(f"Evaluating frozen Phase 10 ensemble on {split}...")
        frame = load_split(split)
        result, predictions = evaluate(frame, fault_model, weather_model, tcn, center, scale, fusion, root_model, policy)
        evaluation[split] = result
        predictions.to_csv(
            PREDICTION_DIR / f"{split}_phase10_predictions.csv.gz", index=False,
            compression={"method": "gzip", "compresslevel": 6},
        )
        del frame, predictions

    phase5 = json.loads((ROOT / "reports" / "fault_classifier.json").read_text(encoding="utf-8"))["evaluation"]
    comparison: dict[str, object] = {}
    for split in ("time_test", "station_test"):
        old = phase5[split]["binary_fault_detection"]
        new = evaluation[split]["binary_fault_detection"]
        comparison[split] = {
            "phase5_f1": old["f1"], "phase10_f1": new["f1"], "f1_change_points": 100 * (new["f1"] - old["f1"]),
            "phase5_recall": old["recall"], "phase10_recall": new["recall"], "recall_change_points": 100 * (new["recall"] - old["recall"]),
            "phase5_precision": old["precision"], "phase10_precision": new["precision"],
            "phase5_episode_recall": old["episode_detection"]["recall"],
            "phase10_episode_recall": new["episode_detection"]["recall"],
        }
    report = {
        "phase": 10, "status": "complete", "compliant_three_parameter_model": True,
        "feature_count": len(PHASE10_FEATURES),
        "training": {"fault_lightgbm": fault_training, "weather_lightgbm": weather_training, "tcn": tcn_training, "root": root_training},
        "policy": policy, "evaluation": evaluation, "comparison_with_phase5": comparison,
        "artifacts": {
            "bundle": BUNDLE_FILE.relative_to(ROOT).as_posix(), "bundle_bytes": BUNDLE_FILE.stat().st_size,
            "tcn": TCN_FILE.relative_to(ROOT).as_posix(), "tcn_bytes": TCN_FILE.stat().st_size,
            "policy": POLICY_FILE.relative_to(ROOT).as_posix(),
        },
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown(report)
    print(json.dumps({"status": "complete", "comparison": comparison, "runtime_seconds": report["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()

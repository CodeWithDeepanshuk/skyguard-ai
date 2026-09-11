"""Package and evaluate the final compliant Phase 10 operating policy."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.refine_phase10_event import probability  # noqa: E402
from data.run_phase10_models import load_split, model_values, root_results  # noqa: E402
from skyguard.evaluation.classification import (  # noqa: E402
    choose_selective_threshold, classification_report, episode_balanced_weights,
)
from skyguard.evaluation.metrics import episode_metrics, point_metrics  # noqa: E402
from skyguard.models.phase10 import aggregate_incident_roots, causal_persistence_scores  # noqa: E402


REPORT = ROOT / "reports" / "phase10_final.json"
BUNDLE = ROOT / "models" / "phase10_final.joblib"
PREDICTION_DIR = ROOT / "data" / "predictions_phase10"


def detect(frame: pd.DataFrame, raw: np.ndarray, policy: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    scores = causal_persistence_scores(frame, raw, float(policy["persistence_decay"]))
    return scores, scores >= float(policy["threshold"])


def evaluate(
    frame: pd.DataFrame, event_model: object, features: tuple[str, ...], root_model: object,
    fault_policy: dict[str, float], weather_threshold: float, root_threshold: float,
) -> tuple[dict[str, object], pd.DataFrame]:
    fault_raw = probability(event_model, frame, features, "sensor_fault")
    weather_scores = probability(event_model, frame, features, "genuine_weather")
    scores, detected = detect(frame, fault_raw, fault_policy)
    events = frame["event_label"].astype(str).to_numpy()
    labels = (events == "sensor_fault").astype(np.int8)
    weather = (events == "genuine_weather").astype(np.int8)
    binary = point_metrics(labels, scores, float(fault_policy["threshold"]), frame["station_id"].astype(str).tolist(), frame["emitted_timestamp_utc"].astype(str).tolist(), weather)
    binary["episode_detection"] = episode_metrics(labels, detected, frame["episode_id"].fillna("").astype(str).tolist(), frame["emitted_timestamp_utc"].astype(str).tolist(), frame["anomaly_type"].astype(str).tolist())
    decisions = np.full(frame.shape[0], "normal", dtype=object)
    decisions[weather_scores >= weather_threshold] = "genuine_weather"
    decisions[detected] = "sensor_fault"
    event_report = classification_report(events, decisions.astype(str), ["normal", "genuine_weather", "sensor_fault"])
    roots, root_prediction, root_confidence, incidents = root_results(frame, detected, scores, root_model, root_threshold)
    predictions = frame.loc[:, ["row_id", "station_id", "emitted_timestamp_utc", "event_label", "anomaly_type", "episode_id"]].copy()
    predictions["fault_probability"] = scores
    predictions["weather_probability"] = weather_scores
    predictions["event_decision"] = decisions
    predictions["root_cause_prediction"] = root_prediction
    predictions["root_cause_confidence"] = root_confidence
    predictions["predicted_incident_id"] = incidents
    return {"rows": int(frame.shape[0]), "binary_fault_detection": binary, "event_decision": event_report, **roots}, predictions


def main() -> None:
    started = time.perf_counter()
    primary = joblib.load(ROOT / "models" / "phase10_full_data_event.joblib")
    sequence_bundle = joblib.load(ROOT / "models" / "phase10_ensemble.joblib")
    new_station = json.loads((ROOT / "reports" / "phase10_new_station_policy.json").read_text(encoding="utf-8"))
    event_model = primary["event_model"]
    features = tuple(primary["features"])
    root_model = sequence_bundle["root_model"]
    known_policy = primary["policy"]["fault"]
    new_policy = new_station["policy"]
    weather_threshold = float(primary["policy"]["weather"]["threshold"])

    validation = load_split("validation")
    train = load_split("train")
    
    # Fit upgraded Root-Cause Classifier on all multi-year fault episodes
    fault_fit = pd.concat([
        train.loc[train["event_label"] == "sensor_fault"],
        validation.loc[validation["event_label"] == "sensor_fault"]
    ], ignore_index=True)
    root_labels = fault_fit["anomaly_type"].astype(str).to_numpy()
    root_weights = episode_balanced_weights(root_labels, fault_fit["episode_id"].fillna("").astype(str).to_numpy())
    
    print(f"Fitting upgraded Root-Cause classifier on {fault_fit.shape[0]:,} multi-year fault rows across 12 classes...")
    from lightgbm import LGBMClassifier
    root_model = LGBMClassifier(
        objective="multiclass",
        n_estimators=580,
        learning_rate=0.035,
        num_leaves=35,
        max_depth=9,
        min_child_samples=12,
        subsample=0.90,
        colsample_bytree=0.85,
        reg_alpha=0.3,
        reg_lambda=3.0,
        random_state=26075,
        n_jobs=-1,
        verbosity=-1,
    )
    root_model.fit(model_values(fault_fit), root_labels, sample_weight=root_weights)

    validation_raw = probability(event_model, validation, features, "sensor_fault")
    validation_scores, validation_detected = detect(validation, validation_raw, known_policy)
    root_probabilities = root_model.predict_proba(model_values(validation))
    root_classes = np.asarray(root_model.classes_, dtype=str)
    root_predictions, root_confidence, _ = aggregate_incident_roots(
        validation, validation_detected, validation_scores, root_probabilities, root_classes,
    )
    selection = validation_detected & (validation["event_label"].to_numpy() == "sensor_fault")
    root_policy = choose_selective_threshold(
        validation.loc[selection, "anomaly_type"].astype(str).to_numpy(), root_predictions[selection],
        root_confidence[selection], target_accuracy=0.72,
    )
    root_threshold = float(root_policy["threshold"])
    training_stations = sorted(train["station_id"].astype(str).unique().tolist())
    policy = {
        "status": "final_phase10_compliant",
        "input_contract": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
        "dew_point_used_by_detector": False,
        "known_station": known_policy,
        "new_station": new_policy,
        "weather_threshold": weather_threshold,
        "root_threshold": root_threshold,
        "tcn_role": "advisory sequence evidence; automatic alerts remain LightGBM-gated because TCN fusion exceeded the unseen-station false-alarm limit",
    }
    joblib.dump({
        "event_model": event_model, "event_features": list(features), "root_model": root_model,
        "phase10_features": sequence_bundle["phase10_features"], "training_stations": training_stations,
        "policy": policy, "tcn_file": "phase10_tcn.pt", "tcn_center": sequence_bundle["tcn_center"],
        "tcn_scale": sequence_bundle["tcn_scale"], "climatology_file": "phase10_climatology.joblib",
    }, BUNDLE, compress=3)

    evaluation = {}
    for split, selected_policy in (("time_test", known_policy), ("station_test", new_policy)):
        frame = load_split(split)
        result, predictions = evaluate(frame, event_model, features, root_model, selected_policy, weather_threshold, root_threshold)
        evaluation[split] = result
        predictions.to_csv(PREDICTION_DIR / f"{split}_phase10_final_predictions.csv.gz", index=False, compression={"method": "gzip", "compresslevel": 6})

    phase5 = json.loads((ROOT / "reports" / "fault_classifier.json").read_text(encoding="utf-8"))["evaluation"]
    comparison = {}
    for split in ("time_test", "station_test"):
        old = phase5[split]["binary_fault_detection"]
        new = evaluation[split]["binary_fault_detection"]
        comparison[split] = {
            "phase5_noncompliant": {key: old[key] for key in ("precision", "recall", "f1", "aucpr", "false_alarms_per_station_day")},
            "phase10_compliant": {key: new[key] for key in ("precision", "recall", "f1", "aucpr", "false_alarms_per_station_day")},
            "episode_recall_phase5": old["episode_detection"]["recall"],
            "episode_recall_phase10": new["episode_detection"]["recall"],
        }
    report = {
        "phase": 10, "status": "complete", "model_version": "SkyGuard-P10-compliant",
        "compliant_three_parameter_detector": True, "feature_count": len(features),
        "policy": policy, "evaluation": evaluation, "comparison": comparison,
        "limitations": [
            "The TCN improves several slow-fault episode recalls but is advisory because its unseen-station false alarms exceeded the deployment constraint.",
            "The compliant unseen-station F1 is lower than Phase 5, whose top feature used forbidden measured dew point.",
            "Real maintenance labels are still required before health scores become calibrated failure forecasts.",
        ],
        "artifacts": {"bundle": BUNDLE.relative_to(ROOT).as_posix(), "bundle_bytes": BUNDLE.stat().st_size},
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": "complete", "comparison": comparison, "root_policy": root_policy}, indent=2))


if __name__ == "__main__":
    main()

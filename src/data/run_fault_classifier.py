"""Train, calibrate, freeze, and evaluate SkyGuard Phase 5 classifiers."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.evaluation.classification import (  # noqa: E402
    choose_selective_threshold, classification_report, episode_balanced_weights,
    expected_calibration_error, multiclass_brier_score,
)
from skyguard.evaluation.metrics import choose_threshold, episode_metrics, point_metrics  # noqa: E402
from skyguard.models.classification import CLASSIFIER_FEATURES, build_classifier, calibrate_prefit  # noqa: E402


FEATURE_DIR = ROOT / "data" / "features"
MODEL_DIR = ROOT / "models"
PREDICTION_DIR = ROOT / "data" / "predictions"
MODEL_FILE = MODEL_DIR / "phase5_classifiers.joblib"
POLICY_FILE = MODEL_DIR / "phase5_policy.json"
REPORT_JSON = ROOT / "reports" / "fault_classifier.json"
REPORT_MD = ROOT / "reports" / "fault_classifier.md"
MANIFEST = PREDICTION_DIR / "phase5_manifest.csv"
RANDOM_SEED = 26073
EVENT_CLASSES = ["normal", "genuine_weather", "sensor_fault"]
METADATA_COLUMNS = [
    "row_id", "station_id", "emitted_timestamp_utc", "is_anomaly", "is_weather_event",
    "anomaly_type", "episode_id", "available_to_detector",
]


def load_split(split: str) -> pd.DataFrame:
    columns = list(CLASSIFIER_FEATURES) + METADATA_COLUMNS
    frame = pd.read_csv(FEATURE_DIR / f"{split}_features.csv.gz", usecols=columns, low_memory=False)
    frame = frame.loc[frame["available_to_detector"] == 1].reset_index(drop=True)
    frame["event_label"] = np.where(
        frame["is_weather_event"] == 1, "genuine_weather",
        np.where(frame["is_anomaly"] == 1, "sensor_fault", "normal"),
    )
    return frame


def training_sample(frame: pd.DataFrame, normal_limit: int = 30000) -> pd.DataFrame:
    normal = frame.index[frame["event_label"] == "normal"].to_numpy()
    rng = np.random.default_rng(RANDOM_SEED)
    selected_normal = rng.choice(normal, size=min(normal_limit, normal.size), replace=False)
    selected = np.concatenate([selected_normal, frame.index[frame["event_label"] != "normal"].to_numpy()])
    return frame.loc[np.sort(selected)].reset_index(drop=True)


def values(frame: pd.DataFrame) -> np.ndarray:
    return frame.loc[:, CLASSIFIER_FEATURES].to_numpy(dtype=np.float32, copy=True)


def probability_column(classes: np.ndarray, label: str) -> int:
    return int(np.flatnonzero(classes == label)[0])


def operational_event_decision(
    probabilities: np.ndarray, classes: np.ndarray, fault_threshold: float, weather_threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    fault = probabilities[:, probability_column(classes, "sensor_fault")]
    weather = probabilities[:, probability_column(classes, "genuine_weather")]
    decisions = np.full(probabilities.shape[0], "normal", dtype=object)
    decisions[weather >= weather_threshold] = "genuine_weather"
    decisions[fault >= fault_threshold] = "sensor_fault"
    confidence = np.where(
        decisions == "sensor_fault", fault,
        np.where(decisions == "genuine_weather", weather, probabilities[:, probability_column(classes, "normal")]),
    )
    return decisions.astype(str), confidence


def event_labels(frame: pd.DataFrame) -> np.ndarray:
    return frame["event_label"].to_numpy(dtype=str)


def evaluate(
    frame: pd.DataFrame,
    event_model: object,
    root_model: object,
    policy: dict[str, object],
) -> tuple[dict[str, object], pd.DataFrame]:
    x_values = values(frame)
    y_event = event_labels(frame)
    event_probabilities = event_model.predict_proba(x_values)
    event_classes = np.asarray(event_model.classes_, dtype=str)
    event_decisions, event_confidence = operational_event_decision(
        event_probabilities, event_classes,
        float(policy["fault_probability_threshold"]), float(policy["weather_probability_threshold"]),
    )
    event_selective = event_decisions.astype(object)
    uncertain_action = (event_decisions != "normal") & (event_confidence < float(policy["event_abstain_threshold"]))
    event_selective[uncertain_action] = "unknown"

    fault_probability = event_probabilities[:, probability_column(event_classes, "sensor_fault")]
    binary_labels = (y_event == "sensor_fault").astype(np.int8)
    weather_flags = (y_event == "genuine_weather").astype(np.int8)
    binary = point_metrics(
        binary_labels, fault_probability, float(policy["fault_probability_threshold"]),
        frame["station_id"].astype(str).tolist(), frame["emitted_timestamp_utc"].astype(str).tolist(), weather_flags,
    )
    binary_predictions = fault_probability >= float(policy["fault_probability_threshold"])
    binary["episode_detection"] = episode_metrics(
        binary_labels, binary_predictions, frame["episode_id"].fillna("").astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), frame["anomaly_type"].astype(str).tolist(),
    )

    event_report = classification_report(y_event, event_decisions, EVENT_CLASSES)
    event_report["calibration"] = {
        "expected_calibration_error": expected_calibration_error(event_probabilities, y_event, event_classes),
        "multiclass_brier_score": multiclass_brier_score(event_probabilities, y_event, event_classes),
    }
    event_report["abstention"] = {
        "threshold": float(policy["event_abstain_threshold"]),
        "unknown_rows": int(np.sum(event_selective == "unknown")),
        "coverage": float(np.mean(event_selective != "unknown")),
        "accepted_accuracy": float(np.mean(event_selective[event_selective != "unknown"] == y_event[event_selective != "unknown"])),
    }

    root_probabilities = root_model.predict_proba(x_values)
    root_classes = np.asarray(root_model.classes_, dtype=str)
    root_indices = np.argmax(root_probabilities, axis=1)
    root_predictions = root_classes[root_indices]
    root_confidence = np.max(root_probabilities, axis=1)
    actual_fault = y_event == "sensor_fault"
    oracle_root = classification_report(
        frame.loc[actual_fault, "anomaly_type"].to_numpy(dtype=str), root_predictions[actual_fault], root_classes.tolist(),
    )
    oracle_root["calibration"] = {
        "expected_calibration_error": expected_calibration_error(
            root_probabilities[actual_fault], frame.loc[actual_fault, "anomaly_type"].to_numpy(dtype=str), root_classes,
        ),
        "multiclass_brier_score": multiclass_brier_score(
            root_probabilities[actual_fault], frame.loc[actual_fault, "anomaly_type"].to_numpy(dtype=str), root_classes,
        ),
    }

    final_root = np.full(frame.shape[0], "not_a_fault", dtype=object)
    detected_fault = event_decisions == "sensor_fault"
    accepted_root = detected_fault & (root_confidence >= float(policy["root_abstain_threshold"]))
    final_root[detected_fault] = "unknown_fault"
    final_root[accepted_root] = root_predictions[accepted_root]
    true_root = frame.loc[actual_fault, "anomaly_type"].to_numpy(dtype=str)
    predicted_root = final_root[actual_fault].astype(str)
    diagnosed = ~np.isin(predicted_root, ["not_a_fault", "unknown_fault"])
    end_to_end = {
        "fault_rows": int(np.sum(actual_fault)),
        "correct_root_cause_rows": int(np.sum(predicted_root == true_root)),
        "exact_accuracy": float(np.mean(predicted_root == true_root)),
        "diagnostic_coverage": float(np.mean(diagnosed)),
        "accepted_root_accuracy": float(np.mean(predicted_root[diagnosed] == true_root[diagnosed])) if np.any(diagnosed) else 0.0,
        "missed_detection_rows": int(np.sum(predicted_root == "not_a_fault")),
        "unknown_fault_rows": int(np.sum(predicted_root == "unknown_fault")),
    }

    predictions = frame.loc[:, ["row_id", "station_id", "emitted_timestamp_utc", "event_label", "anomaly_type", "episode_id"]].copy()
    predictions["fault_probability"] = fault_probability
    predictions["weather_probability"] = event_probabilities[:, probability_column(event_classes, "genuine_weather")]
    predictions["event_decision"] = event_decisions
    predictions["event_confidence"] = event_confidence
    predictions["selective_event_decision"] = event_selective
    predictions["root_cause_prediction"] = final_root
    predictions["root_cause_confidence"] = root_confidence
    result = {
        "rows": int(frame.shape[0]),
        "binary_fault_detection": binary,
        "event_decision": event_report,
        "oracle_root_cause": oracle_root,
        "end_to_end_root_cause": end_to_end,
    }
    return result, predictions


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_predictions(frame: pd.DataFrame, split: str) -> Path:
    output = PREDICTION_DIR / f"{split}_phase5_predictions.csv.gz"
    frame.to_csv(output, index=False, compression={"method": "gzip", "compresslevel": 6})
    return output


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard Phase 5 fault/event classifier", "",
        "The classifiers were trained on 2022, calibrated and frozen on 2023, then evaluated on the two untouched 2024 holdouts.", "",
        "## Frozen-test results", "",
        "| Split | Fault precision | Fault recall | Fault F1 | AUCPR | Episode recall | Weather recall | Weather false-alarm rate | Root accuracy (oracle) | Root accuracy (end-to-end) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("time_test", "station_test"):
        values = report["evaluation"][split]
        binary = values["binary_fault_detection"]
        event = values["event_decision"]
        weather_recall = event["per_class"]["genuine_weather"]["recall"] if event["per_class"]["genuine_weather"]["support"] else 0.0
        lines.append(
            f"| {split} | {binary['precision']:.4f} | {binary['recall']:.4f} | {binary['f1']:.4f} | "
            f"{binary['aucpr']:.4f} | {binary['episode_detection']['recall']:.4f} | {weather_recall:.4f} | "
            f"{binary['weather_false_positive_rate']:.4f} | {values['oracle_root_cause']['accuracy']:.4f} | "
            f"{values['end_to_end_root_cause']['exact_accuracy']:.4f} |"
        )
    lines.extend([
        "", "## Interpretation", "",
        "The binary fault metrics are directly comparable with Phase 4 because they use the same detector-visible rows, weather hard negatives, and station-day definition. Oracle root-cause accuracy measures diagnosis after a fault is known; end-to-end accuracy also includes missed detections and abstentions.",
        "", "Dropout remains excluded from row-level classification and will be measured as a missing stream interval in Phase 7.",
        "", "## Artifacts", "",
        f"- Model bundle: `{report['artifacts']['model']}`",
        f"- Frozen policy: `{report['artifacts']['policy']}`",
        f"- Runtime: {report['runtime_seconds']:.2f} seconds",
        f"- Random seed: {RANDOM_SEED}",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    started = time.perf_counter()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    PREDICTION_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading 2022 training and 2023 validation features...")
    train = load_split("train")
    validation = load_split("validation")
    sampled = training_sample(train)

    print("Training episode-balanced event classifier...")
    x_train = values(sampled)
    y_train = event_labels(sampled)
    event_weights = episode_balanced_weights(y_train, sampled["episode_id"].fillna("").to_numpy(dtype=str))
    event_base = build_classifier(estimators=360)
    event_base.fit(x_train, y_train, sample_weight=event_weights)
    event_model = calibrate_prefit(event_base, values(validation), event_labels(validation))

    print("Training episode-balanced root-cause classifier...")
    train_fault = train.loc[train["event_label"] == "sensor_fault"].reset_index(drop=True)
    validation_fault = validation.loc[validation["event_label"] == "sensor_fault"].reset_index(drop=True)
    root_labels = train_fault["anomaly_type"].to_numpy(dtype=str)
    root_weights = episode_balanced_weights(root_labels, train_fault["episode_id"].fillna("").to_numpy(dtype=str))
    root_base = build_classifier(random_state=RANDOM_SEED + 1, estimators=420)
    root_base.fit(values(train_fault), root_labels, sample_weight=root_weights)
    root_model = calibrate_prefit(
        root_base, values(validation_fault), validation_fault["anomaly_type"].to_numpy(dtype=str),
    )

    print("Selecting probability and abstention policy on 2023 validation...")
    validation_probabilities = event_model.predict_proba(values(validation))
    event_classes = np.asarray(event_model.classes_, dtype=str)
    validation_events = event_labels(validation)
    fault_policy = choose_threshold(
        (validation_events == "sensor_fault").astype(np.int8),
        validation_probabilities[:, probability_column(event_classes, "sensor_fault")],
    )
    weather_policy = choose_threshold(
        (validation_events == "genuine_weather").astype(np.int8),
        validation_probabilities[:, probability_column(event_classes, "genuine_weather")],
    )
    validation_decisions, validation_confidence = operational_event_decision(
        validation_probabilities, event_classes, fault_policy["threshold"], weather_policy["threshold"],
    )
    action_mask = validation_decisions != "normal"
    event_abstention = choose_selective_threshold(
        validation_events[action_mask], validation_decisions[action_mask], validation_confidence[action_mask],
        target_accuracy=0.80,
    )
    validation_root_probabilities = root_model.predict_proba(values(validation_fault))
    validation_root_classes = np.asarray(root_model.classes_, dtype=str)
    validation_root_predictions = validation_root_classes[np.argmax(validation_root_probabilities, axis=1)]
    root_abstention = choose_selective_threshold(
        validation_fault["anomaly_type"].to_numpy(dtype=str), validation_root_predictions,
        np.max(validation_root_probabilities, axis=1), target_accuracy=0.75,
    )
    policy = {
        "status": "frozen_before_2024_evaluation",
        "selection_split": "validation (2023)",
        "fault_probability_threshold": fault_policy["threshold"],
        "weather_probability_threshold": weather_policy["threshold"],
        "event_abstain_threshold": event_abstention["threshold"],
        "root_abstain_threshold": root_abstention["threshold"],
        "validation_selection": {
            "fault": fault_policy, "weather": weather_policy,
            "event_abstention": event_abstention, "root_abstention": root_abstention,
        },
        "dropout_handling": "deferred to Phase 7 stateful stream-gap detection",
    }
    POLICY_FILE.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    feature_importance = sorted(
        zip(CLASSIFIER_FEATURES, event_base.feature_importances_), key=lambda item: item[1], reverse=True,
    )
    joblib.dump({
        "event_classifier": event_model, "root_cause_classifier": root_model,
        "feature_columns": list(CLASSIFIER_FEATURES), "event_classes": EVENT_CLASSES,
        "root_classes": root_model.classes_.tolist(), "policy": policy,
        "metadata": {"train_period": 2022, "calibration_period": 2023, "random_seed": RANDOM_SEED},
    }, MODEL_FILE)

    # No 2024 file is loaded before the model bundle and policy above are frozen.
    evaluation: dict[str, object] = {}
    outputs: list[Path] = []
    validation_result, validation_predictions = evaluate(validation, event_model, root_model, policy)
    evaluation["validation"] = validation_result
    outputs.append(write_predictions(validation_predictions, "validation"))
    del train, sampled, x_train, validation_predictions

    for split in ("time_test", "station_test"):
        print(f"Evaluating frozen Phase 5 models on {split}...")
        frame = load_split(split)
        split_result, predictions = evaluate(frame, event_model, root_model, policy)
        evaluation[split] = split_result
        outputs.append(write_predictions(predictions, split))

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
        writer.writeheader()
        for output in outputs:
            writer.writerow({
                "relative_path": output.relative_to(ROOT).as_posix(), "bytes": output.stat().st_size,
                "sha256": sha256(output),
            })

    report: dict[str, object] = {
        "phase": 5, "status": "complete",
        "training": {
            "sampled_rows": int(sampled.shape[0]) if "sampled" in locals() else int(np.sum(event_weights > 0)),
            "event_class_counts": pd.Series(y_train).value_counts().to_dict(),
            "root_class_counts": pd.Series(root_labels).value_counts().to_dict(),
            "episode_balanced": True,
            "feature_count": len(CLASSIFIER_FEATURES),
            "excluded_shortcut_features": ["hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos"],
        },
        "policy": policy,
        "evaluation": evaluation,
        "feature_importance_top_20": [{"feature": name, "importance": int(score)} for name, score in feature_importance[:20]],
        "artifacts": {
            "model": MODEL_FILE.relative_to(ROOT).as_posix(), "model_bytes": MODEL_FILE.stat().st_size,
            "policy": POLICY_FILE.relative_to(ROOT).as_posix(),
            "prediction_manifest": MANIFEST.relative_to(ROOT).as_posix(),
        },
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "logical_cpu_count": os.cpu_count(),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)
    print(json.dumps({
        "status": "complete",
        "time_test": evaluation["time_test"]["binary_fault_detection"],
        "station_test": evaluation["station_test"]["binary_fault_detection"],
        "runtime_seconds": report["runtime_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()

"""Improve correction coverage with sensor-specific models and safe repair tiers."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.correction.estimators import (  # noqa: E402
    CHANGE_TOLERANCE, CORRECTABLE_FAULTS, ORIGINAL_COLUMNS, SENSORS, VALUE_COLUMNS,
    correction_candidates, infer_affected_sensors,
)
from skyguard.correction.policy import correct_value  # noqa: E402
from skyguard.evaluation.classification import (  # noqa: E402
    choose_threshold_for_precision, episode_balanced_weights, expected_calibration_error,
)
from skyguard.models.classification import (  # noqa: E402
    build_binary_classifier, calibrate_prefit,
)
from skyguard.features.phase10 import PHASE10_FEATURES  # noqa: E402


FEATURE_DIR = ROOT / "data" / "features_phase10"
PREDICTION_DIR = ROOT / "data" / "predictions_phase10"
INCIDENT_DIR = ROOT / "data" / "incidents"
MODEL_DIR = ROOT / "models"
CORRECTION_POLICY_FILE = MODEL_DIR / "correction_policy.json"
MODEL_FILE = MODEL_DIR / "sensor_repair_classifiers.joblib"
POLICY_FILE = MODEL_DIR / "safe_repair_policy.json"
REPORT_JSON = ROOT / "reports" / "safe_repair.json"
REPORT_MD = ROOT / "reports" / "safe_repair.md"
MANIFEST = INCIDENT_DIR / "safe_repair_manifest.csv"
RANDOM_SEED = 26073
INTERVAL_HALF_WIDTH_LIMIT = {"temperature": 4.0, "pressure": 6.0, "humidity": 15.0}
AUTO_REPAIR_ENABLED = {"temperature": True, "pressure": True, "humidity": False}
METADATA = [
    "row_id", "station_id", "emitted_timestamp_utc", "anomaly_type", "anomaly_sensor", "episode_id",
    "is_anomaly", "is_weather_event", "available_to_detector", "original_temperature_c",
    "original_pressure_hpa", "original_relative_humidity_pct",
]
DETECTOR_COLUMNS = [
    "row_id", "fault_probability", "weather_probability", "event_decision",
    "root_cause_prediction", "root_cause_confidence",
]


def load_split(split: str, include_predictions: bool) -> pd.DataFrame:
    frame = pd.read_csv(
        FEATURE_DIR / f"{split}_features.csv.gz",
        usecols=sorted(set(PHASE10_FEATURES + tuple(METADATA))), low_memory=False,
    )
    frame = frame.loc[frame["available_to_detector"] == 1].reset_index(drop=True)
    if include_predictions:
        predictions = pd.read_csv(
            PREDICTION_DIR / f"{split}_phase10_final_predictions.csv.gz", usecols=DETECTOR_COLUMNS,
        )
        frame = frame.merge(predictions, on="row_id", how="inner", validate="one_to_one")
    return frame


def changed_target(frame: pd.DataFrame, sensor: str) -> np.ndarray:
    affected = frame["anomaly_sensor"].fillna("").astype(str).map(
        lambda value: sensor in {item.strip() for item in value.split(",")}
    ).to_numpy()
    reported = pd.to_numeric(frame[VALUE_COLUMNS[sensor]], errors="coerce").to_numpy()
    original = pd.to_numeric(frame[ORIGINAL_COLUMNS[sensor]], errors="coerce").to_numpy()
    changed = np.isfinite(reported) & np.isfinite(original) & (np.abs(reported - original) > CHANGE_TOLERANCE[sensor])
    correctable_fault = (
        (frame["is_anomaly"].to_numpy() == 1)
        & frame["anomaly_type"].isin(CORRECTABLE_FAULTS).to_numpy()
    )
    return (correctable_fault & affected & changed).astype(np.int8)


def sample_training(frame: pd.DataFrame, target: np.ndarray, sensor_index: int) -> np.ndarray:
    rng = np.random.default_rng(RANDOM_SEED + sensor_index)
    positive = np.flatnonzero(target == 1)
    non_normal = np.flatnonzero((frame["is_anomaly"].to_numpy() == 1) | (frame["is_weather_event"].to_numpy() == 1))
    normal = np.flatnonzero((frame["is_anomaly"].to_numpy() == 0) & (frame["is_weather_event"].to_numpy() == 0))
    sampled_normal = rng.choice(normal, size=min(30000, normal.size), replace=False)
    return np.unique(np.concatenate([positive, non_normal, sampled_normal]))


def safe_auto_gate(row: pd.Series, sensor: str, correction: dict[str, object] | None) -> tuple[bool, str]:
    if not AUTO_REPAIR_ENABLED[sensor]:
        return False, "automatic humidity replacement is disabled because uncertainty calibration is not stable across holdouts"
    if correction is None:
        return False, "no causal correction candidate"
    base_candidates = correction_candidates(row, sensor)
    independent_candidates = len([key for key in base_candidates if key != "causal_ensemble"])
    half_width = float(correction["interval_half_width"])
    if independent_candidates < 3:
        return False, "fewer than three causal estimates are available"
    if half_width > INTERVAL_HALF_WIDTH_LIMIT[sensor]:
        return False, "uncertainty interval is too wide for automatic replacement"
    return True, "high sensor probability, three or more causal estimates, and a narrow adaptive interval"


def evaluate_sensor(
    frame: pd.DataFrame, sensor: str, probabilities: np.ndarray, sensor_policy: dict[str, object],
    correction_policy: dict[str, object],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    target = changed_target(frame, sensor)
    positives = int(np.sum(target))
    action_records: list[dict[str, object]] = []
    metrics: dict[str, object] = {}
    review_threshold = float(sensor_policy["review"]["threshold"])
    auto_threshold = float(sensor_policy["auto"]["threshold"])

    for tier, threshold in (("review", review_threshold), ("auto", auto_threshold)):
        selected_mask = probabilities >= threshold
        if tier == "review":
            detector_fallback = np.asarray([
                str(row.get("event_decision", "")) == "sensor_fault"
                and sensor in infer_affected_sensors(row, str(row.get("root_cause_prediction", "unknown_fault")))
                for _, row in frame.iterrows()
            ], dtype=bool)
            selected_mask |= detector_fallback
        selected = np.flatnonzero(selected_mask)
        applied: list[dict[str, float | bool]] = []
        for index in selected:
            row = frame.iloc[index]
            predicted_root = str(row.get("root_cause_prediction", "unknown_fault"))
            correction = correct_value(row, sensor, predicted_root, correction_policy)
            gate_ok, gate_reason = safe_auto_gate(row, sensor, correction)
            if tier == "auto" and not gate_ok:
                continue
            if correction is None:
                continue
            reported = float(row[VALUE_COLUMNS[sensor]])
            original = float(row[ORIGINAL_COLUMNS[sensor]])
            if not math.isfinite(reported) or not math.isfinite(original):
                continue
            estimate = float(correction["estimate"])
            is_true = bool(target[index])
            applied.append({
                "true": is_true, "pre_error": abs(reported - original), "post_error": abs(estimate - original),
                "squared_error": (estimate - original) ** 2,
                "covered": correction["interval_lower"] <= original <= correction["interval_upper"],
            })
            if tier == "review":
                auto_candidate = probabilities[index] >= auto_threshold
                auto_ok, auto_reason = safe_auto_gate(row, sensor, correction)
                repair_tier = "auto_repair_eligible" if auto_candidate and auto_ok else "manual_review"
                reason = auto_reason if auto_candidate else "sensor probability is below the high-precision auto-repair threshold"
                action_records.append({
                    "action_id": "RPR-" + hashlib.sha1(f"{row['row_id']}|{sensor}".encode()).hexdigest()[:14].upper(),
                    "row_id": str(row["row_id"]), "station_id": str(row["station_id"]),
                    "timestamp_utc": str(row["emitted_timestamp_utc"]), "sensor": sensor,
                    "sensor_change_probability": float(probabilities[index]), "tier": repair_tier,
                    "reported_value": reported, "estimated_value": estimate,
                    "interval_lower": float(correction["interval_lower"]),
                    "interval_upper": float(correction["interval_upper"]),
                    "method": correction["method"], "safety_reason": reason,
                    "automatic_application": repair_tier == "auto_repair_eligible",
                })
        tp = sum(bool(item["true"]) for item in applied)
        fp = len(applied) - tp
        true_items = [item for item in applied if item["true"]]
        false_items = [item for item in applied if not item["true"]]
        metrics[tier] = {
            "true_changed_points": positives, "proposed_corrections": len(applied),
            "true_positive_corrections": tp, "false_positive_corrections": fp,
            "precision": tp / len(applied) if applied else 0.0,
            "coverage_recall": tp / positives if positives else 0.0,
            "corrected_mae_on_true_points": float(np.mean([item["post_error"] for item in true_items])) if true_items else None,
            "corrected_rmse_on_true_points": float(np.sqrt(np.mean([item["squared_error"] for item in true_items]))) if true_items else None,
            "reported_mae_on_true_points": float(np.mean([item["pre_error"] for item in true_items])) if true_items else None,
            "interval_coverage_on_true_points": float(np.mean([item["covered"] for item in true_items])) if true_items else None,
            "mean_false_correction_harm": float(np.mean([item["post_error"] for item in false_items])) if false_items else 0.0,
            "maximum_false_correction_harm": float(np.max([item["post_error"] for item in false_items])) if false_items else 0.0,
        }
    return metrics, action_records


def write_actions(split: str, actions: list[dict[str, object]]) -> Path:
    INCIDENT_DIR.mkdir(parents=True, exist_ok=True)
    output = INCIDENT_DIR / f"{split}_repair_actions.jsonl.gz"
    actions.sort(key=lambda item: (item["timestamp_utc"], item["station_id"], item["sensor"]))
    with gzip.open(output, "wt", encoding="utf-8", compresslevel=6) as handle:
        for action in actions:
            handle.write(json.dumps(action, allow_nan=False) + "\n")
    return output


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard Phase 6.1 safe-repair improvement", "",
        "Dedicated sensor-change models recover correction opportunities independently of root-cause classification. Review and auto-repair thresholds were frozen on 2023 before 2024 evaluation.", "",
        "## Frozen 2024 results", "",
        "| Test | Sensor | Tier | Precision | Coverage | Corrected MAE | Interval coverage | False corrections | Mean false-correction harm |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("time_test", "station_test"):
        for sensor in SENSORS:
            for tier in ("review", "auto"):
                item = report["evaluation"][split][sensor][tier]
                mae = "n/a" if item["corrected_mae_on_true_points"] is None else f"{item['corrected_mae_on_true_points']:.4f}"
                interval = "n/a" if item["interval_coverage_on_true_points"] is None else f"{item['interval_coverage_on_true_points']:.4f}"
                lines.append(
                    f"| {split} | {sensor} | {tier} | {item['precision']:.4f} | {item['coverage_recall']:.4f} | "
                    f"{mae} | {interval} | {item['false_positive_corrections']} | {item['mean_false_correction_harm']:.4f} |"
                )
    lines.extend([
        "", "## Safety rule", "",
        "Only the auto tier may be applied without review. It requires the high-precision sensor threshold, at least three causal estimates, and an adaptive interval narrower than the sensor-specific safety limit. Review-tier outputs remain advisory.",
        "", "The test metrics are reported without changing thresholds after inspection. Confirmed operational deployment would still require real maintenance labels and operator approval.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    started = time.perf_counter()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    INCIDENT_DIR.mkdir(parents=True, exist_ok=True)
    correction_policy = json.loads(CORRECTION_POLICY_FILE.read_text(encoding="utf-8"))
    print("Training sensor-specific changed-value models on 2022...")
    train = load_split("train", include_predictions=False)
    validation = load_split("validation", include_predictions=True)
    x_validation = validation.loc[:, PHASE10_FEATURES].to_numpy(dtype=np.float32)
    models: dict[str, object] = {}
    policies: dict[str, object] = {}
    training_counts: dict[str, object] = {}

    for sensor_index, sensor in enumerate(SENSORS):
        target = changed_target(train, sensor)
        selected = sample_training(train, target, sensor_index)
        x_train = train.loc[selected, PHASE10_FEATURES].to_numpy(dtype=np.float32)
        y_train = target[selected]
        weights = episode_balanced_weights(y_train, train.loc[selected, "episode_id"].fillna("").to_numpy(dtype=str))
        base = build_binary_classifier(RANDOM_SEED + 10 + sensor_index, estimators=320)
        base.fit(x_train, y_train, sample_weight=weights)
        validation_target = changed_target(validation, sensor)
        calibrated = calibrate_prefit(base, x_validation, validation_target)
        scores = calibrated.predict_proba(x_validation)[:, 1]
        policies[sensor] = {
            "review": choose_threshold_for_precision(validation_target, scores, 0.70),
            "auto": choose_threshold_for_precision(validation_target, scores, 0.98),
            "validation_ece": expected_calibration_error(
                np.column_stack([1.0 - scores, scores]), validation_target.astype(str), np.array(["0", "1"]),
            ),
            "interval_half_width_limit": INTERVAL_HALF_WIDTH_LIMIT[sensor],
            "automatic_repair_enabled": AUTO_REPAIR_ENABLED[sensor],
        }
        models[sensor] = calibrated
        training_counts[sensor] = {"sampled_rows": int(selected.size), "positive_rows": int(np.sum(y_train))}

    policy_document = {
        "status": "frozen_before_2024_evaluation", "selection_split": "validation (2023)",
        "input_contract": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
        "dew_point_used_by_detector": False,
        "review_target_precision": 0.70, "auto_target_precision": 0.98,
        "auto_safety": "three causal candidates and sensor-specific maximum interval half-width",
        "review_fusion": "union of compliant detector proposals and sensor-specific rescue probability",
        "automatic_repair_enabled": AUTO_REPAIR_ENABLED,
        "sensors": policies,
    }
    POLICY_FILE.write_text(json.dumps(policy_document, indent=2), encoding="utf-8")
    joblib.dump({
        "models": models, "feature_columns": list(PHASE10_FEATURES), "policy": policy_document,
        "metadata": {"training_period": 2022, "calibration_period": 2023, "random_seed": RANDOM_SEED,
                     "input_contract": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
                     "dew_point_used_by_detector": False},
    }, MODEL_FILE)

    evaluation: dict[str, object] = {}
    outputs: dict[str, object] = {}
    files: list[Path] = []
    for split, frame in [("validation", validation)]:
        split_metrics: dict[str, object] = {}
        actions: list[dict[str, object]] = []
        matrix = frame.loc[:, PHASE10_FEATURES].to_numpy(dtype=np.float32)
        for sensor in SENSORS:
            probabilities = models[sensor].predict_proba(matrix)[:, 1]
            split_metrics[sensor], sensor_actions = evaluate_sensor(
                frame, sensor, probabilities, policies[sensor], correction_policy,
            )
            actions.extend(sensor_actions)
        evaluation[split] = split_metrics
        action_file = write_actions(split, actions)
        files.append(action_file)
        outputs[split] = {"actions": len(actions), "auto_eligible": sum(item["automatic_application"] for item in actions), "file": action_file.relative_to(ROOT).as_posix()}

    # Models and thresholds are persisted before either 2024 holdout is opened.
    for split in ("time_test", "station_test"):
        print(f"Evaluating frozen safe-repair policy on {split}...")
        frame = load_split(split, include_predictions=True)
        matrix = frame.loc[:, PHASE10_FEATURES].to_numpy(dtype=np.float32)
        split_metrics = {}
        actions = []
        for sensor in SENSORS:
            probabilities = models[sensor].predict_proba(matrix)[:, 1]
            split_metrics[sensor], sensor_actions = evaluate_sensor(
                frame, sensor, probabilities, policies[sensor], correction_policy,
            )
            actions.extend(sensor_actions)
        evaluation[split] = split_metrics
        action_file = write_actions(split, actions)
        files.append(action_file)
        outputs[split] = {"actions": len(actions), "auto_eligible": sum(item["automatic_application"] for item in actions), "file": action_file.relative_to(ROOT).as_posix()}

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
        writer.writeheader()
        for path in files:
            writer.writerow({"relative_path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})

    report = {
        "phase": "6.1", "status": "complete", "training": training_counts,
        "policy": policy_document, "evaluation": evaluation, "outputs": outputs,
        "artifacts": {"model": MODEL_FILE.relative_to(ROOT).as_posix(), "policy": POLICY_FILE.relative_to(ROOT).as_posix(), "manifest": MANIFEST.relative_to(ROOT).as_posix()},
        "runtime_seconds": round(time.perf_counter() - started, 4),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    write_markdown(report)
    print(json.dumps({"status": "complete", "outputs": outputs, "time_test": evaluation["time_test"], "station_test": evaluation["station_test"], "runtime_seconds": report["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()

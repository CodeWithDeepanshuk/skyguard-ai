"""Fit and evaluate compliant corrections, incidents, explanations, and sensor health."""

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
    CORRECTABLE_FAULTS, ORIGINAL_COLUMNS, SENSORS, VALUE_COLUMNS, changed_from_original,
    infer_affected_sensors, number, sensor_evidence_score, true_affected_sensors,
)
from skyguard.correction.incidents import SensorHealthTracker, explain, recommendation, severity  # noqa: E402
from skyguard.correction.policy import correct_value, fit_correction_policy  # noqa: E402
from data.finalize_phase10 import evaluate as evaluate_phase10  # noqa: E402
from data.run_phase10_models import load_split as load_phase10_split  # noqa: E402


FEATURE_DIR = ROOT / "data" / "features_phase10"
PREDICTION_DIR = ROOT / "data" / "predictions_phase10"
OUTPUT_DIR = ROOT / "data" / "incidents"
MODEL_DIR = ROOT / "models"
CLASSIFIER_FILE = MODEL_DIR / "phase10_final.joblib"
POLICY_FILE = MODEL_DIR / "correction_policy.json"
REPORT_JSON = ROOT / "reports" / "correction_health.json"
REPORT_MD = ROOT / "reports" / "correction_health.md"
MANIFEST = OUTPUT_DIR / "manifest.csv"
AUDIT_COLUMNS = [
    "row_id", "station_id", "emitted_timestamp_utc", "anomaly_type", "anomaly_sensor",
    "is_anomaly", "available_to_detector", "original_temperature_c", "original_pressure_hpa",
    "original_relative_humidity_pct",
]
PREDICTION_COLUMNS = [
    "row_id", "fault_probability", "weather_probability", "event_decision",
    "root_cause_prediction", "root_cause_confidence",
]


def load_split(split: str, classifier_features: list[str]) -> pd.DataFrame:
    usecols = sorted(set(classifier_features + AUDIT_COLUMNS))
    frame = pd.read_csv(FEATURE_DIR / f"{split}_features.csv.gz", usecols=usecols, low_memory=False)
    frame = frame.loc[frame["available_to_detector"] == 1].copy()
    predictions = pd.read_csv(
        PREDICTION_DIR / f"{split}_phase10_final_predictions.csv.gz", usecols=PREDICTION_COLUMNS, low_memory=False,
    )
    merged = frame.merge(predictions, on="row_id", how="inner", validate="one_to_one")
    if merged.shape[0] != frame.shape[0]:
        raise RuntimeError(f"{split} feature/prediction row mismatch")
    return merged


def ensure_validation_predictions(artifact: dict[str, object]) -> None:
    """Create the 2023 Phase 10 prediction table needed to freeze correction policy."""
    output = PREDICTION_DIR / "validation_phase10_final_predictions.csv.gz"
    frame = load_phase10_split("validation")
    _, predictions = evaluate_phase10(
        frame, artifact["event_model"], tuple(artifact["event_features"]), artifact["root_model"],
        artifact["policy"]["known_station"], float(artifact["policy"]["weather_threshold"]),
        float(artifact["policy"]["root_threshold"]),
    )
    predictions.to_csv(output, index=False, compression={"method": "gzip", "compresslevel": 6})


def summarize_corrections(frame: pd.DataFrame, policy: dict[str, object], operational: bool) -> dict[str, object]:
    totals = {sensor: 0 for sensor in SENSORS}
    entries: dict[str, list[dict[str, float]]] = {sensor: [] for sensor in SENSORS}
    faults = frame.loc[(frame["is_anomaly"] == 1) & frame["anomaly_type"].isin(CORRECTABLE_FAULTS)]
    for _, row in faults.iterrows():
        true_sensors = true_affected_sensors(row.get("anomaly_sensor", ""))
        predicted_root = str(row.get("root_cause_prediction", "unknown_fault"))
        inferred = infer_affected_sensors(row, predicted_root) if operational and row["event_decision"] == "sensor_fault" else []
        for sensor in true_sensors:
            if not changed_from_original(row, sensor):
                continue
            totals[sensor] += 1
            if operational and (row["event_decision"] != "sensor_fault" or sensor not in inferred):
                continue
            fault_for_policy = predicted_root if operational else str(row["anomaly_type"])
            correction = correct_value(row, sensor, fault_for_policy, policy)
            if correction is None:
                continue
            original = number(row, ORIGINAL_COLUMNS[sensor])
            reported = number(row, VALUE_COLUMNS[sensor])
            estimate = float(correction["estimate"])
            entries[sensor].append({
                "reported_error": abs(reported - original),
                "corrected_error": abs(estimate - original),
                "corrected_squared_error": (estimate - original) ** 2,
                "covered": float(correction["interval_lower"] <= original <= correction["interval_upper"]),
            })

    result: dict[str, object] = {}
    for sensor in SENSORS:
        values = entries[sensor]
        corrected = len(values)
        reported_mae = float(np.mean([item["reported_error"] for item in values])) if values else None
        corrected_mae = float(np.mean([item["corrected_error"] for item in values])) if values else None
        result[sensor] = {
            "changed_affected_points": totals[sensor],
            "corrected_points": corrected,
            "coverage": corrected / totals[sensor] if totals[sensor] else 0.0,
            "reported_value_mae": reported_mae,
            "corrected_value_mae": corrected_mae,
            "corrected_value_rmse": float(np.sqrt(np.mean([item["corrected_squared_error"] for item in values]))) if values else None,
            "mae_reduction_percent": (
                100.0 * (1.0 - corrected_mae / reported_mae)
                if reported_mae and corrected_mae is not None else None
            ),
            "interval_90_coverage": float(np.mean([item["covered"] for item in values])) if values else None,
        }
    return result


def local_contributions(frame: pd.DataFrame, artifact: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    incidents = frame.loc[frame["event_decision"] == "sensor_fault"]
    if incidents.empty:
        return {}
    feature_columns = artifact["event_features"]
    base = artifact["event_model"].calibrated_classifiers_[0].estimator.estimator
    matrix = incidents.loc[:, feature_columns].to_numpy(dtype=np.float32)
    contributions = base.booster_.predict(matrix, pred_contrib=True)
    contributions = contributions.reshape(matrix.shape[0], len(base.classes_), len(feature_columns) + 1)
    class_index = int(np.flatnonzero(base.classes_ == "sensor_fault")[0])
    result: dict[str, list[dict[str, object]]] = {}
    for row_index, row_id in enumerate(incidents["row_id"].astype(str)):
        values = contributions[row_index, class_index, :-1]
        strongest = np.argsort(np.abs(values))[-3:][::-1]
        result[row_id] = [
            {"feature": feature_columns[index], "contribution": round(float(values[index]), 5)}
            for index in strongest
        ]
    return result


def generate_incidents(
    frame: pd.DataFrame, split: str, policy: dict[str, object], artifact: dict[str, object],
) -> tuple[Path, Path, int]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    contribution_map = local_contributions(frame, artifact)
    tracker = SensorHealthTracker()
    incident_path = OUTPUT_DIR / f"{split}_incidents.jsonl.gz"
    health_path = OUTPUT_DIR / f"{split}_sensor_health.csv"
    incident_count = 0
    ordered = frame.loc[frame["event_decision"] == "sensor_fault"].sort_values(
        ["emitted_timestamp_utc", "station_id", "row_id"]
    )
    with gzip.open(incident_path, "wt", encoding="utf-8", compresslevel=6) as handle:
        for _, row in ordered.iterrows():
            root = str(row["root_cause_prediction"])
            fault_probability = float(row["fault_probability"])
            sensors = infer_affected_sensors(row, root)
            evidence_score = max((sensor_evidence_score(row, sensor) for sensor in sensors), default=0.0)
            level = severity(fault_probability, root, evidence_score)
            corrections: list[dict[str, object]] = []
            sensor_health: dict[str, float] = {}
            for sensor in sensors:
                correction = correct_value(row, sensor, root, policy)
                if correction is not None:
                    reported = number(row, VALUE_COLUMNS[sensor])
                    correction["reported_value"] = reported if reported is not None and math.isfinite(reported) else None
                    corrections.append(correction)
                sensor_health[sensor] = tracker.update(
                    str(row["station_id"]), sensor, str(row["emitted_timestamp_utc"]), level, fault_probability,
                )
            explanation, evidence = explain(row, sensors, root, fault_probability)
            lowest_health = min(sensor_health.values(), default=100.0)
            incident_id = "INC-" + hashlib.sha1(f"{split}|{row['row_id']}".encode("utf-8")).hexdigest()[:14].upper()
            incident = {
                "incident_id": incident_id, "row_id": str(row["row_id"]), "split": split,
                "station_id": str(row["station_id"]), "timestamp_utc": str(row["emitted_timestamp_utc"]),
                "decision": "probable_sensor_fault", "fault_probability": fault_probability,
                "root_cause": root, "root_cause_confidence": float(row["root_cause_confidence"]),
                "affected_sensors": sensors, "severity": level, "explanation": explanation,
                "evidence": evidence, "model_feature_contributions": contribution_map.get(str(row["row_id"]), []),
                "corrections": corrections, "sensor_health_after_incident": sensor_health,
                "recommended_action": recommendation(level, lowest_health),
                "provenance": "SIH-compliant Phase 10 three-parameter decision plus causal correction policy",
            }
            handle.write(json.dumps(incident, allow_nan=False) + "\n")
            incident_count += 1

    stations = sorted(frame["station_id"].astype(str).unique())
    with health_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "station_id", "sensor", "health_score", "status", "incident_count", "severity_counts",
            "last_incident_utc", "health_trend", "degradation_slope_points_per_day",
            "projected_health_7d", "degradation_risk_7d", "maintenance_horizon_days",
            "forecast_confidence", "forecast_method", "recommended_action",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for station in stations:
            for sensor in SENSORS:
                snapshot = tracker.snapshot(station, sensor)
                snapshot["severity_counts"] = json.dumps(snapshot["severity_counts"], sort_keys=True)
                writer.writerow(snapshot)
    return incident_path, health_path, incident_count


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard Phase 6 correction, explanation, and health report", "",
        "Correction methods and 90% uncertainty widths were selected on 2023 validation and frozen before either 2024 split was loaded.", "",
        "## Causal correction results", "",
        "| Test | Mode | Sensor | Changed points | Correction coverage | Reported MAE | Corrected MAE | Corrected RMSE | MAE reduction | Interval coverage |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("time_test", "station_test"):
        for mode in ("oracle_policy", "operational"):
            for sensor in SENSORS:
                item = report["evaluation"][split][mode][sensor]
                def fmt(value: object) -> str:
                    return "n/a" if value is None else f"{float(value):.4f}"
                lines.append(
                    f"| {split} | {mode} | {sensor} | {item['changed_affected_points']} | {item['coverage']:.4f} | "
                    f"{fmt(item['reported_value_mae'])} | {fmt(item['corrected_value_mae'])} | {fmt(item['corrected_value_rmse'])} | "
                    f"{fmt(item['mae_reduction_percent'])}% | {fmt(item['interval_90_coverage'])} |"
                )
    lines.extend([
        "", "## Scope", "",
        "Oracle-policy results isolate corrected-value quality using the known affected sensor and fault family. Operational results include Phase 10 misses, inferred affected sensors, root-cause uncertainty, and candidate availability. Original clean values are used only for offline metrics and never appear in incident files.",
        "", f"Generated incidents: validation {report['outputs']['validation']['incidents']:,}, time test {report['outputs']['time_test']['incidents']:,}, unseen stations {report['outputs']['station_test']['incidents']:,}.",
        "", "Communication-only and timestamp faults receive an explanation but no fabricated physical correction. Dropout remains a Phase 7 stream-gap task.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    artifact = joblib.load(CLASSIFIER_FILE)
    classifier_features = list(artifact["event_features"])
    ensure_validation_predictions(artifact)

    print("Selecting causal correction policy on 2023 validation...")
    validation = load_split("validation", classifier_features)
    validation_faults = validation.loc[validation["is_anomaly"] == 1]
    policy = fit_correction_policy(validation_faults.to_dict(orient="records"))
    policy["status"] = "frozen_before_2024_evaluation"
    policy["selection_split"] = "validation (2023)"
    POLICY_FILE.write_text(json.dumps(policy, indent=2), encoding="utf-8")

    evaluation: dict[str, object] = {}
    outputs: dict[str, dict[str, object]] = {}
    artifacts: list[Path] = []
    for split, frame in [("validation", validation)]:
        evaluation[split] = {
            "oracle_policy": summarize_corrections(frame, policy, operational=False),
            "operational": summarize_corrections(frame, policy, operational=True),
        }
        incident_file, health_file, count = generate_incidents(frame, split, policy, artifact)
        artifacts.extend([incident_file, health_file])
        outputs[split] = {"incidents": count, "incident_file": incident_file.relative_to(ROOT).as_posix(), "health_file": health_file.relative_to(ROOT).as_posix()}

    # The frozen 2024 files are loaded only after correction_policy.json is persisted.
    for split in ("time_test", "station_test"):
        print(f"Evaluating frozen Phase 6 policy on {split}...")
        frame = load_split(split, classifier_features)
        evaluation[split] = {
            "oracle_policy": summarize_corrections(frame, policy, operational=False),
            "operational": summarize_corrections(frame, policy, operational=True),
        }
        incident_file, health_file, count = generate_incidents(frame, split, policy, artifact)
        artifacts.extend([incident_file, health_file])
        outputs[split] = {"incidents": count, "incident_file": incident_file.relative_to(ROOT).as_posix(), "health_file": health_file.relative_to(ROOT).as_posix()}

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
        writer.writeheader()
        for path in artifacts:
            writer.writerow({"relative_path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})

    report = {
        "phase": 6, "status": "complete",
        "policy": policy,
        "evaluation": evaluation,
        "outputs": outputs,
        "artifacts": {
            "correction_policy": POLICY_FILE.relative_to(ROOT).as_posix(),
            "manifest": MANIFEST.relative_to(ROOT).as_posix(),
        },
        "runtime_seconds": round(time.perf_counter() - started, 4),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    write_markdown(report)
    print(json.dumps({
        "status": "complete", "outputs": outputs,
        "time_test_operational": evaluation["time_test"]["operational"],
        "station_test_operational": evaluation["station_test"]["operational"],
        "runtime_seconds": report["runtime_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()

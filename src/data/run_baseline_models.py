"""Train, freeze, and evaluate SkyGuard Phase 4 anomaly baselines."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.evaluation.metrics import (  # noqa: E402
    alert_run_metrics, choose_threshold, episode_metrics, fault_recall, point_metrics,
)
from skyguard.models.baselines import score_row  # noqa: E402
from skyguard.models.isolation import ISOLATION_FEATURES, anomaly_scores, build_model, save_model  # noqa: E402


FEATURE_DIR = ROOT / "data" / "features"
PREDICTION_DIR = ROOT / "data" / "predictions"
MODEL_DIR = ROOT / "models"
THRESHOLD_FILE = MODEL_DIR / "baseline_thresholds.json"
MODEL_FILE = MODEL_DIR / "isolation_forest.joblib"
REPORT_JSON = ROOT / "reports" / "baseline_models.json"
REPORT_MD = ROOT / "reports" / "baseline_models.md"
MANIFEST_FILE = PREDICTION_DIR / "manifest.csv"
SCORE_NAMES = ("qc_rules", "hampel", "ewma", "neighbor", "combined", "isolation_forest")
OUTPUT_SPLITS = ("validation", "time_test", "station_test")
DEFERRED_FAULTS = ("dropout",)


@dataclass
class SplitData:
    split: str
    row_ids: list[str]
    stations: list[str]
    timestamps: list[str]
    anomaly_types: list[str]
    episode_ids: list[str]
    labels: np.ndarray
    weather: np.ndarray
    available: np.ndarray
    features: np.ndarray
    deterministic: dict[str, np.ndarray]

    @property
    def eligible(self) -> np.ndarray:
        return self.available == 1


def to_float(value: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return math.nan
    return parsed if math.isfinite(parsed) else math.nan


def load_split(split: str, include_scores: bool = True) -> SplitData:
    path = FEATURE_DIR / f"{split}_features.csv.gz"
    rows: list[str] = []
    stations: list[str] = []
    timestamps: list[str] = []
    anomaly_types: list[str] = []
    episode_ids: list[str] = []
    labels: list[int] = []
    weather: list[int] = []
    available: list[int] = []
    feature_rows: list[list[float]] = []
    deterministic: dict[str, list[float]] = {name: [] for name in SCORE_NAMES[:-1]}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row["row_id"])
            stations.append(row["station_id"])
            timestamps.append(row["emitted_timestamp_utc"] or row["timestamp_utc"])
            anomaly_types.append(row["anomaly_type"])
            episode_ids.append(row["episode_id"])
            labels.append(int(row["is_anomaly"]))
            weather.append(int(row["is_weather_event"]))
            available.append(int(row["available_to_detector"]))
            feature_rows.append([to_float(row[column]) for column in ISOLATION_FEATURES])
            if include_scores:
                scores = score_row(row)
                for name, value in scores.items():
                    deterministic[name].append(value)
    return SplitData(
        split=split, row_ids=rows, stations=stations, timestamps=timestamps,
        anomaly_types=anomaly_types, episode_ids=episode_ids,
        labels=np.asarray(labels, dtype=np.int8), weather=np.asarray(weather, dtype=np.int8),
        available=np.asarray(available, dtype=np.int8), features=np.asarray(feature_rows, dtype=np.float32),
        deterministic={name: np.asarray(values, dtype=np.float64) for name, values in deterministic.items()},
    )


def score_all(data: SplitData, model: object) -> dict[str, np.ndarray]:
    scores = dict(data.deterministic)
    scores["isolation_forest"] = anomaly_scores(model, data.features)
    return scores


def evaluate_detector(data: SplitData, scores: np.ndarray, threshold: float) -> dict[str, object]:
    mask = data.eligible
    labels = data.labels[mask]
    masked_scores = scores[mask]
    stations = [value for value, keep in zip(data.stations, mask) if keep]
    timestamps = [value for value, keep in zip(data.timestamps, mask) if keep]
    anomaly_types = [value for value, keep in zip(data.anomaly_types, mask) if keep]
    episode_ids = [value for value, keep in zip(data.episode_ids, mask) if keep]
    weather = data.weather[mask]
    predictions = masked_scores >= threshold
    result = point_metrics(labels, masked_scores, threshold, stations, timestamps, weather)
    result["row_recall_by_fault"] = fault_recall(labels, predictions, anomaly_types)
    result["true_episode_detection"] = episode_metrics(
        labels, predictions, episode_ids, timestamps, anomaly_types,
    )
    result["predicted_alert_runs"] = alert_run_metrics(labels, predictions, stations, timestamps)
    result["excluded_unavailable_rows"] = int(np.sum(~mask))
    result["deferred_fault_types"] = list(DEFERRED_FAULTS)
    return result


def write_predictions(data: SplitData, scores: dict[str, np.ndarray], thresholds: dict[str, dict[str, float]]) -> Path:
    PREDICTION_DIR.mkdir(parents=True, exist_ok=True)
    output = PREDICTION_DIR / f"{data.split}_baseline_scores.csv.gz"
    fields = [
        "row_id", "station_id", "timestamp_utc", "is_anomaly", "is_weather_event", "anomaly_type",
        "episode_id", "available_to_detector",
    ]
    for name in SCORE_NAMES:
        fields.extend([f"{name}_score", f"{name}_prediction"])
    with gzip.open(output, "wt", encoding="utf-8", newline="", compresslevel=6) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row_id in enumerate(data.row_ids):
            output_row: dict[str, object] = {
                "row_id": row_id, "station_id": data.stations[index], "timestamp_utc": data.timestamps[index],
                "is_anomaly": int(data.labels[index]), "is_weather_event": int(data.weather[index]),
                "anomaly_type": data.anomaly_types[index], "episode_id": data.episode_ids[index],
                "available_to_detector": int(data.available[index]),
            }
            for name in SCORE_NAMES:
                output_row[f"{name}_score"] = f"{scores[name][index]:.8g}"
                output_row[f"{name}_prediction"] = (
                    int(scores[name][index] >= thresholds[name]["threshold"])
                    if data.available[index] else ""
                )
            writer.writerow(output_row)
    return output


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard Phase 4 baseline report", "",
        "Thresholds were selected on 2023 validation only, saved, and frozen before the 2024 time and unseen-station files were loaded.", "",
        "## Test results", "",
        "| Split | Detector | Precision | Recall | F1 | AUCPR | False alarms/station-day | Episode recall | Weather FPR |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("time_test", "station_test"):
        for detector in SCORE_NAMES:
            values = report["evaluation"][split][detector]
            lines.append(
                f"| {split} | {detector} | {values['precision']:.4f} | {values['recall']:.4f} | "
                f"{values['f1']:.4f} | {values['aucpr']:.4f} | {values['false_alarms_per_station_day']:.4f} | "
                f"{values['true_episode_detection']['recall']:.4f} | {values['weather_false_positive_rate']:.4f} |"
            )
    lines.extend([
        "", "## What the baselines establish", "",
        f"- Best 2024 time-holdout point F1: {max((report['evaluation']['time_test'][name]['f1'], name) for name in SCORE_NAMES)[1]} ({max(report['evaluation']['time_test'][name]['f1'] for name in SCORE_NAMES):.4f}).",
        f"- Best unseen-station point F1: {max((report['evaluation']['station_test'][name]['f1'], name) for name in SCORE_NAMES)[1]} ({max(report['evaluation']['station_test'][name]['f1'] for name in SCORE_NAMES):.4f}).",
        f"- Highest unseen-station episode recall: {max((report['evaluation']['station_test'][name]['true_episode_detection']['recall'], name) for name in SCORE_NAMES)[1]} ({max(report['evaluation']['station_test'][name]['true_episode_detection']['recall'] for name in SCORE_NAMES):.4f}).",
        "- Neighbour comparison rejects the regional-weather hard negatives well and has the lowest unseen-station false-alarm rate.",
        "- Bias, gradual drift, duplicate packets, and some frozen faults remain difficult; these are the main targets for the supervised fault classifier and stateful replay phases.",
        "", "## Evaluation boundary", "",
        "Point metrics include every detector-visible row. Dropout rows are excluded because no value reaches a row-level detector; dropout evaluation is deferred to the stateful replay/communication-gap evaluator in Phase 7. Regional weather scenarios remain negative hard cases and are included in false-positive metrics.",
        "", "## Reproducibility", "",
        f"- Training rows used by Isolation Forest: {report['training']['normal_available_rows']:,}",
        f"- Isolation Forest fit time: {report['training']['fit_seconds']:.3f} seconds",
        f"- Saved model bytes: {report['artifacts']['model_bytes']:,}",
        f"- Total Phase 4 runtime: {report['runtime']['total_seconds']:.3f} seconds",
        "- Random seed: 26073",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    started = time.perf_counter()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    PREDICTION_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading 2022 training features...")
    train = load_split("train", include_scores=False)
    normal_mask = (train.labels == 0) & train.eligible
    model = build_model()
    fit_started = time.perf_counter()
    model.fit(train.features[normal_mask])
    fit_seconds = time.perf_counter() - fit_started
    del train

    print("Selecting thresholds using 2023 validation only...")
    validation = load_split("validation")
    validation_scores = score_all(validation, model)
    validation_mask = validation.eligible
    thresholds = {
        name: choose_threshold(validation.labels[validation_mask], scores[validation_mask])
        for name, scores in validation_scores.items()
    }
    threshold_document = {
        "status": "frozen_before_test_evaluation",
        "selection_split": "validation (2023)",
        "selection_metric": "maximum point-level F1; ties use stricter threshold",
        "eligible_rows": int(np.sum(validation_mask)),
        "excluded_faults": list(DEFERRED_FAULTS),
        "detectors": thresholds,
    }
    THRESHOLD_FILE.write_text(json.dumps(threshold_document, indent=2), encoding="utf-8")
    save_model(MODEL_FILE, model, {
        "training_split": "train (2022)", "training_filter": "normal detector-visible rows",
        "normal_available_rows": int(np.sum(normal_mask)), "random_seed": 26073,
    })

    # Locked test data is deliberately loaded only after thresholds and model are persisted.
    evaluation: dict[str, dict[str, object]] = {}
    outputs: list[Path] = []
    for split, data, scores in [("validation", validation, validation_scores)]:
        evaluation[split] = {
            name: evaluate_detector(data, values, thresholds[name]["threshold"])
            for name, values in scores.items()
        }
        outputs.append(write_predictions(data, scores, thresholds))

    for split in ("time_test", "station_test"):
        print(f"Evaluating frozen models on {split}...")
        data = load_split(split)
        split_scores = score_all(data, model)
        evaluation[split] = {
            name: evaluate_detector(data, values, thresholds[name]["threshold"])
            for name, values in split_scores.items()
        }
        outputs.append(write_predictions(data, split_scores, thresholds))

    with MANIFEST_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
        writer.writeheader()
        for output in outputs:
            writer.writerow({
                "relative_path": output.relative_to(ROOT).as_posix(), "bytes": output.stat().st_size,
                "sha256": sha256(output),
            })

    report: dict[str, object] = {
        "phase": 4,
        "status": "complete",
        "evaluation_contract": {
            "training": "2022 normal detector-visible rows",
            "threshold_selection": "2023 validation only",
            "locked_tests": ["2024 time holdout", "2024 four-station holdout"],
            "positive_class": "injected sensor/communication fault on a detector-visible row",
            "weather_scenarios": "negative hard cases",
            "deferred": "dropout is evaluated as a stream gap in Phase 7",
        },
        "training": {
            "normal_available_rows": int(np.sum(normal_mask)), "fit_seconds": round(fit_seconds, 4),
            "isolation_features": list(ISOLATION_FEATURES),
        },
        "thresholds": thresholds,
        "evaluation": evaluation,
        "artifacts": {
            "model": MODEL_FILE.relative_to(ROOT).as_posix(), "model_bytes": MODEL_FILE.stat().st_size,
            "thresholds": THRESHOLD_FILE.relative_to(ROOT).as_posix(),
            "prediction_manifest": MANIFEST_FILE.relative_to(ROOT).as_posix(),
        },
        "runtime": {
            "total_seconds": round(time.perf_counter() - started, 4),
            "logical_cpu_count": os.cpu_count(),
        },
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)
    print(json.dumps({
        "status": "complete", "thresholds": {key: value["threshold"] for key, value in thresholds.items()},
        "time_test_f1": {key: evaluation["time_test"][key]["f1"] for key in SCORE_NAMES},
        "station_test_f1": {key: evaluation["station_test"][key]["f1"] for key in SCORE_NAMES},
        "runtime_seconds": report["runtime"]["total_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()

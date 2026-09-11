"""Point, episode, and threshold metrics for anomaly detectors."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve


def choose_threshold(labels: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    """Select the validation-only threshold that maximizes point F1."""
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    if thresholds.size == 0:
        return {"threshold": float("inf"), "precision": 0.0, "recall": 0.0, "f1": 0.0}
    f1 = 2.0 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    best_f1 = float(np.max(f1))
    candidates = np.flatnonzero(np.isclose(f1, best_f1))
    best = int(candidates[-1])  # tied F1: prefer the stricter threshold
    return {
        "threshold": float(thresholds[best]),
        "precision": float(precision[best]),
        "recall": float(recall[best]),
        "f1": float(f1[best]),
    }


def point_metrics(
    labels: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    stations: list[str],
    timestamps: list[str],
    weather_flags: np.ndarray,
) -> dict[str, float | int]:
    predictions = scores >= threshold
    positive = labels == 1
    negative = ~positive
    tp = int(np.sum(predictions & positive))
    fp = int(np.sum(predictions & negative))
    fn = int(np.sum(~predictions & positive))
    tn = int(np.sum(~predictions & negative))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    station_days = len({(station, timestamp[:10]) for station, timestamp in zip(stations, timestamps)})
    weather_total = int(np.sum(weather_flags == 1))
    weather_fp = int(np.sum(predictions & (weather_flags == 1)))
    return {
        "rows": int(labels.size), "positives": int(np.sum(positive)),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "aucpr": float(average_precision_score(labels, scores)) if np.any(positive) else 0.0,
        "false_alarms_per_station_day": fp / station_days if station_days else 0.0,
        "station_days": station_days,
        "weather_rows": weather_total,
        "weather_false_positives": weather_fp,
        "weather_false_positive_rate": weather_fp / weather_total if weather_total else 0.0,
    }


def fault_recall(labels: np.ndarray, predictions: np.ndarray, fault_types: list[str]) -> dict[str, dict[str, float | int]]:
    totals: dict[str, int] = defaultdict(int)
    detected: dict[str, int] = defaultdict(int)
    for label, prediction, fault_type in zip(labels, predictions, fault_types):
        if label == 1:
            totals[fault_type] += 1
            detected[fault_type] += int(prediction)
    return {
        fault_type: {
            "rows": total,
            "detected_rows": detected[fault_type],
            "recall": detected[fault_type] / total if total else 0.0,
        }
        for fault_type, total in sorted(totals.items())
    }


def episode_metrics(
    labels: np.ndarray,
    predictions: np.ndarray,
    episode_ids: list[str],
    timestamps: list[str],
    anomaly_types: list[str],
) -> dict[str, object]:
    episodes: dict[str, dict[str, object]] = {}
    for label, prediction, episode_id, timestamp, anomaly_type in zip(
        labels, predictions, episode_ids, timestamps, anomaly_types
    ):
        if label != 1 or not episode_id:
            continue
        item = episodes.setdefault(episode_id, {"timestamps": [], "detections": [], "type": anomaly_type})
        item["timestamps"].append(timestamp)
        if prediction:
            item["detections"].append(timestamp)

    latencies: list[float] = []
    per_type: dict[str, dict[str, int]] = defaultdict(lambda: {"episodes": 0, "detected": 0})
    detected_count = 0
    for item in episodes.values():
        anomaly_type = str(item["type"])
        per_type[anomaly_type]["episodes"] += 1
        detections = item["detections"]
        if detections:
            detected_count += 1
            per_type[anomaly_type]["detected"] += 1
            start = datetime.fromisoformat(min(item["timestamps"]).replace("Z", "+00:00"))
            first = datetime.fromisoformat(min(detections).replace("Z", "+00:00"))
            latencies.append(max(0.0, (first - start).total_seconds() / 60.0))

    type_report = {
        key: {**value, "recall": value["detected"] / value["episodes"]}
        for key, value in sorted(per_type.items())
    }
    return {
        "episodes": len(episodes),
        "detected_episodes": detected_count,
        "recall": detected_count / len(episodes) if episodes else 0.0,
        "median_detection_latency_minutes": float(np.median(latencies)) if latencies else None,
        "mean_detection_latency_minutes": float(np.mean(latencies)) if latencies else None,
        "per_fault_type": type_report,
    }


def alert_run_metrics(
    labels: np.ndarray,
    predictions: np.ndarray,
    stations: list[str],
    timestamps: list[str],
    maximum_gap_minutes: float = 180.0,
) -> dict[str, float | int]:
    """Cluster predicted rows into station alert runs and measure run precision."""
    predicted_rows: dict[str, list[tuple[datetime, bool]]] = defaultdict(list)
    for label, prediction, station, timestamp in zip(labels, predictions, stations, timestamps):
        if prediction:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            predicted_rows[station].append((parsed, bool(label)))

    runs: list[bool] = []
    maximum_gap = timedelta(minutes=maximum_gap_minutes)
    for rows in predicted_rows.values():
        rows.sort(key=lambda item: item[0])
        previous: datetime | None = None
        run_has_fault = False
        for timestamp, is_fault in rows:
            if previous is not None and timestamp - previous > maximum_gap:
                runs.append(run_has_fault)
                run_has_fault = False
            run_has_fault = run_has_fault or is_fault
            previous = timestamp
        if previous is not None:
            runs.append(run_has_fault)

    true_runs = sum(runs)
    return {
        "predicted_alert_runs": len(runs),
        "fault_overlapping_runs": true_runs,
        "false_alert_runs": len(runs) - true_runs,
        "precision": true_runs / len(runs) if runs else 0.0,
        "maximum_gap_minutes": maximum_gap_minutes,
    }

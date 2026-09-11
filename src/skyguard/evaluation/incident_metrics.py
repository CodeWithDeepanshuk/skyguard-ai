"""Incident matching, latency, root-cause, and calibration metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score


@dataclass(frozen=True)
class IncidentMatch:
    truth_index: int
    prediction_index: int
    overlap_seconds: float
    latency_minutes: float


def _times(frame: pd.DataFrame, start: str, end: str) -> tuple[pd.Series, pd.Series]:
    starts = pd.to_datetime(frame[start], utc=True)
    ends = pd.to_datetime(frame[end], utc=True)
    return starts, ends


def match_incidents(
    truth: pd.DataFrame,
    predictions: pd.DataFrame,
    tolerance_minutes: float = 0.0,
) -> list[IncidentMatch]:
    """Greedy one-to-one interval matching, restricted to the same station."""

    if truth.empty or predictions.empty:
        return []
    truth_start, truth_end = _times(truth, "start_utc", "end_utc")
    pred_start, pred_end = _times(predictions, "start_utc", "end_utc")
    alert_time = pd.to_datetime(
        predictions["first_alert_utc"] if "first_alert_utc" in predictions else predictions["start_utc"],
        utc=True,
    )
    tolerance = pd.Timedelta(minutes=float(tolerance_minutes))
    candidates: list[tuple[float, int, int, float]] = []
    for truth_index in range(len(truth)):
        station = str(truth.iloc[truth_index]["station_id"])
        for prediction_index in range(len(predictions)):
            if str(predictions.iloc[prediction_index]["station_id"]) != station:
                continue
            start = max(truth_start.iloc[truth_index] - tolerance, pred_start.iloc[prediction_index])
            end = min(truth_end.iloc[truth_index] + tolerance, pred_end.iloc[prediction_index])
            overlap = (end - start).total_seconds()
            if overlap <= 0:
                continue
            latency = max(0.0, (alert_time.iloc[prediction_index] - truth_start.iloc[truth_index]).total_seconds() / 60.0)
            candidates.append((overlap, truth_index, prediction_index, latency))
    matches: list[IncidentMatch] = []
    used_truth: set[int] = set()
    used_predictions: set[int] = set()
    for overlap, truth_index, prediction_index, latency in sorted(candidates, reverse=True):
        if truth_index in used_truth or prediction_index in used_predictions:
            continue
        used_truth.add(truth_index)
        used_predictions.add(prediction_index)
        matches.append(IncidentMatch(truth_index, prediction_index, overlap, latency))
    return matches


def incident_metrics(
    truth: pd.DataFrame,
    predictions: pd.DataFrame,
    station_days: int,
    tolerance_minutes: float = 0.0,
) -> dict[str, object]:
    matches = match_incidents(truth, predictions, tolerance_minutes)
    tp = len(matches)
    fp = len(predictions) - tp
    fn = len(truth) - tp
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    latencies = np.asarray([match.latency_minutes for match in matches], dtype=float)
    result: dict[str, object] = {
        "true_incidents": int(len(truth)), "predicted_incidents": int(len(predictions)),
        "tp": tp, "fp": fp, "fn": fn,
        "precision": float(precision), "recall": float(recall), "f1": float(f1),
        "false_alerts_per_station_day": float(fp / max(int(station_days), 1)),
        "median_latency_minutes": float(np.median(latencies)) if latencies.size else None,
        "mean_latency_minutes": float(np.mean(latencies)) if latencies.size else None,
        "p90_latency_minutes": float(np.quantile(latencies, .90)) if latencies.size else None,
    }
    if matches and "root_cause" in truth and "root_cause" in predictions:
        actual = [str(truth.iloc[item.truth_index].root_cause) for item in matches]
        predicted = [str(predictions.iloc[item.prediction_index].root_cause) for item in matches]
        result["matched_root_accuracy"] = float(accuracy_score(actual, predicted))
        result["matched_root_macro_f1"] = float(f1_score(actual, predicted, average="macro", zero_division=0))
    return result


def calibration_metrics(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> dict[str, object]:
    labels = np.asarray(labels, dtype=float)
    probabilities = np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)
    if labels.shape != probabilities.shape:
        raise ValueError("labels and probabilities must have the same shape")
    edges = np.linspace(0.0, 1.0, int(bins) + 1)
    assignments = np.minimum(np.digitize(probabilities, edges[1:-1], right=False), bins - 1)
    rows: list[dict[str, object]] = []
    ece = 0.0
    for index in range(bins):
        mask = assignments == index
        if not np.any(mask):
            continue
        confidence = float(probabilities[mask].mean())
        accuracy = float(labels[mask].mean())
        fraction = float(mask.mean())
        ece += fraction * abs(confidence - accuracy)
        rows.append({
            "bin": index, "count": int(mask.sum()), "mean_confidence": confidence,
            "observed_rate": accuracy, "absolute_gap": abs(confidence - accuracy),
        })
    return {
        "brier_score": float(np.mean((probabilities - labels) ** 2)),
        "expected_calibration_error": float(ece),
        "reliability_bins": rows,
    }

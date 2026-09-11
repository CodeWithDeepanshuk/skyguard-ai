"""Operational score fusion and incident hierarchy for Phase 10."""

from __future__ import annotations

import numpy as np
import pandas as pd


def station_days(frame: pd.DataFrame) -> int:
    dates = pd.to_datetime(frame["emitted_timestamp_utc"], utc=True).dt.date.astype(str)
    return int(pd.DataFrame({"station": frame["station_id"].astype(str), "date": dates}).drop_duplicates().shape[0])


def constrained_threshold(
    labels: np.ndarray,
    scores: np.ndarray,
    frame: pd.DataFrame,
    weather_flags: np.ndarray,
    false_alarm_limit: float = 0.05,
    weather_false_fault_limit: float = 0.02,
) -> dict[str, float]:
    """Maximize validation F1 under explicit operational false-alarm limits."""

    days = station_days(frame)
    order = np.argsort(-scores, kind="stable")
    ordered_scores = scores[order]
    ordered_labels = labels[order].astype(np.int8)
    ordered_weather = weather_flags[order].astype(np.int8)
    tp_all = np.cumsum(ordered_labels)
    fp_all = np.cumsum(1 - ordered_labels)
    weather_all = np.cumsum(ordered_weather)
    group_ends = np.flatnonzero(np.r_[ordered_scores[:-1] != ordered_scores[1:], True])
    tp = tp_all[group_ends].astype(np.float64)
    fp = fp_all[group_ends].astype(np.float64)
    fn = float(np.sum(labels)) - tp
    precision = tp / np.maximum(tp + fp, 1.0)
    recall = tp / np.maximum(tp + fn, 1.0)
    f1 = 2.0 * precision * recall / np.maximum(precision + recall, 1e-12)
    false_alarms = fp / max(days, 1)
    weather_total = max(int(np.sum(weather_flags)), 1)
    weather_rate = weather_all[group_ends] / weather_total
    feasible = (false_alarms <= false_alarm_limit) & (weather_rate <= weather_false_fault_limit)
    candidate_indices = np.flatnonzero(feasible) if np.any(feasible) else np.arange(group_ends.size)
    # Lexicographic maximum: F1 first, then recall, then a higher threshold.
    chosen = int(candidate_indices[np.lexsort((ordered_scores[group_ends][candidate_indices], recall[candidate_indices], f1[candidate_indices]))[-1]])
    return {
        "threshold": float(ordered_scores[group_ends[chosen]]),
        "precision": float(precision[chosen]), "recall": float(recall[chosen]), "f1": float(f1[chosen]),
        "false_alarms_per_station_day": float(false_alarms[chosen]),
        "weather_false_fault_rate": float(weather_rate[chosen]),
        "constraints_met": float(np.any(feasible)),
    }


def causal_persistence_scores(frame: pd.DataFrame, scores: np.ndarray, decay: float, maximum_gap_hours: float = 3.0) -> np.ndarray:
    """Carry strong incident evidence forward without using future observations."""

    result = np.zeros_like(scores, dtype=np.float64)
    timestamps = pd.to_datetime(frame["emitted_timestamp_utc"], utc=True).astype("int64").to_numpy() / 3.6e12
    station_ids = frame["station_id"].astype(str).to_numpy()
    order = np.lexsort((timestamps, station_ids))
    previous_station = ""
    previous_time = 0.0
    state = 0.0
    for index in order:
        station = station_ids[index]
        timestamp = timestamps[index]
        if station != previous_station or timestamp - previous_time > maximum_gap_hours or timestamp <= previous_time:
            state = float(scores[index])
        else:
            state = max(float(scores[index]), state * decay)
        result[index] = state
        previous_station = station
        previous_time = timestamp
    return result


def choose_persistence_policy(
    frame: pd.DataFrame, labels: np.ndarray, base_scores: np.ndarray, weather_flags: np.ndarray,
) -> tuple[dict[str, float], np.ndarray]:
    options: list[tuple[dict[str, float], np.ndarray]] = []
    for decay in (0.0, 0.55, 0.70, 0.82, 0.90):
        scores = causal_persistence_scores(frame, base_scores, decay)
        policy = constrained_threshold(labels, scores, frame, weather_flags)
        policy["persistence_decay"] = decay
        options.append((policy, scores))
    return max(options, key=lambda item: (item[0]["f1"], item[0]["recall"]))


def aggregate_incident_roots(
    frame: pd.DataFrame,
    detected: np.ndarray,
    fault_scores: np.ndarray,
    probabilities: np.ndarray,
    classes: np.ndarray,
    maximum_gap_hours: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assign one probability-aggregated diagnosis to each detected incident."""

    predictions = np.full(frame.shape[0], "not_a_fault", dtype=object)
    confidence = np.zeros(frame.shape[0], dtype=np.float64)
    incident_ids = np.full(frame.shape[0], "", dtype=object)
    timestamps = pd.to_datetime(frame["emitted_timestamp_utc"], utc=True).astype("int64").to_numpy() / 3.6e12
    stations = frame["station_id"].astype(str).to_numpy()
    time_since = pd.to_numeric(frame["time_since_previous_minutes"], errors="coerce").to_numpy()
    order = np.lexsort((timestamps, stations))
    groups: list[list[int]] = []
    current: list[int] = []
    previous_station = ""
    previous_time = -np.inf
    for index in order:
        if not detected[index]:
            continue
        station = stations[index]
        timestamp = timestamps[index]
        if current and (station != previous_station or timestamp - previous_time > maximum_gap_hours or timestamp <= previous_time):
            groups.append(current)
            current = []
        current.append(int(index))
        previous_station = station
        previous_time = timestamp
    if current:
        groups.append(current)

    for number, indices in enumerate(groups, start=1):
        index_array = np.asarray(indices, dtype=np.int64)
        weights = np.maximum(fault_scores[index_array], 1e-4)
        combined = np.average(probabilities[index_array], axis=0, weights=weights)
        class_index = int(np.argmax(combined))
        label = str(classes[class_index])
        conf = float(combined[class_index])

        # Packet/order faults are deterministic and should not compete with physical models.
        intervals = time_since[index_array]
        if np.any(np.isfinite(intervals) & (intervals == 0.0)) and "duplicate_packet" in classes:
            label, conf = "duplicate_packet", 1.0
        elif np.any(np.isfinite(intervals) & (intervals < 0.0)) and "timestamp_error" in classes:
            label, conf = "timestamp_error", 1.0

        incident = f"P10-{number:06d}"
        predictions[index_array] = label
        confidence[index_array] = conf
        incident_ids[index_array] = incident
    return predictions.astype(str), confidence, incident_ids.astype(str)

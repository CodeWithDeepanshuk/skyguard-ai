"""Causal corrected-value candidates and sensor evidence."""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np


SENSORS = ("temperature", "pressure", "humidity")
VALUE_COLUMNS = {"temperature": "temperature_value", "pressure": "pressure_value", "humidity": "humidity_value"}
ORIGINAL_COLUMNS = {
    "temperature": "original_temperature_c",
    "pressure": "original_pressure_hpa",
    "humidity": "original_relative_humidity_pct",
}
PHYSICAL_RANGES = {"temperature": (-80.0, 60.0), "pressure": (850.0, 1100.0), "humidity": (0.0, 100.0)}
MIN_SCALES = {"temperature": 0.5, "pressure": 0.5, "humidity": 2.0}
NEIGHBOR_SCALES = {"temperature": 3.0, "pressure": 5.0, "humidity": 15.0}
RATE_SCALES = {"temperature": 8.0, "pressure": 8.0, "humidity": 35.0}
CHANGE_TOLERANCE = {"temperature": 0.05, "pressure": 0.05, "humidity": 0.1}
CORRECTABLE_FAULTS = {
    "spike", "sudden_drop", "frozen_sensor", "bias", "drift", "noise", "unit_error",
    "scaling_error", "communication_corruption", "multi_sensor_failure",
}


def number(row: Mapping[str, object], key: str) -> float:
    try:
        value = float(row.get(key, math.nan))
    except (TypeError, ValueError):
        return math.nan
    return value if math.isfinite(value) else math.nan


def valid_value(sensor: str, value: float) -> bool:
    low, high = PHYSICAL_RANGES[sensor]
    return math.isfinite(value) and low <= value <= high


def correction_candidates(row: Mapping[str, object], sensor: str) -> dict[str, float]:
    candidates = {
        "temporal_median": number(row, f"{sensor}_rolling_median_24h"),
        "ewma_prior": number(row, f"{sensor}_ewma_prior"),
        "lag1": number(row, f"{sensor}_lag1"),
        "neighbor_median": number(row, f"neighbor_{sensor}_median"),
        "neighbor_weighted_mean": number(row, f"neighbor_{sensor}_weighted_mean"),
    }
    causal_values = [
        value for name, value in candidates.items()
        if name in {"temporal_median", "ewma_prior", "neighbor_median", "neighbor_weighted_mean"}
        and valid_value(sensor, value)
    ]
    candidates["causal_ensemble"] = float(np.median(causal_values)) if causal_values else math.nan
    return {name: value for name, value in candidates.items() if valid_value(sensor, value)}


def uncertainty_scale(row: Mapping[str, object], sensor: str) -> float:
    """Causal local scale that expands when temporal/neighbour estimates disagree."""
    candidates = list(correction_candidates(row, sensor).values())
    candidate_scale = float(np.std(candidates)) if len(candidates) >= 2 else 0.0
    rolling_mad = number(row, f"{sensor}_rolling_mad_24h")
    neighbor_mad = number(row, f"neighbor_{sensor}_mad")
    scales = [MIN_SCALES[sensor], candidate_scale]
    if math.isfinite(rolling_mad):
        scales.append(1.4826 * rolling_mad)
    if math.isfinite(neighbor_mad):
        scales.append(1.4826 * neighbor_mad)
    return max(scales)


def sensor_evidence(row: Mapping[str, object], sensor: str) -> dict[str, float]:
    robust_z = abs(number(row, f"{sensor}_robust_z_24h"))
    residual = abs(number(row, f"{sensor}_ewma_residual"))
    mad = number(row, f"{sensor}_rolling_mad_24h")
    robust_scale = max(1.4826 * mad, MIN_SCALES[sensor]) if math.isfinite(mad) else MIN_SCALES[sensor]
    ewma = residual / robust_scale if math.isfinite(residual) else 0.0
    neighbor_residual = abs(number(row, f"neighbor_{sensor}_residual"))
    neighbor = neighbor_residual / NEIGHBOR_SCALES[sensor] if math.isfinite(neighbor_residual) else 0.0
    rate = abs(number(row, f"{sensor}_rate_per_hour"))
    rate_score = rate / RATE_SCALES[sensor] if math.isfinite(rate) else 0.0
    frozen = number(row, f"{sensor}_frozen_run_length")
    frozen_score = frozen / 4.0 if math.isfinite(frozen) else 0.0
    missing = number(row, f"{sensor}_missing")
    return {
        "robust_z": robust_z if math.isfinite(robust_z) else 0.0,
        "ewma": ewma, "neighbor": neighbor, "rate": rate_score,
        "frozen": frozen_score, "missing": 3.0 if missing == 1 else 0.0,
    }


def sensor_evidence_score(row: Mapping[str, object], sensor: str) -> float:
    return max(sensor_evidence(row, sensor).values())


def infer_affected_sensors(row: Mapping[str, object], predicted_root: str) -> list[str]:
    if predicted_root in {"communication_corruption", "multi_sensor_failure"}:
        return list(SENSORS)
    if predicted_root == "unit_error":
        return ["temperature"]
    if predicted_root in {"duplicate_packet", "timestamp_error", "dropout", "not_a_fault"}:
        return []
    scores = {sensor: sensor_evidence_score(row, sensor) for sensor in SENSORS}
    strongest = max(scores, key=scores.get)
    selected = [sensor for sensor, score in scores.items() if score >= max(1.5, scores[strongest] * 0.70)]
    return selected or [strongest]


def true_affected_sensors(value: object) -> list[str]:
    text = str(value or "")
    return [sensor for sensor in SENSORS if sensor in {item.strip() for item in text.split(",")}]


def changed_from_original(row: Mapping[str, object], sensor: str) -> bool:
    reported = number(row, VALUE_COLUMNS[sensor])
    original = number(row, ORIGINAL_COLUMNS[sensor])
    return math.isfinite(reported) and math.isfinite(original) and abs(reported - original) > CHANGE_TOLERANCE[sensor]

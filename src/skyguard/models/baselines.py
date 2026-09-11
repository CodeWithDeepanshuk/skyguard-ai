"""Transparent anomaly scores built from causal weather-station features."""

from __future__ import annotations

import math
from collections.abc import Mapping


SENSORS = ("temperature", "pressure", "humidity")
NEIGHBOR_SCALES = {"temperature": 3.0, "pressure": 5.0, "humidity": 15.0}
RATE_SCALES = {"temperature": 8.0, "pressure": 8.0, "humidity": 35.0}
MIN_ROBUST_SCALES = {"temperature": 0.5, "pressure": 0.5, "humidity": 2.0}


def number(row: Mapping[str, object], key: str) -> float:
    value = row.get(key, "")
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def finite_max(values: list[float], default: float = 0.0) -> float:
    valid = [value for value in values if math.isfinite(value)]
    return max(valid) if valid else default


def hampel_score(row: Mapping[str, object]) -> float:
    """Largest absolute 24-hour robust z-score across primary sensors."""
    return finite_max([abs(number(row, f"{sensor}_robust_z_24h")) for sensor in SENSORS])


def ewma_score(row: Mapping[str, object]) -> float:
    """Largest scale-normalized residual from the prior-state EWMA."""
    scores: list[float] = []
    for sensor in SENSORS:
        residual = number(row, f"{sensor}_ewma_residual")
        mad = number(row, f"{sensor}_rolling_mad_24h")
        if math.isfinite(residual):
            scale = max(1.4826 * mad, MIN_ROBUST_SCALES[sensor]) if math.isfinite(mad) else MIN_ROBUST_SCALES[sensor]
            scores.append(abs(residual) / scale)
    return finite_max(scores)


def neighbor_score(row: Mapping[str, object]) -> float:
    """Largest disagreement with causally aligned nearby stations."""
    scores: list[float] = []
    for sensor in SENSORS:
        count = number(row, f"neighbor_{sensor}_count")
        residual = number(row, f"neighbor_{sensor}_residual")
        if math.isfinite(count) and count >= 1 and math.isfinite(residual):
            scores.append(abs(residual) / NEIGHBOR_SCALES[sensor])
    return finite_max(scores)


def qc_rule_score(row: Mapping[str, object]) -> float:
    """Continuous score for physical, rate, frozen, missing, and timing rules."""
    scores: list[float] = []
    for sensor in SENSORS:
        rate = number(row, f"{sensor}_rate_per_hour")
        frozen = number(row, f"{sensor}_frozen_run_length")
        if math.isfinite(rate):
            scores.append(abs(rate) / RATE_SCALES[sensor])
        if math.isfinite(frozen):
            scores.append(frozen / 4.0)

    missing = number(row, "primary_missing_count")
    gap = number(row, "gap_ratio")
    out_of_order = number(row, "out_of_order_indicator")
    if math.isfinite(missing):
        scores.append(2.0 * missing)
    if math.isfinite(gap):
        scores.append(max(0.0, gap - 1.0))
    if math.isfinite(out_of_order):
        scores.append(3.0 * out_of_order)

    bounds = {
        "temperature_value": (-80.0, 60.0, 10.0),
        "pressure_value": (850.0, 1100.0, 25.0),
        "humidity_value": (0.0, 100.0, 10.0),
    }
    for key, (low, high, scale) in bounds.items():
        value = number(row, key)
        if math.isfinite(value) and (value < low or value > high):
            scores.append(4.0 + min(abs(value - min(max(value, low), high)) / scale, 10.0))
    return finite_max(scores)


def combined_score(row: Mapping[str, object]) -> float:
    """Union score with each component expressed near its alert scale."""
    return max(
        hampel_score(row) / 3.0,
        ewma_score(row) / 3.0,
        neighbor_score(row),
        qc_rule_score(row),
    )


def score_row(row: Mapping[str, object]) -> dict[str, float]:
    return {
        "qc_rules": qc_rule_score(row),
        "hampel": hampel_score(row),
        "ewma": ewma_score(row),
        "neighbor": neighbor_score(row),
        "combined": combined_score(row),
    }

"""Validation-selected correction methods and uncertainty intervals."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping

import numpy as np

from .estimators import (
    CORRECTABLE_FAULTS, ORIGINAL_COLUMNS, PHYSICAL_RANGES, SENSORS, correction_candidates, number,
    true_affected_sensors, uncertainty_scale,
)


def fit_correction_policy(rows: Iterable[Mapping[str, object]], minimum_group_rows: int = 10) -> dict[str, object]:
    errors: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    normalized_errors: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    availability: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        fault_type = str(row.get("anomaly_type", ""))
        if fault_type not in CORRECTABLE_FAULTS or str(row.get("available_to_detector", "1")) != "1":
            continue
        for sensor in true_affected_sensors(row.get("anomaly_sensor", "")):
            original = number(row, ORIGINAL_COLUMNS[sensor])
            if not math.isfinite(original):
                continue
            availability[(sensor, fault_type)] += 1
            for method, estimate in correction_candidates(row, sensor).items():
                absolute_error = abs(estimate - original)
                scale = uncertainty_scale(row, sensor)
                errors[(sensor, fault_type, method)].append(absolute_error)
                errors[(sensor, "__fallback__", method)].append(absolute_error)
                normalized_errors[(sensor, fault_type, method)].append(absolute_error / scale)
                normalized_errors[(sensor, "__fallback__", method)].append(absolute_error / scale)

    policies: dict[str, dict[str, object]] = {}
    for sensor in SENSORS:
        policies[sensor] = {}
        fault_types = sorted({key[1] for key in errors if key[0] == sensor and key[1] != "__fallback__"})
        for fault_type in fault_types + ["__fallback__"]:
            candidates: list[tuple[float, str, list[float]]] = []
            expected = availability.get((sensor, fault_type), 0)
            if fault_type == "__fallback__":
                fallback_sizes = [
                    len(values) for key, values in errors.items()
                    if key[0] == sensor and key[1] == fault_type
                ]
                if not fallback_sizes:
                    continue
                expected = max(fallback_sizes)
            for (key_sensor, key_fault, method), values in errors.items():
                if key_sensor != sensor or key_fault != fault_type or len(values) < minimum_group_rows:
                    continue
                coverage = len(values) / expected if expected else 0.0
                if coverage >= 0.60:
                    candidates.append((float(np.mean(values)), method, values))
            if not candidates:
                continue
            mae, method, selected_errors = min(candidates, key=lambda item: (item[0], item[1]))
            policies[sensor][fault_type] = {
                "method": method,
                "validation_rows": len(selected_errors),
                "validation_mae": mae,
                "absolute_error_q90": float(np.quantile(selected_errors, 0.90)),
                "absolute_error_q95": float(np.quantile(selected_errors, 0.95)),
                "normalized_error_q90": float(np.quantile(normalized_errors[(sensor, fault_type, method)], 0.90)),
                "normalized_error_q95": float(np.quantile(normalized_errors[(sensor, fault_type, method)], 0.95)),
            }
    return {
        "status": "selected_on_2023_validation",
        "causality": "lag, prior EWMA, prior rolling median, and backward-aligned neighbours only",
        "minimum_group_rows": minimum_group_rows,
        "sensors": policies,
    }


def correct_value(
    row: Mapping[str, object], sensor: str, predicted_fault: str, policy: Mapping[str, object],
) -> dict[str, object] | None:
    sensor_policy = policy.get("sensors", {}).get(sensor, {})
    selected = sensor_policy.get(predicted_fault) or sensor_policy.get("__fallback__")
    if not selected:
        return None
    candidates = correction_candidates(row, sensor)
    method = str(selected["method"])
    estimate = candidates.get(method)
    if estimate is None:
        for fallback in ("causal_ensemble", "neighbor_median", "temporal_median", "ewma_prior", "lag1"):
            if fallback in candidates:
                method = fallback
                estimate = candidates[fallback]
                break
    if estimate is None:
        return None
    local_scale = uncertainty_scale(row, sensor)
    uncertainty = max(
        float(selected["absolute_error_q90"]),
        float(selected.get("normalized_error_q90", 0.0)) * local_scale,
    )
    physical_low, physical_high = PHYSICAL_RANGES[sensor]
    return {
        "sensor": sensor,
        "method": method,
        "estimate": float(estimate),
        "interval_lower": float(max(physical_low, estimate - uncertainty)),
        "interval_upper": float(min(physical_high, estimate + uncertainty)),
        "interval_level": 0.90,
        "validation_absolute_error_q90": float(selected["absolute_error_q90"]),
        "interval_half_width": uncertainty,
        "local_uncertainty_scale": local_scale,
        "uncertainty_strategy": "max(validation absolute q90, normalized conformal q90 x causal local scale)",
    }

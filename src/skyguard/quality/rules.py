"""Stateless weather-observation quality-control rules."""

from __future__ import annotations

from math import isfinite
from .models import Alert, Observation, QualityThresholds


SENSORS = (
    ("temperature", "temperature_c", "temperature_quality"),
    ("pressure", "pressure_hpa", "pressure_quality"),
    ("humidity", "relative_humidity_pct", ""),
)


def check_missing(observation: Observation) -> list[Alert]:
    alerts: list[Alert] = []
    for sensor, value_field, _ in SENSORS:
        if getattr(observation, value_field) is None:
            alerts.append(Alert.create(
                observation, "MISSING_VALUE", sensor, "medium", 0.75, None,
                "A numeric sensor value is required.",
                f"{sensor.capitalize()} is missing from this observation.",
            ))
    return alerts


def check_physical_bounds(observation: Observation, thresholds: QualityThresholds) -> list[Alert]:
    alerts: list[Alert] = []
    sea_level = observation.pressure_source.strip().lower() in {
        "slp", "sea_level_pressure", "ma1_altimeter", "qnh",
        "dwd_station_pressure_reduced_to_msl", "metar_qnh",
    }
    pressure_lower = thresholds.pressure_min_hpa if sea_level else thresholds.station_pressure_min_hpa
    pressure_upper = thresholds.pressure_max_hpa if sea_level else thresholds.station_pressure_max_hpa
    bounds = (
        ("temperature", observation.temperature_c, thresholds.temperature_min_c, thresholds.temperature_max_c, "°C"),
        ("pressure", observation.pressure_hpa, pressure_lower, pressure_upper, "hPa"),
        ("humidity", observation.relative_humidity_pct, thresholds.humidity_min_pct, thresholds.humidity_max_pct, "%"),
    )
    for sensor, value, lower, upper, unit in bounds:
        if value is not None and not isfinite(value):
            alerts.append(Alert.create(
                observation, "NONFINITE_VALUE", sensor, "high", 1.0,
                value, "Finite numeric measurement required.",
                f"{sensor.capitalize()} contains NaN or infinity; exclude from temporal evidence.",
            ))
            continue
        if value is not None and not lower <= value <= upper:
            distance = lower - value if value < lower else value - upper
            scale = max(upper - lower, 1.0)
            alerts.append(Alert.create(
                observation, "PHYSICAL_BOUNDS", sensor, "critical", 0.9 + min(0.1, distance / scale),
                value, f"{lower:g} to {upper:g} {unit}",
                f"Reported {sensor} {value:g} {unit} is outside the configured physical range.",
            ))
    return alerts


def check_source_quality(observation: Observation, thresholds: QualityThresholds) -> list[Alert]:
    alerts: list[Alert] = []
    for sensor, _, quality_field in SENSORS:
        if not quality_field:
            continue
        code = getattr(observation, quality_field)
        if code in thresholds.erroneous_quality_codes:
            severity, score = "high", 0.9
        elif code in thresholds.suspicious_quality_codes:
            severity, score = "medium", 0.7
        else:
            continue
        alerts.append(Alert.create(
            observation, "SOURCE_QUALITY_FLAG", sensor, severity, score, code,
            "NOAA quality code is not suspect or erroneous.",
            f"The source quality code for {sensor} is {code}; retain the value for audit but exclude it from clean training candidates.",
        ))
    return alerts


def check_cross_variable_consistency(observation: Observation, thresholds: QualityThresholds) -> list[Alert]:
    if observation.dew_point_c is None or observation.temperature_c is None:
        return []
    difference = observation.dew_point_c - observation.temperature_c
    if difference <= thresholds.dew_point_margin_c:
        return []
    return [Alert.create(
        observation, "DEWPOINT_ABOVE_TEMPERATURE", "multivariate", "high", min(1.0, 0.75 + difference / 20.0),
        f"T={observation.temperature_c:g}, Td={observation.dew_point_c:g}",
        f"Dew point should not exceed temperature by more than {thresholds.dew_point_margin_c:g} °C.",
        "Dew point is materially above air temperature, indicating inconsistent temperature/humidity inputs.",
    )]


def run_stateless_rules(observation: Observation, thresholds: QualityThresholds) -> list[Alert]:
    return [
        *check_missing(observation),
        *check_physical_bounds(observation, thresholds),
        *check_source_quality(observation, thresholds),
        *check_cross_variable_consistency(observation, thresholds),
    ]

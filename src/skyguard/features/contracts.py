"""Feature, label, audit, and configuration contracts."""

from __future__ import annotations

from dataclasses import dataclass


SENSORS = {
    "temperature": "temperature_c",
    "pressure": "pressure_hpa",
    "humidity": "relative_humidity_pct",
}

IDENTITY_COLUMNS = (
    "row_id", "station_id", "timestamp_utc", "emitted_timestamp_utc", "split", "cluster", "evaluation_role",
)

LABEL_COLUMNS = (
    "is_anomaly", "is_weather_event", "anomaly_type", "anomaly_sensor", "anomaly_severity",
)

AUDIT_COLUMNS = (
    "episode_id", "label_category", "label_source", "injection_seed", "stream_action",
    "timestamp_offset_seconds", "original_timestamp_utc", "original_temperature_c",
    "original_pressure_hpa", "original_relative_humidity_pct", "available_to_detector",
)

BASE_FEATURE_COLUMNS = (
    "temperature_value", "pressure_value", "humidity_value",
    "primary_missing_count", "time_since_previous_minutes", "gap_ratio", "out_of_order_indicator",
    "hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos",
    "temperature_dewpoint_spread_c", "temperature_humidity_interaction",
    "pressure_temperature_ratio",
    "neighbor_station_count", "neighbor_min_age_minutes", "neighbor_max_age_minutes", "nearest_neighbor_km",
)

TEMPORAL_SUFFIXES = (
    "missing", "lag1", "delta1", "rate_per_hour", "rolling_count_24h", "rolling_median_24h",
    "rolling_mad_24h", "robust_z_24h", "ewma_prior", "ewma_residual", "frozen_run_length",
)

NEIGHBOR_SUFFIXES = (
    "count", "weighted_mean", "median", "mad", "residual", "max_abs_difference", "agreement_fraction",
)

MODEL_FEATURE_COLUMNS = tuple(BASE_FEATURE_COLUMNS) + tuple(
    f"{sensor}_{suffix}" for sensor in SENSORS for suffix in TEMPORAL_SUFFIXES
) + tuple(
    f"neighbor_{sensor}_{suffix}" for sensor in SENSORS for suffix in NEIGHBOR_SUFFIXES
)

OUTPUT_COLUMNS = IDENTITY_COLUMNS + MODEL_FEATURE_COLUMNS + LABEL_COLUMNS + AUDIT_COLUMNS


@dataclass(frozen=True)
class FeatureConfig:
    rolling_window_hours: float = 24.0
    ewma_alpha: float = 0.2
    neighbor_tolerance_minutes: float = 180.0
    max_neighbors: int = 5
    temperature_equality_tolerance: float = 0.05
    pressure_equality_tolerance: float = 0.05
    humidity_equality_tolerance: float = 0.05
    temperature_neighbor_agreement: float = 3.0
    pressure_neighbor_agreement: float = 5.0
    humidity_neighbor_agreement: float = 15.0

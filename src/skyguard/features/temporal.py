"""Causal station-local and multivariate feature construction."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import median

from .contracts import FeatureConfig, SENSORS, TEMPORAL_SUFFIXES


def optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def formatted_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds") + "Z"


@dataclass
class SensorState:
    last_value: float | None = None
    ewma: float | None = None
    frozen_run_length: int = 0
    history: deque[tuple[datetime, float]] = field(default_factory=deque)


@dataclass
class StationFeatureState:
    last_timestamp: datetime | None = None
    sensors: dict[str, SensorState] = field(default_factory=lambda: {sensor: SensorState() for sensor in SENSORS})


class TemporalFeatureBuilder:
    def __init__(self, expected_interval_minutes: dict[str, float], config: FeatureConfig | None = None) -> None:
        self.expected_interval_minutes = expected_interval_minutes
        self.config = config or FeatureConfig()
        self.states: dict[str, StationFeatureState] = {}

    def transform(self, row: dict[str, str]) -> dict[str, object]:
        station_id = row["station_id"]
        original_time = datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z"))
        offset_seconds = int(row.get("timestamp_offset_seconds", "0") or 0)
        emitted_time = original_time + timedelta(seconds=offset_seconds)
        available = row.get("stream_action", "emit") != "drop"
        state = self.states.setdefault(station_id, StationFeatureState())
        previous_time = state.last_timestamp
        delta_minutes = None if previous_time is None else (emitted_time - previous_time).total_seconds() / 60.0
        out_of_order = delta_minutes is not None and delta_minutes <= 0.0

        features: dict[str, object] = {
            "emitted_timestamp_utc": formatted_timestamp(emitted_time),
            "available_to_detector": "1" if available else "0",
            "time_since_previous_minutes": "" if delta_minutes is None else round(delta_minutes, 4),
            "gap_ratio": "",
            "out_of_order_indicator": 1 if out_of_order else 0,
        }
        expected = self.expected_interval_minutes.get(station_id)
        if delta_minutes is not None and expected and expected > 0:
            features["gap_ratio"] = round(delta_minutes / expected, 6)

        angle_hour = 2.0 * math.pi * (emitted_time.hour + emitted_time.minute / 60.0) / 24.0
        angle_day = 2.0 * math.pi * (emitted_time.timetuple().tm_yday - 1) / 365.25
        features.update({
            "hour_sin": round(math.sin(angle_hour), 8),
            "hour_cos": round(math.cos(angle_hour), 8),
            "day_of_year_sin": round(math.sin(angle_day), 8),
            "day_of_year_cos": round(math.cos(angle_day), 8),
        })

        values = {sensor: optional_float(row[field]) for sensor, field in SENSORS.items()}
        features.update({
            "temperature_value": "" if not available or values["temperature"] is None else values["temperature"],
            "pressure_value": "" if not available or values["pressure"] is None else values["pressure"],
            "humidity_value": "" if not available or values["humidity"] is None else values["humidity"],
            "primary_missing_count": sum(value is None for value in values.values()),
        })

        if not available:
            self._blank_temporal(features)
            self._multivariate(features, row, values, available=False)
            return features

        for sensor, value in values.items():
            self._sensor_features(features, sensor, value, emitted_time, state, delta_minutes, out_of_order)
        self._multivariate(features, row, values, available=True)

        if not out_of_order:
            state.last_timestamp = emitted_time
        return features

    def _blank_temporal(self, features: dict[str, object]) -> None:
        for sensor in SENSORS:
            for suffix in TEMPORAL_SUFFIXES:
                features[f"{sensor}_{suffix}"] = ""

    def _sensor_features(
        self,
        features: dict[str, object],
        sensor: str,
        value: float | None,
        timestamp: datetime,
        station_state: StationFeatureState,
        delta_minutes: float | None,
        out_of_order: bool,
    ) -> None:
        sensor_state = station_state.sensors[sensor]
        prefix = f"{sensor}_"
        features[prefix + "missing"] = 1 if value is None else 0
        features[prefix + "lag1"] = "" if sensor_state.last_value is None else sensor_state.last_value
        features[prefix + "delta1"] = ""
        features[prefix + "rate_per_hour"] = ""
        features[prefix + "rolling_count_24h"] = ""
        features[prefix + "rolling_median_24h"] = ""
        features[prefix + "rolling_mad_24h"] = ""
        features[prefix + "robust_z_24h"] = ""
        features[prefix + "ewma_prior"] = "" if sensor_state.ewma is None else sensor_state.ewma
        features[prefix + "ewma_residual"] = ""
        features[prefix + "frozen_run_length"] = sensor_state.frozen_run_length

        if value is None:
            return
        if sensor_state.last_value is not None:
            features[prefix + "delta1"] = round(value - sensor_state.last_value, 6)
            if delta_minutes is not None and delta_minutes > 0:
                features[prefix + "rate_per_hour"] = round((value - sensor_state.last_value) / (delta_minutes / 60.0), 6)
        if sensor_state.ewma is not None:
            features[prefix + "ewma_residual"] = round(value - sensor_state.ewma, 6)

        if not out_of_order:
            cutoff = timestamp - timedelta(hours=self.config.rolling_window_hours)
            while sensor_state.history and sensor_state.history[0][0] < cutoff:
                sensor_state.history.popleft()
            history_values = [item[1] for item in sensor_state.history]
            features[prefix + "rolling_count_24h"] = len(history_values)
            if history_values:
                center = median(history_values)
                deviations = [abs(item - center) for item in history_values]
                mad = median(deviations)
                features[prefix + "rolling_median_24h"] = round(center, 6)
                features[prefix + "rolling_mad_24h"] = round(mad, 6)
                if len(history_values) >= 3 and mad > 1e-9:
                    features[prefix + "robust_z_24h"] = round((value - center) / (1.4826 * mad), 6)

            tolerance = {
                "temperature": self.config.temperature_equality_tolerance,
                "pressure": self.config.pressure_equality_tolerance,
                "humidity": self.config.humidity_equality_tolerance,
            }[sensor]
            if sensor_state.last_value is not None and abs(value - sensor_state.last_value) <= tolerance:
                sensor_state.frozen_run_length += 1
            else:
                sensor_state.frozen_run_length = 1
            features[prefix + "frozen_run_length"] = sensor_state.frozen_run_length
            sensor_state.history.append((timestamp, value))
            sensor_state.ewma = value if sensor_state.ewma is None else self.config.ewma_alpha * value + (1.0 - self.config.ewma_alpha) * sensor_state.ewma
            sensor_state.last_value = value

    @staticmethod
    def _multivariate(features: dict[str, object], row: dict[str, str], values: dict[str, float | None], available: bool) -> None:
        temperature = values["temperature"] if available else None
        pressure = values["pressure"] if available else None
        humidity = values["humidity"] if available else None
        dew_point = optional_float(row.get("dew_point_c")) if available else None
        features["temperature_dewpoint_spread_c"] = "" if temperature is None or dew_point is None else round(temperature - dew_point, 6)
        features["temperature_humidity_interaction"] = "" if temperature is None or humidity is None else round(temperature * (100.0 - humidity) / 100.0, 6)
        features["pressure_temperature_ratio"] = "" if pressure is None or temperature is None else round(pressure / (temperature + 273.15), 8)

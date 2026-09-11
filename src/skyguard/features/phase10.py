"""SIH-compliant Phase 10 features using only temperature, pressure, and RH.

The input feature tables contain historical/audit columns, but ``PHASE10_FEATURES``
explicitly excludes labels, audit values, calendar shortcuts, and dew point.  The
new trend state is causal: a row uses its current observation and observations
that arrived earlier for the same station.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

import numpy as np
import pandas as pd

from .contracts import MODEL_FEATURE_COLUMNS


SENSORS = ("temperature", "pressure", "humidity")
VALUE_COLUMNS = {
    "temperature": "temperature_value",
    "pressure": "pressure_value",
    "humidity": "humidity_value",
}
SLOPE_WINDOWS_HOURS = (3, 6, 12, 24)
FORBIDDEN_PHASE10_INPUTS = {
    "temperature_dewpoint_spread_c",
    "hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos",
}
PHASE10_BASE_FEATURES = tuple(
    column for column in MODEL_FEATURE_COLUMNS if column not in FORBIDDEN_PHASE10_INPUTS
)
TREND_FEATURES = tuple(
    feature
    for sensor in SENSORS
    for feature in (
        *(f"{sensor}_slope_{hours}h" for hours in SLOPE_WINDOWS_HOURS),
        *(f"{sensor}_neighbor_residual_slope_{hours}h" for hours in SLOPE_WINDOWS_HOURS),
        f"{sensor}_cusum_positive",
        f"{sensor}_cusum_negative",
        f"{sensor}_monotonic_run",
        f"{sensor}_climatology_residual",
    )
)
WEATHER_GATE_FEATURES = (
    "regional_agreement_mean",
    "regional_agreement_min",
    "regional_agreeing_sensor_count",
    "regional_standardized_disagreement_max",
    "regional_trend_disagreement_mean",
)
PHASE10_FEATURES = PHASE10_BASE_FEATURES + TREND_FEATURES + WEATHER_GATE_FEATURES


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _timestamp(value: object) -> datetime:
    return datetime.fromisoformat(str(value).removesuffix("Z"))


@dataclass
class RollingSlope:
    """Constant-time rolling least-squares slope."""

    window_hours: float
    values: deque[tuple[float, float]] = field(default_factory=deque)
    sum_t: float = 0.0
    sum_x: float = 0.0
    sum_tt: float = 0.0
    sum_tx: float = 0.0

    def push(self, time_hours: float, value: float | None) -> float:
        if value is None:
            return np.nan
        self.values.append((time_hours, value))
        self.sum_t += time_hours
        self.sum_x += value
        self.sum_tt += time_hours * time_hours
        self.sum_tx += time_hours * value
        cutoff = time_hours - self.window_hours
        while self.values and self.values[0][0] < cutoff:
            old_t, old_x = self.values.popleft()
            self.sum_t -= old_t
            self.sum_x -= old_x
            self.sum_tt -= old_t * old_t
            self.sum_tx -= old_t * old_x
        count = len(self.values)
        if count < 3 or self.values[-1][0] - self.values[0][0] < min(1.0, self.window_hours / 3.0):
            return np.nan
        denominator = count * self.sum_tt - self.sum_t * self.sum_t
        if abs(denominator) < 1e-10:
            return np.nan
        return (count * self.sum_tx - self.sum_t * self.sum_x) / denominator


@dataclass
class SensorTrendState:
    local_slopes: dict[int, RollingSlope] = field(
        default_factory=lambda: {hours: RollingSlope(float(hours)) for hours in SLOPE_WINDOWS_HOURS}
    )
    residual_slopes: dict[int, RollingSlope] = field(
        default_factory=lambda: {hours: RollingSlope(float(hours)) for hours in SLOPE_WINDOWS_HOURS}
    )
    cusum_positive: float = 0.0
    cusum_negative: float = 0.0
    previous_value: float | None = None
    previous_direction: int = 0
    monotonic_run: int = 0

    def update(self, time_hours: float, value: float | None, residual: float | None, robust_z: float | None) -> dict[str, float]:
        output: dict[str, float] = {}
        for hours, state in self.local_slopes.items():
            output[f"slope_{hours}h"] = state.push(time_hours, value)
        for hours, state in self.residual_slopes.items():
            output[f"neighbor_residual_slope_{hours}h"] = state.push(time_hours, residual)

        if robust_z is not None:
            clipped = float(np.clip(robust_z, -12.0, 12.0))
            self.cusum_positive = max(0.0, min(50.0, 0.95 * self.cusum_positive + clipped - 0.5))
            self.cusum_negative = max(0.0, min(50.0, 0.95 * self.cusum_negative - clipped - 0.5))
        output["cusum_positive"] = self.cusum_positive
        output["cusum_negative"] = self.cusum_negative

        if value is not None and self.previous_value is not None:
            difference = value - self.previous_value
            direction = 1 if difference > 1e-9 else (-1 if difference < -1e-9 else 0)
            if direction and direction == self.previous_direction:
                self.monotonic_run += 1
            elif direction:
                self.monotonic_run = 2
            else:
                self.monotonic_run = 0
            self.previous_direction = direction
        if value is not None:
            self.previous_value = value
        output["monotonic_run"] = float(self.monotonic_run)
        return output


def fit_climatology(train: pd.DataFrame) -> dict[str, dict[tuple[object, ...], float]]:
    """Fit station and cluster hour/month medians from clean 2022 rows."""

    frame = train.loc[(train["is_anomaly"] == 0) & (train["is_weather_event"] == 0)].copy()
    timestamp = pd.to_datetime(frame["emitted_timestamp_utc"], utc=True)
    frame["_month"] = timestamp.dt.month.astype(np.int8)
    frame["_hour"] = timestamp.dt.hour.astype(np.int8)
    profiles: dict[str, dict[tuple[object, ...], float]] = {}
    for sensor, column in VALUE_COLUMNS.items():
        station = frame.groupby(["station_id", "_month", "_hour"], observed=True)[column].median()
        cluster = frame.groupby(["cluster", "_month", "_hour"], observed=True)[column].median()
        global_profile = frame.groupby(["_month", "_hour"], observed=True)[column].median()
        profiles[f"{sensor}_station"] = {tuple(key): float(value) for key, value in station.dropna().items()}
        profiles[f"{sensor}_cluster"] = {tuple(key): float(value) for key, value in cluster.dropna().items()}
        profiles[f"{sensor}_global"] = {tuple(key): float(value) for key, value in global_profile.dropna().items()}
    return profiles


def expected_climatology(
    profiles: Mapping[str, Mapping[tuple[object, ...], float]], sensor: str,
    station_id: str, cluster: str, month: int, hour: int,
) -> float | None:
    station_value = profiles[f"{sensor}_station"].get((station_id, month, hour))
    if station_value is not None:
        return float(station_value)
    cluster_value = profiles[f"{sensor}_cluster"].get((cluster, month, hour))
    if cluster_value is not None:
        return float(cluster_value)
    global_value = profiles[f"{sensor}_global"].get((month, hour))
    return None if global_value is None else float(global_value)


def add_phase10_features(
    frame: pd.DataFrame,
    profiles: Mapping[str, Mapping[tuple[object, ...], float]],
) -> pd.DataFrame:
    """Append compliant trend/weather features while preserving input row order."""

    output = frame.reset_index(drop=True).copy()
    row_count = output.shape[0]
    results = {column: np.full(row_count, np.nan, dtype=np.float64) for column in TREND_FEATURES + WEATHER_GATE_FEATURES}
    # Offline replay can carry an explicit arrival order and arrival timestamp.
    # They are routing metadata, never model inputs.  This prevents a corrupted
    # or shifted packet timestamp from being sorted into the past/future and
    # changing causal trend state.  Production callers without these columns
    # retain the historical emitted-timestamp behaviour.
    order_columns = ["station_id", "stream_order"] if "stream_order" in output else [
        "station_id", "emitted_timestamp_utc"
    ]
    order = output.sort_values(order_columns, kind="stable").index.to_numpy()
    station_ids = output["station_id"].astype(str).to_numpy()
    clusters = output["cluster"].astype(str).to_numpy()
    time_column = (
        "causal_arrival_timestamp_utc"
        if "causal_arrival_timestamp_utc" in output
        else "emitted_timestamp_utc"
    )
    timestamps = output[time_column].astype(str).to_numpy()
    source: dict[str, np.ndarray] = {}
    needed = []
    for sensor in SENSORS:
        needed.extend([
            VALUE_COLUMNS[sensor], f"neighbor_{sensor}_residual", f"{sensor}_robust_z_24h",
            f"neighbor_{sensor}_agreement_fraction", f"neighbor_{sensor}_mad",
        ])
    for column in needed:
        source[column] = pd.to_numeric(output[column], errors="coerce").to_numpy(dtype=np.float64)

    current_station = None
    states: dict[str, SensorTrendState] = {}
    for index in order:
            station_id = station_ids[index]
            if station_id != current_station:
                current_station = station_id
                states = {sensor: SensorTrendState() for sensor in SENSORS}
            observed_time = _timestamp(timestamps[index])
            time_hours = observed_time.timestamp() / 3600.0
            cluster = clusters[index]
            agreement_values: list[float] = []
            standardized_disagreement: list[float] = []
            trend_disagreement: list[float] = []
            for sensor in SENSORS:
                raw_value = source[VALUE_COLUMNS[sensor]][index]
                raw_residual = source[f"neighbor_{sensor}_residual"][index]
                raw_robust_z = source[f"{sensor}_robust_z_24h"][index]
                value = float(raw_value) if np.isfinite(raw_value) else None
                residual = float(raw_residual) if np.isfinite(raw_residual) else None
                robust_z = float(raw_robust_z) if np.isfinite(raw_robust_z) else None
                values = states[sensor].update(time_hours, value, residual, robust_z)
                for suffix, result in values.items():
                    results[f"{sensor}_{suffix}"][index] = result
                expected = expected_climatology(
                    profiles, sensor, str(station_id), cluster, observed_time.month, observed_time.hour,
                )
                results[f"{sensor}_climatology_residual"][index] = (
                    np.nan if value is None or expected is None else value - expected
                )
                raw_agreement = source[f"neighbor_{sensor}_agreement_fraction"][index]
                if np.isfinite(raw_agreement):
                    agreement_values.append(float(raw_agreement))
                raw_neighbor_mad = source[f"neighbor_{sensor}_mad"][index]
                neighbor_mad = float(raw_neighbor_mad) if np.isfinite(raw_neighbor_mad) else None
                physical_floor = {"temperature": 0.5, "pressure": 0.5, "humidity": 2.0}[sensor]
                if residual is not None:
                    standardized_disagreement.append(abs(residual) / max(neighbor_mad or 0.0, physical_floor))
                slope_6h = values["neighbor_residual_slope_6h"]
                if np.isfinite(slope_6h):
                    trend_disagreement.append(abs(slope_6h) / physical_floor)

            if agreement_values:
                results["regional_agreement_mean"][index] = float(np.mean(agreement_values))
                results["regional_agreement_min"][index] = float(np.min(agreement_values))
                results["regional_agreeing_sensor_count"][index] = float(np.sum(np.asarray(agreement_values) >= 0.6))
            if standardized_disagreement:
                results["regional_standardized_disagreement_max"][index] = float(np.max(standardized_disagreement))
            if trend_disagreement:
                results["regional_trend_disagreement_mean"][index] = float(np.mean(trend_disagreement))

    for column, values in results.items():
        output[column] = values

    from skyguard.features.spatial_qc import add_spatial_qc
    output = add_spatial_qc(output)
    return output


def assert_phase10_compliance() -> None:
    forbidden = set(PHASE10_FEATURES) & FORBIDDEN_PHASE10_INPUTS
    if forbidden:
        raise AssertionError(f"Forbidden Phase 10 inputs: {sorted(forbidden)}")
    if any("dew" in column.lower() for column in PHASE10_FEATURES):
        raise AssertionError("Dew-point information is forbidden in Phase 10")

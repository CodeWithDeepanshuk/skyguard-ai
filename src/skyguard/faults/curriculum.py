"""Iteration 8 multi-climate weather and sensor-fault curriculum.

The injector changes only the three SIH26073 observation variables.  Calendar,
station, cluster and coordinates are routing metadata.  Every event is causal,
reproducible and non-overlapping, and the untouched source values are retained.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np
import pandas as pd


WEATHER_FAMILIES = (
    "regional_heatwave",
    "regional_cold_surge",
    "pressure_front",
    "humidity_surge",
    "dry_intrusion",
    "multivariate_storm",
)
FAULT_FAMILIES = ("bias", "drift", "frozen_sensor", "spike", "noise")
SENSOR_COLUMNS = {
    "temperature": "temperature_c",
    "pressure": "pressure_hpa",
    "humidity": "relative_humidity_pct",
}
LABEL_DEFAULTS = {
    "label_category": "normal",
    "is_anomaly": 0,
    "is_weather_event": 0,
    "episode_id": "",
    "anomaly_type": "normal",
    "anomaly_sensor": "",
    "anomaly_severity": "",
    "label_source": "none",
    "injection_seed": "",
    "stream_action": "emit",
    "timestamp_offset_seconds": 0,
}


@dataclass(frozen=True)
class CurriculumEvent:
    split: str
    scope: str
    episode_id: str
    label_category: str
    anomaly_type: str
    sensors: str
    stations: str
    cluster: str
    start_utc: str
    end_utc: str
    affected_rows: int
    random_seed: int
    description: str


class MultiClimateCurriculum:
    """Inject balanced weather and fault episodes into a canonical observation frame."""

    def __init__(self, frame: pd.DataFrame, split: str, seed: int = 17) -> None:
        required = {
            "station_id", "timestamp_utc", "cluster", "temperature_c",
            "pressure_hpa", "relative_humidity_pct",
        }
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Curriculum input is missing: {sorted(missing)}")
        self.frame = frame.reset_index(drop=True).copy()
        self.split = split
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.timestamps = pd.to_datetime(self.frame["timestamp_utc"], utc=True)
        self.reserved = np.zeros(len(self.frame), dtype=bool)
        self.events: list[CurriculumEvent] = []
        self.counter = 0
        for column, value in LABEL_DEFAULTS.items():
            self.frame[column] = value
        self.frame["split"] = split
        self.frame["original_timestamp_utc"] = self.frame["timestamp_utc"].astype(str)
        self.frame["original_temperature_c"] = pd.to_numeric(self.frame["temperature_c"], errors="coerce")
        self.frame["original_pressure_hpa"] = pd.to_numeric(self.frame["pressure_hpa"], errors="coerce")
        self.frame["original_relative_humidity_pct"] = pd.to_numeric(
            self.frame["relative_humidity_pct"], errors="coerce"
        )
        self.stations_by_cluster = {
            str(cluster): sorted(group["station_id"].astype(str).unique().tolist())
            for cluster, group in self.frame.groupby("cluster", sort=True)
        }
        # Official AWS archives do not share one cadence.  DWD is regular while
        # Indian ISD stations can report every 30, 60 or 180 minutes.  Injection
        # density must therefore scale with each station's observed cadence;
        # otherwise a genuine 3-hourly station can never satisfy an hourly point
        # count even when it fully covers the requested event window.
        self.cadence_hours: dict[str, float] = {}
        for station, group in self.frame.groupby("station_id", sort=False):
            times = pd.to_datetime(group["timestamp_utc"], utc=True).sort_values()
            delta = times.diff().dt.total_seconds().div(3600.0)
            plausible = delta[(delta > 0) & (delta <= 12)]
            self.cadence_hours[str(station)] = float(plausible.median()) if len(plausible) else 1.0

    def _minimum_points(self, station: str, duration_hours: float, floor: int) -> int:
        cadence = max(self.cadence_hours.get(str(station), 1.0), 1.0 / 6.0)
        half_expected_coverage = int(duration_hours / (2.0 * cadence))
        hourly_legacy_limit = max(floor, int(duration_hours / 3.0))
        return max(3, min(hourly_legacy_limit, max(3, half_expected_coverage)))

    def _next_id(self, weather: bool) -> str:
        self.counter += 1
        kind = "WX" if weather else "FLT"
        return f"{self.split.upper()}-I8-{kind}-{self.counter:04d}"

    def _random_start(self, start: pd.Timestamp, end: pd.Timestamp, duration_hours: float) -> pd.Timestamp:
        latest = end - pd.Timedelta(hours=duration_hours + 3.0)
        if latest <= start:
            raise ValueError(f"Invalid curriculum interval: {start} to {end}")
        seconds = int((latest - start).total_seconds())
        return start + pd.Timedelta(seconds=int(self.rng.integers(0, seconds + 1)))

    def _regional_window(
        self, cluster: str, start: pd.Timestamp, end: pd.Timestamp, duration_hours: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        stations = self.stations_by_cluster[cluster]
        if len(stations) < 3:
            raise RuntimeError(f"Regional weather needs at least three stations in {cluster}")
        for _ in range(800):
            anchor = self._random_start(start, end, duration_hours)
            selected: list[int] = []
            phases: list[float] = []
            covered = 0
            for offset, station in enumerate(stations):
                lag_hours = min(1.5, 0.5 * offset)
                station_start = anchor + pd.Timedelta(hours=lag_hours)
                station_end = station_start + pd.Timedelta(hours=duration_hours)
                mask = (
                    self.frame["station_id"].astype(str).eq(station).to_numpy()
                    & self.timestamps.ge(station_start).to_numpy()
                    & self.timestamps.le(station_end).to_numpy()
                    & ~self.reserved
                )
                indices = np.flatnonzero(mask)
                if len(indices) < self._minimum_points(station, duration_hours, floor=6):
                    continue
                covered += 1
                elapsed = (self.timestamps.iloc[indices] - station_start).dt.total_seconds().to_numpy() / 3600.0
                selected.extend(indices.tolist())
                phases.extend(np.clip(elapsed / duration_hours, 0.0, 1.0).tolist())
            if covered >= 3 and len(selected) >= 9:
                order = np.argsort(selected)
                return np.asarray(selected, dtype=int)[order], np.asarray(phases, dtype=float)[order]
        raise RuntimeError(f"Unable to find a non-overlapping regional window in {cluster}")

    def _station_window(
        self, cluster: str, start: pd.Timestamp, end: pd.Timestamp, duration_hours: float,
    ) -> np.ndarray:
        stations = self.stations_by_cluster[cluster]
        for _ in range(800):
            station = str(self.rng.choice(stations))
            anchor = self._random_start(start, end, duration_hours)
            finish = anchor + pd.Timedelta(hours=duration_hours)
            mask = (
                self.frame["station_id"].astype(str).eq(station).to_numpy()
                & self.timestamps.ge(anchor).to_numpy()
                & self.timestamps.le(finish).to_numpy()
                & ~self.reserved
            )
            indices = np.flatnonzero(mask)
            if len(indices) >= self._minimum_points(station, duration_hours, floor=4):
                return indices
        raise RuntimeError(f"Unable to find a non-overlapping station window in {cluster}")

    def _mark(
        self, indices: np.ndarray, scope: str, cluster: str, anomaly_type: str,
        sensors: Iterable[str], weather: bool, description: str,
    ) -> CurriculumEvent:
        episode_id = self._next_id(weather)
        sensor_list = list(sensors)
        self.frame.loc[indices, "label_category"] = "genuine_weather_scenario" if weather else "sensor_fault"
        self.frame.loc[indices, "is_anomaly"] = 0 if weather else 1
        self.frame.loc[indices, "is_weather_event"] = 1 if weather else 0
        self.frame.loc[indices, "episode_id"] = episode_id
        self.frame.loc[indices, "anomaly_type"] = anomaly_type
        self.frame.loc[indices, "anomaly_sensor"] = ",".join(sensor_list)
        self.frame.loc[indices, "anomaly_severity"] = "event" if weather else "subtle"
        self.frame.loc[indices, "label_source"] = "iteration8_synthetic_weather" if weather else "iteration8_synthetic_fault"
        self.frame.loc[indices, "injection_seed"] = str(self.seed)
        self.reserved[indices] = True
        times = self.timestamps.iloc[indices]
        stations = sorted(self.frame.loc[indices, "station_id"].astype(str).unique().tolist())
        event = CurriculumEvent(
            split=self.split,
            scope=scope,
            episode_id=episode_id,
            label_category="genuine_weather_scenario" if weather else "sensor_fault",
            anomaly_type=anomaly_type,
            sensors=",".join(sensor_list),
            stations=",".join(stations),
            cluster=cluster,
            start_utc=times.min().isoformat(),
            end_utc=times.max().isoformat(),
            affected_rows=int(len(indices)),
            random_seed=self.seed,
            description=description,
        )
        self.events.append(event)
        return event

    def inject_weather(
        self, family: str, cluster: str, scope: str, start: str | pd.Timestamp, end: str | pd.Timestamp,
    ) -> CurriculumEvent:
        if family not in WEATHER_FAMILIES:
            raise ValueError(f"Unknown weather family: {family}")
        duration = float(self.rng.uniform(12.0, 30.0))
        indices, phase = self._regional_window(cluster, pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC"), duration)
        pulse = 0.65 + 0.35 * np.sin(np.pi * phase)
        ramp = 0.25 + 0.75 * phase
        temperature = pd.to_numeric(self.frame.loc[indices, "temperature_c"]).to_numpy(float)
        pressure = pd.to_numeric(self.frame.loc[indices, "pressure_hpa"]).to_numpy(float)
        humidity = pd.to_numeric(self.frame.loc[indices, "relative_humidity_pct"]).to_numpy(float)

        if family == "regional_heatwave":
            temperature += float(self.rng.uniform(3.0, 7.0)) * pulse
            humidity -= float(self.rng.uniform(3.0, 12.0)) * pulse
        elif family == "regional_cold_surge":
            temperature -= float(self.rng.uniform(3.0, 9.0)) * ramp
            pressure += float(self.rng.uniform(2.0, 7.0)) * ramp
            humidity += float(self.rng.uniform(3.0, 15.0)) * pulse
        elif family == "pressure_front":
            pressure -= float(self.rng.uniform(5.0, 14.0)) * ramp
            temperature -= float(self.rng.uniform(0.5, 3.0)) * ramp
            humidity += float(self.rng.uniform(6.0, 20.0)) * pulse
        elif family == "humidity_surge":
            humidity += float(self.rng.uniform(15.0, 35.0)) * pulse
            temperature -= float(self.rng.uniform(0.5, 2.5)) * pulse
        elif family == "dry_intrusion":
            humidity -= float(self.rng.uniform(15.0, 35.0)) * pulse
            temperature += float(self.rng.uniform(1.0, 4.0)) * pulse
            pressure += float(self.rng.uniform(0.5, 3.0)) * ramp
        elif family == "multivariate_storm":
            pressure -= float(self.rng.uniform(7.0, 16.0)) * pulse
            humidity += float(self.rng.uniform(15.0, 35.0)) * pulse
            temperature -= float(self.rng.uniform(1.5, 5.0)) * pulse

        self.frame.loc[indices, "temperature_c"] = np.clip(temperature, -60.0, 60.0)
        self.frame.loc[indices, "pressure_hpa"] = np.clip(pressure, 850.0, 1120.0)
        self.frame.loc[indices, "relative_humidity_pct"] = np.clip(humidity, 0.0, 100.0)
        return self._mark(
            indices, scope, cluster, family, SENSOR_COLUMNS, True,
            f"Coherent {family} across at least three neighbour stations with causal spatial lag.",
        )

    def inject_fault(
        self, family: str, cluster: str, scope: str, start: str | pd.Timestamp, end: str | pd.Timestamp,
    ) -> CurriculumEvent:
        if family not in FAULT_FAMILIES:
            raise ValueError(f"Unknown fault family: {family}")
        duration = 1.0 if family == "spike" else float(self.rng.uniform(8.0, 54.0))
        if family == "spike":
            start_time, end_time = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
            candidates = np.flatnonzero(
                self.frame["cluster"].astype(str).eq(cluster).to_numpy()
                & self.timestamps.ge(start_time).to_numpy()
                & self.timestamps.le(end_time).to_numpy()
                & ~self.reserved
            )
            if not len(candidates):
                raise RuntimeError(f"Unable to find an unreserved spike row in {cluster}")
            indices = np.asarray([int(self.rng.choice(candidates))], dtype=int)
        else:
            indices = self._station_window(
                cluster, pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC"), duration
            )
        sensor = str(self.rng.choice(list(SENSOR_COLUMNS)))
        column = SENSOR_COLUMNS[sensor]
        values = pd.to_numeric(self.frame.loc[indices, column]).to_numpy(float)
        magnitudes = {
            "temperature": (0.8, 3.5),
            "pressure": (1.2, 6.0),
            "humidity": (4.0, 18.0),
        }
        magnitude = float(self.rng.uniform(*magnitudes[sensor])) * float(self.rng.choice([-1.0, 1.0]))
        if family == "bias":
            values += magnitude
        elif family == "drift":
            values += magnitude * np.linspace(0.0, 1.0, len(indices))
        elif family == "frozen_sensor":
            values[:] = values[0]
        elif family == "spike":
            values += magnitude * 4.0
        elif family == "noise":
            values += self.rng.normal(0.0, abs(magnitude), len(indices))
        bounds = {
            "temperature": (-100.0, 100.0),
            "pressure": (700.0, 1300.0),
            "humidity": (-20.0, 120.0),
        }[sensor]
        self.frame.loc[indices, column] = np.clip(values, *bounds)
        return self._mark(
            indices, scope, cluster, family, [sensor], False,
            f"{family} applied to one {sensor} sensor with a low-to-moderate severity ladder.",
        )

    def build_training(self, start: str, end: str, weather_repetitions: int = 4, fault_repetitions: int = 8) -> None:
        for cluster in sorted(self.stations_by_cluster):
            for family in WEATHER_FAMILIES:
                for _ in range(weather_repetitions):
                    self.inject_weather(family, cluster, "train", start, end)
            for family in FAULT_FAMILIES:
                for _ in range(fault_repetitions):
                    self.inject_fault(family, cluster, "train", start, end)

    def build_validation(self, scopes: dict[str, tuple[str, str]]) -> None:
        for scope, (start, end) in scopes.items():
            for cluster in sorted(self.stations_by_cluster):
                for family in WEATHER_FAMILIES:
                    self.inject_weather(family, cluster, scope, start, end)
                for family in FAULT_FAMILIES:
                    self.inject_fault(family, cluster, scope, start, end)

    def event_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(event) for event in self.events])

    def validate(self) -> dict[str, object]:
        event_ids = self.frame.loc[self.reserved, "episode_id"].astype(str)
        errors: list[str] = []
        if not event_ids.ne("").all():
            errors.append("reserved rows without episode IDs")
        if event_ids.groupby(event_ids.index).size().max() != 1:
            errors.append("overlapping event assignment")
        weather = self.event_frame().query("label_category == 'genuine_weather_scenario'")
        faults = self.event_frame().query("label_category == 'sensor_fault'")
        if not set(weather["anomaly_type"]) <= set(WEATHER_FAMILIES):
            errors.append("unknown weather family in event log")
        if not set(faults["anomaly_type"]) <= set(FAULT_FAMILIES):
            errors.append("unknown fault family in event log")
        return {
            "status": "PASS" if not errors else "FAIL",
            "rows": int(len(self.frame)),
            "event_rows": int(self.reserved.sum()),
            "event_row_fraction": float(self.reserved.mean()),
            "weather_events": int(len(weather)),
            "fault_events": int(len(faults)),
            "weather_families": sorted(weather["anomaly_type"].unique().tolist()),
            "fault_families": sorted(faults["anomaly_type"].unique().tolist()),
            "errors": errors,
        }

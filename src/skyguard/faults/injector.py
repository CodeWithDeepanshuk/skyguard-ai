"""Reproducible fault injection on clean real weather observations."""

from __future__ import annotations

import bisect
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta

from .models import Episode, FAULT_TYPES


SENSOR_FIELDS = {
    "temperature": "temperature_c",
    "pressure": "pressure_hpa",
    "humidity": "relative_humidity_pct",
}

LABEL_FIELDS = (
    "split", "label_category", "is_anomaly", "is_weather_event", "episode_id",
    "anomaly_type", "anomaly_sensor", "anomaly_severity", "label_source",
    "injection_seed", "stream_action", "timestamp_offset_seconds",
    "original_timestamp_utc", "original_temperature_c", "original_pressure_hpa",
    "original_relative_humidity_pct",
)


class FaultInjector:
    def __init__(self, rows: list[dict[str, str]], split: str, seed: int) -> None:
        self.rows = rows
        self.split = split
        self.seed = seed
        self.rng = random.Random(seed)
        self.reserved: set[int] = set()
        self.episodes: list[Episode] = []
        self.station_indices: defaultdict[str, list[int]] = defaultdict(list)
        self.station_times: dict[str, list[datetime]] = {}
        self.cluster_stations: defaultdict[str, set[str]] = defaultdict(set)
        self.counter = 0

        for index, row in enumerate(self.rows):
            row.update({
                "split": split,
                "label_category": "normal",
                "is_anomaly": "0",
                "is_weather_event": "0",
                "episode_id": "",
                "anomaly_type": "normal",
                "anomaly_sensor": "",
                "anomaly_severity": "",
                "label_source": "none",
                "injection_seed": "",
                "stream_action": "emit",
                "timestamp_offset_seconds": "0",
                "original_timestamp_utc": row["timestamp_utc"],
                "original_temperature_c": row["temperature_c"],
                "original_pressure_hpa": row["pressure_hpa"],
                "original_relative_humidity_pct": row["relative_humidity_pct"],
            })
            self.station_indices[row["station_id"]].append(index)
            self.cluster_stations[row["cluster"]].add(row["station_id"])
        for station_id, indices in self.station_indices.items():
            self.station_times[station_id] = [self._time(self.rows[index]) for index in indices]

    @staticmethod
    def _time(row: dict[str, str]) -> datetime:
        return datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z"))

    @staticmethod
    def _value(row: dict[str, str], sensor: str) -> float:
        return float(row[SENSOR_FIELDS[sensor]])

    @staticmethod
    def _set_value(row: dict[str, str], sensor: str, value: float) -> None:
        row[SENSOR_FIELDS[sensor]] = f"{value:.4f}"

    @staticmethod
    def _clean(row: dict[str, str]) -> bool:
        try:
            temperature = float(row["temperature_c"])
            pressure = float(row["pressure_hpa"])
            humidity = float(row["relative_humidity_pct"])
        except (TypeError, ValueError):
            return False
        if not (-60.0 <= temperature <= 60.0 and 870.0 <= pressure <= 1075.0 and 0.0 <= humidity <= 100.0):
            return False
        suspect = {"2", "3", "6", "7"}
        return row.get("temperature_quality", "") not in suspect and row.get("pressure_quality", "") not in suspect

    def _next_id(self, category: str) -> str:
        self.counter += 1
        prefix = "WX" if category == "genuine_weather_scenario" else "FLT"
        return f"{self.split.upper()}-{prefix}-{self.counter:04d}"

    def _single(self) -> list[int]:
        candidates = [index for index, row in enumerate(self.rows) if index not in self.reserved and self._clean(row)]
        if not candidates:
            raise RuntimeError("No unreserved clean row is available for injection.")
        return [self.rng.choice(candidates)]

    def _window(self, minimum_hours: float, maximum_hours: float, minimum_points: int) -> list[int]:
        station_ids = list(self.station_indices)
        for _ in range(500):
            station_id = self.rng.choice(station_ids)
            indices = self.station_indices[station_id]
            eligible_starts = [index for index in indices if index not in self.reserved and self._clean(self.rows[index])]
            if not eligible_starts:
                continue
            start_index = self.rng.choice(eligible_starts)
            start = self._time(self.rows[start_index])
            end = start + timedelta(hours=self.rng.uniform(minimum_hours, maximum_hours))
            times = self.station_times[station_id]
            left = bisect.bisect_left(times, start)
            right = bisect.bisect_right(times, end)
            selected = [
                index for index in indices[left:right]
                if index not in self.reserved and self._clean(self.rows[index])
            ]
            if len(selected) >= minimum_points:
                return selected
        raise RuntimeError(f"Unable to find a clean {minimum_hours}-{maximum_hours} hour window.")

    def _mark(
        self,
        indices: list[int],
        anomaly_type: str,
        sensors: list[str],
        severity: str,
        stream_action: str,
        description: str,
        category: str = "sensor_fault",
    ) -> Episode:
        episode_id = self._next_id(category)
        is_fault = category == "sensor_fault"
        for index in indices:
            row = self.rows[index]
            row.update({
                "label_category": category,
                "is_anomaly": "1" if is_fault else "0",
                "is_weather_event": "0" if is_fault else "1",
                "episode_id": episode_id,
                "anomaly_type": anomaly_type,
                "anomaly_sensor": ",".join(sensors),
                "anomaly_severity": severity,
                "label_source": "synthetic_fault" if is_fault else "synthetic_weather_scenario",
                "injection_seed": str(self.seed),
                "stream_action": stream_action,
            })
            self.reserved.add(index)
        times = [self._time(self.rows[index]) for index in indices]
        stations = sorted({self.rows[index]["station_id"] for index in indices})
        episode = Episode(
            split=self.split,
            episode_id=episode_id,
            label_category=category,
            anomaly_type=anomaly_type,
            sensors=",".join(sensors),
            stations=",".join(stations),
            start_utc=min(times).isoformat(timespec="seconds") + "Z",
            end_utc=max(times).isoformat(timespec="seconds") + "Z",
            severity=severity,
            affected_rows=len(indices),
            stream_action=stream_action,
            random_seed=self.seed,
            description=description,
        )
        self.episodes.append(episode)
        return episode

    def inject(self, anomaly_type: str) -> Episode:
        if anomaly_type not in FAULT_TYPES:
            raise ValueError(f"Unknown fault type: {anomaly_type}")
        severity = self.rng.choices(["low", "medium", "high"], weights=[2, 5, 3], k=1)[0]

        if anomaly_type in {"spike", "sudden_drop", "unit_error", "scaling_error"}:
            indices = self._single()
        elif anomaly_type in {"duplicate_packet", "timestamp_error", "communication_corruption"}:
            indices = self._window(0.5, 6.0, 1)[: self.rng.randint(1, 3)]
        elif anomaly_type == "drift":
            indices = self._window(24.0, 72.0, 8)
        elif anomaly_type in {"frozen_sensor", "multi_sensor_failure"}:
            indices = self._window(12.0, 36.0, 4)
        elif anomaly_type == "bias":
            indices = self._window(12.0, 48.0, 4)
        elif anomaly_type == "noise":
            indices = self._window(6.0, 24.0, 4)
        elif anomaly_type == "dropout":
            indices = self._window(6.0, 24.0, 2)
        else:
            raise AssertionError(anomaly_type)

        sensor = self.rng.choice(list(SENSOR_FIELDS))
        sensors = [sensor]
        stream_action = "emit"

        if anomaly_type == "spike":
            magnitude = {"temperature": (8, 25), "pressure": (10, 50), "humidity": (30, 80)}[sensor]
            delta = self.rng.uniform(*magnitude) * self.rng.choice([-1, 1])
            self._set_value(self.rows[indices[0]], sensor, self._value(self.rows[indices[0]], sensor) + delta)
            description = f"Single-reading {sensor} spike of {delta:.2f}."
        elif anomaly_type == "sudden_drop":
            magnitude = {"temperature": (8, 25), "pressure": (20, 80), "humidity": (30, 90)}[sensor]
            delta = self.rng.uniform(*magnitude)
            self._set_value(self.rows[indices[0]], sensor, self._value(self.rows[indices[0]], sensor) - delta)
            description = f"Single-reading {sensor} drop of {delta:.2f}."
        elif anomaly_type == "bias":
            magnitude = {"temperature": (2, 6), "pressure": (3, 15), "humidity": (10, 30)}[sensor]
            delta = self.rng.uniform(*magnitude) * self.rng.choice([-1, 1])
            for index in indices:
                self._set_value(self.rows[index], sensor, self._value(self.rows[index], sensor) + delta)
            description = f"Constant {sensor} bias of {delta:.2f} across a contiguous episode."
        elif anomaly_type == "drift":
            magnitude = {"temperature": (3, 10), "pressure": (5, 25), "humidity": (15, 50)}[sensor]
            final_delta = self.rng.uniform(*magnitude) * self.rng.choice([-1, 1])
            denominator = max(len(indices) - 1, 1)
            for offset, index in enumerate(indices):
                self._set_value(self.rows[index], sensor, self._value(self.rows[index], sensor) + final_delta * offset / denominator)
            description = f"Gradual {sensor} drift ending at {final_delta:.2f} from baseline."
        elif anomaly_type == "noise":
            sigma = {"temperature": (3, 8), "pressure": (4, 15), "humidity": (15, 35)}[sensor]
            standard_deviation = self.rng.uniform(*sigma)
            for index in indices:
                self._set_value(self.rows[index], sensor, self._value(self.rows[index], sensor) + self.rng.gauss(0, standard_deviation))
            description = f"Excessive zero-mean {sensor} noise with sigma {standard_deviation:.2f}."
        elif anomaly_type == "frozen_sensor":
            fixed = self._value(self.rows[indices[0]], sensor)
            for index in indices:
                self._set_value(self.rows[index], sensor, fixed)
            description = f"{sensor.capitalize()} frozen at {fixed:.2f} for the episode."
        elif anomaly_type == "dropout":
            stream_action = "drop"
            sensor, sensors = "communication", ["communication"]
            description = "Consecutive station records are removed from the emitted stream."
        elif anomaly_type == "duplicate_packet":
            stream_action = "duplicate"
            sensor, sensors = "communication", ["communication"]
            description = "Selected station records are emitted twice by the replay engine."
        elif anomaly_type == "timestamp_error":
            stream_action = "timestamp_shift"
            sensor, sensors = "timestamp", ["timestamp"]
            offset = self.rng.choice([-1, 1]) * self.rng.randint(1, 6) * 3600
            for index in indices:
                self.rows[index]["timestamp_offset_seconds"] = str(offset)
            description = f"Selected timestamps are shifted by {offset} seconds."
        elif anomaly_type == "unit_error":
            sensor, sensors = "temperature", ["temperature"]
            value = self._value(self.rows[indices[0]], sensor)
            self._set_value(self.rows[indices[0]], sensor, value * 9.0 / 5.0 + 32.0)
            description = "Celsius temperature is interpreted and emitted as Fahrenheit."
        elif anomaly_type == "scaling_error":
            sensor, sensors = self.rng.choice(["pressure", "humidity"]), []
            sensors = [sensor]
            factor = self.rng.choice([0.1, 10.0]) if sensor == "pressure" else self.rng.choice([0.01, 10.0])
            self._set_value(self.rows[indices[0]], sensor, self._value(self.rows[indices[0]], sensor) * factor)
            description = f"{sensor.capitalize()} is multiplied by scaling factor {factor:g}."
        elif anomaly_type == "communication_corruption":
            sensors = ["temperature", "pressure", "humidity"]
            for index in indices:
                self._set_value(self.rows[index], "temperature", self.rng.uniform(-150, 150))
                self._set_value(self.rows[index], "pressure", self.rng.uniform(0, 2000))
                self._set_value(self.rows[index], "humidity", self.rng.uniform(-50, 200))
            description = "Communication corruption replaces all primary values with implausible numbers."
        elif anomaly_type == "multi_sensor_failure":
            sensors = ["temperature", "pressure", "humidity"]
            fixed = {sensor_name: self._value(self.rows[indices[0]], sensor_name) for sensor_name in sensors}
            for index in indices:
                for sensor_name, value in fixed.items():
                    self._set_value(self.rows[index], sensor_name, value)
            description = "All primary sensors remain constant across the episode."
        else:
            raise AssertionError(anomaly_type)

        return self._mark(indices, anomaly_type, sensors, severity, stream_action, description)

    def inject_regional_weather_event(self) -> Episode:
        clusters = [cluster for cluster, stations in self.cluster_stations.items() if len(stations) >= 3]
        for _ in range(500):
            cluster = self.rng.choice(clusters)
            stations = sorted(self.cluster_stations[cluster])
            anchor_station = self.rng.choice(stations)
            anchor_candidates = [
                index for index in self.station_indices[anchor_station]
                if index not in self.reserved and self._clean(self.rows[index])
            ]
            if not anchor_candidates:
                continue
            anchor = self.rng.choice(anchor_candidates)
            start = self._time(self.rows[anchor])
            end = start + timedelta(hours=self.rng.uniform(12.0, 36.0))
            selected: list[int] = []
            covered_stations: list[str] = []
            for station_id in stations:
                indices = self.station_indices[station_id]
                times = self.station_times[station_id]
                left = bisect.bisect_left(times, start)
                right = bisect.bisect_right(times, end)
                station_rows = [
                    index for index in indices[left:right]
                    if index not in self.reserved and self._clean(self.rows[index])
                ]
                if len(station_rows) >= 2:
                    selected.extend(station_rows)
                    covered_stations.append(station_id)
            if len(covered_stations) < 3 or len(selected) < 8:
                continue
            delta = self.rng.uniform(3.0, 8.0)
            duration = max((end - start).total_seconds(), 1.0)
            for index in selected:
                phase = (self._time(self.rows[index]) - start).total_seconds() / duration
                coherent_delta = delta * (0.65 + 0.35 * math.sin(math.pi * max(0.0, min(1.0, phase))))
                value = min(59.5, self._value(self.rows[index], "temperature") + coherent_delta)
                self._set_value(self.rows[index], "temperature", value)
            return self._mark(
                selected, "regional_temperature_event", ["temperature"], "event", "emit",
                f"Coherent regional temperature rise peaking near {delta:.2f} °C across {len(covered_stations)} stations.",
                category="genuine_weather_scenario",
            )
        raise RuntimeError("Unable to construct a non-overlapping regional weather scenario.")

    def inject_suite(self, episodes_per_fault: int, weather_events: int) -> list[Episode]:
        schedule = [fault_type for fault_type in FAULT_TYPES for _ in range(episodes_per_fault)]
        self.rng.shuffle(schedule)
        for fault_type in schedule:
            self.inject(fault_type)
        for _ in range(weather_events):
            self.inject_regional_weather_event()
        return self.episodes

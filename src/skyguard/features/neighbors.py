"""Backward-only geographic neighbour feature alignment."""

from __future__ import annotations

import bisect
import math
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median

from .contracts import FeatureConfig, NEIGHBOR_SUFFIXES, SENSORS
from .temporal import optional_float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    value = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 6371.0 * 2.0 * math.asin(math.sqrt(value))


class NeighborIndex:
    def __init__(self, context_rows: list[dict[str, str]], stations: dict[str, dict[str, str]], config: FeatureConfig | None = None) -> None:
        self.config = config or FeatureConfig()
        self.stations = stations
        self.series: defaultdict[str, list[tuple[datetime, dict[str, str]]]] = defaultdict(list)
        for row in context_rows:
            if row.get("stream_action", "emit") in {"drop", "timestamp_shift"}:
                continue
            timestamp = datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z"))
            self.series[row["station_id"]].append((timestamp, row))
        self.times: dict[str, list[datetime]] = {}
        for station_id, values in self.series.items():
            values.sort(key=lambda item: item[0])
            self.times[station_id] = [item[0] for item in values]

        self.candidates: dict[str, list[tuple[str, float]]] = {}
        for station_id, station in stations.items():
            choices: list[tuple[str, float]] = []
            for other_id, other in stations.items():
                if other_id == station_id or other["cluster"] != station["cluster"] or other_id not in self.series:
                    continue
                distance = haversine_km(
                    float(station["latitude"]), float(station["longitude"]),
                    float(other["latitude"]), float(other["longitude"]),
                )
                choices.append((other_id, distance))
            self.candidates[station_id] = sorted(choices, key=lambda item: item[1])[: self.config.max_neighbors]

    def features(self, row: dict[str, str]) -> dict[str, object]:
        output: dict[str, object] = {
            "neighbor_station_count": 0,
            "neighbor_min_age_minutes": "",
            "neighbor_max_age_minutes": "",
            "nearest_neighbor_km": "",
        }
        for sensor in SENSORS:
            for suffix in NEIGHBOR_SUFFIXES:
                output[f"neighbor_{sensor}_{suffix}"] = ""
        if row.get("stream_action", "emit") == "drop":
            return output

        query = datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z")) + timedelta(
            seconds=int(row.get("timestamp_offset_seconds", "0") or 0)
        )
        matched: list[tuple[dict[str, str], float, float]] = []
        for station_id, distance in self.candidates.get(row["station_id"], []):
            times = self.times[station_id]
            position = bisect.bisect_right(times, query) - 1
            if position < 0:
                continue
            timestamp, neighbor_row = self.series[station_id][position]
            age_minutes = (query - timestamp).total_seconds() / 60.0
            if 0.0 <= age_minutes <= self.config.neighbor_tolerance_minutes:
                matched.append((neighbor_row, distance, age_minutes))

        if not matched:
            return output
        output["neighbor_station_count"] = len(matched)
        output["neighbor_min_age_minutes"] = round(min(item[2] for item in matched), 4)
        output["neighbor_max_age_minutes"] = round(max(item[2] for item in matched), 4)
        output["nearest_neighbor_km"] = round(min(item[1] for item in matched), 4)

        agreement_limits = {
            "temperature": self.config.temperature_neighbor_agreement,
            "pressure": self.config.pressure_neighbor_agreement,
            "humidity": self.config.humidity_neighbor_agreement,
        }
        for sensor, field in SENSORS.items():
            current = optional_float(row.get(field))
            values: list[tuple[float, float]] = []
            for neighbor_row, distance, _ in matched:
                value = optional_float(neighbor_row.get(field))
                if value is not None:
                    values.append((value, distance))
            prefix = f"neighbor_{sensor}_"
            output[prefix + "count"] = len(values)
            if not values:
                continue
            raw = [item[0] for item in values]
            weights = [1.0 / max(item[1], 1.0) ** 2 for item in values]
            weighted_mean = sum(value * weight for value, weight in zip(raw, weights)) / sum(weights)
            center = median(raw)
            mad = median([abs(value - center) for value in raw])
            output[prefix + "weighted_mean"] = round(weighted_mean, 6)
            output[prefix + "median"] = round(center, 6)
            output[prefix + "mad"] = round(mad, 6)
            if current is not None:
                differences = [abs(current - value) for value in raw]
                output[prefix + "residual"] = round(current - center, 6)
                output[prefix + "max_abs_difference"] = round(max(differences), 6)
                output[prefix + "agreement_fraction"] = round(
                    sum(difference <= agreement_limits[sensor] for difference in differences) / len(differences), 6
                )
        return output

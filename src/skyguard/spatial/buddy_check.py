"""NOAA MADIS-Grade Spatial Buddy Check for Atmospheric Telemetry.

Performs robust leave-one-out spatial consistency testing across neighbouring AWS stations.
Calculates distance-weighted median, elevation-lapse adjusted estimates,
and Scaled Median Absolute Deviation (MAD) to detect localized sensor failures.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


SIGMA_MIN = {
    "temperature": 0.6,    # Deg C minimum noise floor
    "humidity": 3.0,       # % RH minimum noise floor
    "pressure": 0.8,       # hPa minimum noise floor
}

LAPSE_RATE_C_PER_M = -0.0065  # Environmental lapse rate: -6.5 C per 1000m


@dataclass
class NeighborContribution:
    station_id: str
    station_name: str
    distance_km: float
    raw_value: float
    adjusted_value: float
    weight: float
    residual: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BuddyCheckResult:
    parameter: str
    observed_value: float
    consensus_value: float
    difference: float
    mad_scale: float
    effective_sigma: float
    z_spatial: float
    status: str  # CONSISTENT | SUSPECT | DISCREPANT
    num_neighbors: int
    estimators: Dict[str, float]
    neighbors: List[NeighborContribution]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["neighbors"] = [n.to_dict() if hasattr(n, "to_dict") else n for n in self.neighbors]
        return d


def adjust_for_elevation(
    parameter: str,
    neighbor_val: float,
    neighbor_elev_m: float,
    target_elev_m: float,
) -> float:
    """Apply physical atmospheric lapse rate adjustments between differing elevations."""
    delta_h = target_elev_m - neighbor_elev_m
    if parameter == "temperature":
        # T_target = T_neighbor + lapse_rate * delta_h
        return neighbor_val + (LAPSE_RATE_C_PER_M * delta_h)
    elif parameter == "pressure":
        # Standard barometric approximation: ~12 hPa decrease per 100m elevation gain near sea level
        # P_target = P_neighbor * (1 - 0.0065 * delta_h / 288.15) ** 5.255
        try:
            factor = (1.0 - (0.0065 * delta_h / 288.15)) ** 5.255
            return neighbor_val * factor
        except Exception:
            return neighbor_val
    # Relative humidity is not adjusted by linear lapse rate directly
    return neighbor_val


def calculate_weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Compute exact weighted median for robustness against corrupted neighbour sensors."""
    if len(values) == 0:
        return 0.0
    sorter = np.argsort(values)
    sorted_values = values[sorter]
    sorted_weights = weights[sorter]
    cum_weights = np.cumsum(sorted_weights)
    cutoff = sorted_weights.sum() / 2.0
    idx = np.searchsorted(cum_weights, cutoff)
    return float(sorted_values[min(idx, len(sorted_values) - 1)])


class SpatialBuddyCheck:
    """NOAA MADIS-grade spatial consistency engine."""

    def __init__(self, power_decay: float = 2.0):
        self.power_decay = power_decay

    def check(
        self,
        parameter: str,
        target_station_id: str,
        target_value: float,
        target_elevation_m: float,
        neighbor_observations: List[Dict[str, Any]],
    ) -> BuddyCheckResult:
        """Run leave-one-out spatial buddy check against valid neighbour observations.

        `neighbor_observations` is a list of dicts containing:
        - station_id
        - station_name
        - distance_km
        - elevation_m
        - value (measured parameter value)
        """
        valid_neighbors = [
            n for n in neighbor_observations
            if n.get("value") is not None and not math.isnan(n["value"]) and n.get("distance_km", 0) > 0
        ]

        if not valid_neighbors:
            # No neighbours available: cannot disprove observation
            return BuddyCheckResult(
                parameter=parameter,
                observed_value=target_value,
                consensus_value=target_value,
                difference=0.0,
                mad_scale=1.0,
                effective_sigma=1.0,
                z_spatial=0.0,
                status="ISOLATED_UNVERIFIABLE",
                num_neighbors=0,
                estimators={"observed": target_value},
                neighbors=[],
            )

        distances = np.array([max(0.5, float(n["distance_km"])) for n in valid_neighbors])
        raw_vals = np.array([float(n["value"]) for n in valid_neighbors])
        elevations = np.array([float(n.get("elevation_m") or 0.0) for n in valid_neighbors])

        # Inverse distance weights: w_i = 1 / (d_i ^ p)
        weights = 1.0 / (distances ** self.power_decay)
        normalized_weights = weights / np.sum(weights)

        # 1. Elevation-adjusted values
        adjusted_vals = np.array([
            adjust_for_elevation(parameter, raw_vals[i], elevations[i], target_elevation_m)
            for i in range(len(valid_neighbors))
        ])

        # 2. Estimator comparison:
        # a) Weighted mean of adjusted values
        weighted_mean = float(np.sum(adjusted_vals * normalized_weights))

        # b) Simple median of adjusted values
        simple_median = float(np.median(adjusted_vals))

        # c) Weighted robust median
        robust_median = calculate_weighted_median(adjusted_vals, weights)

        # Selected primary consensus estimator: robust_median
        consensus_val = round(robust_median, 2)
        difference = round(target_value - consensus_val, 2)

        # 3. Median Absolute Deviation (MAD)
        abs_deviations = np.abs(adjusted_vals - simple_median)
        mad = float(np.median(abs_deviations))
        mad_scaled = round(1.4826 * mad, 3)

        # Minimum noise floor
        floor = SIGMA_MIN.get(parameter.lower(), 0.5)
        effective_sigma = max(mad_scaled, floor)

        # Spatial Z-score
        z_spatial = round(difference / effective_sigma, 2)

        # Classification
        abs_z = abs(z_spatial)
        if abs_z <= 2.0:
            status = "CONSISTENT"
        elif abs_z <= 3.0:
            status = "SUSPECT"
        else:
            status = "DISCREPANT"

        # Build neighbor contribution details
        contributions: List[NeighborContribution] = []
        for i, n in enumerate(valid_neighbors):
            res = round(float(raw_vals[i] - consensus_val), 2)
            contributions.append(
                NeighborContribution(
                    station_id=n["station_id"],
                    station_name=n.get("station_name", n["station_id"]),
                    distance_km=round(float(distances[i]), 1),
                    raw_value=round(float(raw_vals[i]), 2),
                    adjusted_value=round(float(adjusted_vals[i]), 2),
                    weight=round(float(normalized_weights[i]), 4),
                    residual=res,
                )
            )

        return BuddyCheckResult(
            parameter=parameter,
            observed_value=round(target_value, 2),
            consensus_value=consensus_val,
            difference=difference,
            mad_scale=mad_scaled,
            effective_sigma=round(effective_sigma, 3),
            z_spatial=z_spatial,
            status=status,
            num_neighbors=len(valid_neighbors),
            estimators={
                "distance_weighted_mean": round(weighted_mean, 2),
                "simple_median": round(simple_median, 2),
                "robust_weighted_median": round(robust_median, 2),
            },
            neighbors=contributions,
        )

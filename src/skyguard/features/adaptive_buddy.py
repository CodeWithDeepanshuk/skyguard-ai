"""Leakage-safe robust buddy checks for irregular station networks."""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1.0, a)))


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    return float(values[np.searchsorted(np.cumsum(weights), weights.sum()/2, side="left")])


def buddy_expectation(target_id: str, target_lat: float, target_lon: float,
                      candidates: Iterable[dict], value_key: str, min_neighbors: int = 2,
                      radii_km: tuple[float, ...] = (50, 100, 200, 350),
                      max_neighbors: int = 12, gaussian_bandwidth_km: float = 100) -> dict:
    """Estimate target value from contemporaneous peers; target is always excluded."""
    peers = []
    for row in candidates:
        if str(row.get("station_id")) == str(target_id):
            continue
        try:
            value = float(row[value_key])
            distance = haversine_km(target_lat, target_lon, float(row["latitude"]), float(row["longitude"]))
        except (KeyError, TypeError, ValueError):
            continue
        if np.isfinite(value):
            peers.append((distance, value, str(row.get("station_id"))))
    peers.sort()
    chosen, radius = [], None
    for candidate_radius in radii_km:
        chosen = [row for row in peers if row[0] <= candidate_radius][:max_neighbors]
        if len(chosen) >= min_neighbors:
            radius = candidate_radius
            break
    if len(chosen) < min_neighbors:
        return {"available": False, "expected": None, "neighbor_count": len(chosen),
                "radius_km": radius, "neighbor_ids": [row[2] for row in chosen], "target_excluded": True}
    distances = np.array([row[0] for row in chosen], dtype=float)
    values = np.array([row[1] for row in chosen], dtype=float)
    weights = np.exp(-0.5*(distances/max(gaussian_bandwidth_km, 1e-6))**2)
    center = weighted_median(values, weights)
    mad = weighted_median(np.abs(values-center), weights)
    return {"available": True, "expected": center, "robust_scale": max(1.4826*mad, 1e-6),
            "neighbor_count": len(chosen), "radius_km": radius,
            "neighbor_ids": [row[2] for row in chosen], "target_excluded": True}


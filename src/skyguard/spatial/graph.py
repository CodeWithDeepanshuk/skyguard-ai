"""Adaptive Spatial Neighbour Graph for India-Wide Automatic Weather Stations.

Implements multi-scale concentric ring neighbour discovery (25 km -> 250 km)
using exact Haversine geodesy. Guarantees leave-one-out isolation for
quality control validation.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from skyguard.stations.registry import MasterStationRegistry, StationMetadata, haversine_km

SEARCH_RADII_KM = [25.0, 50.0, 75.0, 100.0, 150.0, 250.0, 500.0]


class SpatialNeighborGraph:
    """Spatial proximity graph for AWS stations across India."""

    def __init__(self, registry: Optional[MasterStationRegistry] = None):
        self.registry = registry or MasterStationRegistry()
        self._stations: Dict[str, StationMetadata] = self.registry.stations
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def get_neighbors(
        self,
        station_id: str,
        k: int = 5,
        max_radius_km: float = 250.0,
        min_neighbors: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find the closest K valid neighbours for a station using adaptive search radii.

        Always excludes the target station itself (leave-one-out isolation).
        """
        cache_key = f"{station_id}_{k}_{max_radius_km}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        target = self.registry.get_station(station_id)
        if not target:
            return []

        t_lat, t_lon = target.latitude, target.longitude

        # Compute distances to all other stations
        candidates: List[Tuple[float, StationMetadata]] = []
        for sid, s in self._stations.items():
            if s.station_id == target.station_id:
                continue  # Leave-one-out exclusion
            dist = haversine_km(t_lat, t_lon, s.latitude, s.longitude)
            if dist <= max_radius_km:
                candidates.append((dist, s))

        # Sort by distance ascending
        candidates.sort(key=lambda x: x[0])

        # If adaptive radii needed: check if we met min_neighbors within concentric radii
        selected: List[Tuple[float, StationMetadata]] = []
        for r in SEARCH_RADII_KM:
            if r > max_radius_km and len(selected) >= min_neighbors:
                break
            selected = [c for c in candidates if c[0] <= r]
            if len(selected) >= k:
                selected = selected[:k]
                break

        if len(selected) < k and candidates:
            selected = candidates[:k]

        result = [
            {
                "station_id": s.station_id,
                "station_name": s.station_name,
                "distance_km": round(dist, 2),
                "latitude": s.latitude,
                "longitude": s.longitude,
                "elevation_m": s.elevation_m,
                "state": s.state,
                "network_type": s.network_type,
            }
            for dist, s in selected
        ]

        self._cache[cache_key] = result
        return result

    def get_all_neighbors(self, k: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Compute neighbour lists for all stations in registry."""
        return {sid: self.get_neighbors(sid, k=k) for sid in self._stations}

"""Authoritative identifier and geography-based station resolution."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from typing import Any

from skyguard.providers.base import ObservationRecord
from skyguard.stations.registry import haversine_km


ROOT = Path(__file__).resolve().parents[3]


class StationIdentityResolver:
    """Map provider IDs to catalog IDs without ever joining by name alone."""

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        catalog_path = root / "config" / "all_india_aws_network.csv"
        with catalog_path.open("r", encoding="utf-8", newline="") as handle:
            self.catalog = list(csv.DictReader(handle))
        self.by_id = {str(row.get("station_id") or ""): row for row in self.catalog}
        self.by_icao = {
            str(row.get("icao") or "").upper(): row
            for row in self.catalog if str(row.get("icao") or "").strip()
        }
        self.by_wmo_prefix: dict[str, list[dict[str, str]]] = {}
        for row in self.catalog:
            station_id = str(row.get("station_id") or "")
            if len(station_id) >= 5 and station_id[:5].isdigit():
                self.by_wmo_prefix.setdefault(station_id[:5], []).append(row)

    @staticmethod
    def _traditional_id(record: ObservationRecord) -> str:
        source = record.wigos_id or record.provider_station_id
        tail = source.split("-")[-1]
        return tail if tail.isdigit() else ""

    def _nearest(self, candidates: list[dict[str, str]], record: ObservationRecord) -> dict[str, str] | None:
        ranked: list[tuple[float, dict[str, str]]] = []
        for row in candidates:
            try:
                distance = haversine_km(
                    record.latitude, record.longitude,
                    float(row["latitude"]), float(row["longitude"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            ranked.append((distance, row))
        if not ranked:
            return None
        distance, station = min(ranked, key=lambda item: item[0])
        # A WMO-prefix match plus 30 km geographic agreement is sufficiently
        # specific; otherwise preserve the provider's authoritative identity.
        return station if distance <= 30.0 else None

    def resolve(self, record: ObservationRecord) -> ObservationRecord:
        station: dict[str, str] | None = self.by_id.get(record.canonical_station_id)
        if station is None and record.icao_code:
            station = self.by_icao.get(record.icao_code.upper())
        if station is None:
            traditional = self._traditional_id(record)
            if traditional:
                station = self._nearest(self.by_wmo_prefix.get(traditional[:5], []), record)
        if station is None:
            return record
        canonical = str(station.get("station_id") or record.canonical_station_id)
        return replace(
            record,
            station_id=canonical,
            canonical_station_id=canonical,
            station_name=record.station_name or str(station.get("station_name") or canonical),
            icao_code=record.icao_code or str(station.get("icao") or ""),
        )


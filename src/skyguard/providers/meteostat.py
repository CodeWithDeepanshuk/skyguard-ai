"""Meteostat Weather Provider for historical & observed station time-series.

Fetches open physical station observations from Meteostat bulk or open data endpoints.
Tagged strictly as SourceType.OBSERVED with is_direct_observation=True.
Never interpolates unmonitored grid cells.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request

from skyguard.providers.base import (
    ObservationRecord,
    ProviderName,
    RHSource,
    SourceType,
    WeatherProvider,
)

METEOSTAT_BULK_URL = "https://bulk.meteostat.net/v2/hourly"
ROOT = Path(__file__).resolve().parents[3]
CACHE_PATH = ROOT / "data" / "runtime" / "meteostat_provider_cache.json"


class MeteostatWeatherProvider(WeatherProvider):
    """Provider for Meteostat verified station observations."""

    def __init__(
        self,
        bulk_endpoint: str = METEOSTAT_BULK_URL,
        cache_path: Path = CACHE_PATH,
        timeout_seconds: float = 8.0,
    ):
        super().__init__(name=ProviderName.METEOSTAT.value, source_type=SourceType.OBSERVED)
        self.bulk_endpoint = bulk_endpoint
        self.cache_path = cache_path
        self.timeout_seconds = timeout_seconds
        self._station_wmo_map: Dict[str, str] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        # Map common Indian station IDs to 5-digit WMO IDs
        # e.g. New Delhi: 42182, Mumbai: 43057, Kolkata: 42809, Chennai: 43279
        common_wmo = {
            "DELHI_IGI_AIRPORT": "42181",
            "DELHI_SAFDARJUNG": "42182",
            "MUMBAI_SANTACRUZ": "43057",
            "MUMBAI_COLABA": "43058",
            "KOLKATA_ALIPORE": "42809",
            "CHENNAI_MEENAMBAKKAM": "43279",
            "BENGALURU_HAL": "43295",
            "HYDERABAD_BEGUMPET": "43128",
            "AHMEDABAD_AIRPORT": "42647",
            "JAIPUR_SANGANER": "42348",
            "LUCKNOW_AMAUSI": "42369",
            "AMRITSAR_AIRPORT": "42071",
            "VARANASI_BABATPUR": "42475",
            "PATNA_AIRPORT": "42492",
            "BHOPAL_BAIRAGARH": "42667",
            "GWALIOR_AIRPORT": "42435",
        }
        self._station_wmo_map.update(common_wmo)

        # Load from all_india_aws_network if wmo column exists
        net_file = ROOT / "config" / "all_india_aws_network.csv"
        if net_file.exists():
            try:
                with net_file.open("r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        sid = row.get("station_id", "").strip()
                        wmo = row.get("wmo_id", "").strip()
                        if sid and wmo:
                            self._station_wmo_map[sid] = wmo
            except Exception:
                pass

    def _resolve_station_code(self, station_id: str) -> Optional[str]:
        sid = station_id.strip()
        if sid in self._station_wmo_map:
            return self._station_wmo_map[sid]
        # Check if station_id is already a 5-digit WMO ID
        if sid.isdigit() and len(sid) == 5:
            return sid
        # Check if station_id has numeric digits at the end
        parts = sid.split("_")
        for p in parts:
            if p.isdigit() and len(p) == 5:
                return p
        return None

    def fetch_current(self, station_id: str) -> Optional[ObservationRecord]:
        records = self.fetch_history(station_id, hours=3)
        return records[0] if records else None

    def fetch_history(self, station_id: str, hours: int = 24) -> List[ObservationRecord]:
        code = self._resolve_station_code(station_id)
        if not code:
            return []

        url = f"{self.bulk_endpoint}/{code}.csv.gz"
        req = urllib.request.Request(url, headers={"User-Agent": "SkyGuard-AI/2.0"})
        records: List[ObservationRecord] = []

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                compressed_data = resp.read()
                with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as gz:
                    lines = gz.read().decode("utf-8").strip().split("\n")
                    # Meteostat hourly columns format:
                    # date, hour, temp, dwpt, rhum, prcp, snow, wdir, wspd, wpgt, pres, tsun, coco
                    for line in lines[-hours:]:
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 11:
                            dt_str = f"{parts[0]}T{int(parts[1]):02d}:00:00Z"
                            temp_c = float(parts[2]) if parts[2] else None
                            rh_pct = float(parts[4]) if parts[4] else None
                            pres_hpa = float(parts[10]) if parts[10] else None

                            records.append(ObservationRecord(
                                provider=self.name,
                                source_type=self.source_type.value,
                                station_id=station_id,
                                timestamp_utc=dt_str,
                                latitude=0.0,
                                longitude=0.0,
                                temperature_c=temp_c,
                                relative_humidity_pct=rh_pct,
                                pressure_hpa=pres_hpa,
                                is_direct_observation=True,
                                is_interpolated=False,
                                is_model_field=False,
                                rh_source=RHSource.OBSERVED.value if rh_pct is not None else RHSource.UNAVAILABLE.value,
                            ))
        except Exception:
            return []

        records.sort(key=lambda r: r.timestamp_utc, reverse=True)
        return records

    def station_metadata(self) -> List[Dict[str, Any]]:
        return [
            {"station_id": sid, "wmo_id": wmo, "provider": self.name, "source_type": self.source_type.value}
            for sid, wmo in self._station_wmo_map.items()
        ]

    def healthcheck(self) -> Dict[str, Any]:
        t0 = time.time()
        try:
            # Check headers of bulk index or a known station
            test_url = f"{self.bulk_endpoint}/42182.csv.gz"
            req = urllib.request.Request(test_url, headers={"User-Agent": "SkyGuard-AI/2.0"}, method="HEAD")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                status_code = resp.getcode()
                latency_ms = round((time.time() - t0) * 1000, 1)
                return {
                    "provider": self.name,
                    "status": "healthy" if status_code == 200 else "degraded",
                    "latency_ms": latency_ms,
                    "endpoint": self.bulk_endpoint,
                }
        except Exception as exc:
            return {
                "provider": self.name,
                "status": "unreachable",
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "error": str(exc),
            }

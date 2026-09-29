"""Weather Provider Manager and Hierarchical Orchestrator.

Manages data ingestion across:
1. IMD WIS 2.0 (Official WMO wis2box.imd.gov.in node)
2. METAR (AviationWeather.gov official aerodrome observations)
3. Meteostat (Verified open station observations)
4. Open-Meteo (Independent Numerical Reference Weather Model)

Enforces strict provenance tagging and independent validation baselines.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from skyguard.providers.base import (
    ObservationRecord,
    ProviderName,
    SourceType,
    WeatherProvider,
)
from skyguard.providers.imd_wis2 import IMDWIS2Provider
from skyguard.providers.imd_api import IMDAWSAPIProvider
from skyguard.providers.imd_fixture import IMDFixtureProvider
from skyguard.providers.metar import MetarWeatherProvider
from skyguard.providers.meteostat import MeteostatWeatherProvider
from skyguard.providers.reference_weather import ReferenceWeatherProvider

ROOT = Path(__file__).resolve().parents[3]


class WeatherProviderManager:
    """Orchestrates hierarchical weather observations and reference fields."""

    def __init__(self, root: Path = ROOT):
        self.root = root
        self.wis2 = IMDWIS2Provider()
        self.imd_api = IMDAWSAPIProvider()
        self.imd_fixture = IMDFixtureProvider(root=root)
        self.metar = MetarWeatherProvider()
        self.meteostat = MeteostatWeatherProvider()
        self.reference = ReferenceWeatherProvider()

        self._providers: Dict[str, WeatherProvider] = {
            ProviderName.IMD_AWS.value: self.imd_api,
            "IMD_FIXTURE_REPLAY": self.imd_fixture,
            ProviderName.IMD_WIS2.value: self.wis2,
            ProviderName.METAR.value: self.metar,
            ProviderName.METEOSTAT.value: self.meteostat,
            ProviderName.OPEN_METEO_REFERENCE.value: self.reference,
        }

        self.stations: Dict[str, Dict[str, Any]] = {}
        self._load_master_stations()

    def _load_master_stations(self) -> None:
        # Load known stations and register coordinates with reference provider
        for fname in ["imd_aws_master.csv", "all_india_aws_network.csv", "stations.csv"]:
            p = self.root / "config" / fname
            if not p.exists():
                p = self.root / "data" / "stations" / fname
            if p.exists():
                try:
                    with p.open("r", encoding="utf-8", newline="") as f:
                        for row in csv.DictReader(f):
                            sid = row.get("station_id", "").strip()
                            if sid and sid not in self.stations:
                                self.stations[sid] = row
                                lat = float(row.get("latitude", 0))
                                lon = float(row.get("longitude", 0))
                                if lat and lon:
                                    self.reference.register_station_coordinates(sid, lat, lon)
                except Exception:
                    pass

    def get_station_coords(self, station_id: str) -> Tuple[Optional[float], Optional[float]]:
        meta = self.stations.get(station_id)
        if meta and meta.get("latitude") and meta.get("longitude"):
            try:
                return float(meta["latitude"]), float(meta["longitude"])
            except (ValueError, TypeError):
                pass
        return None, None

    def fetch_observation(self, station_id: str) -> Optional[ObservationRecord]:
        """Fetch the highest-priority genuine direct physical observation."""
        # 0. Check live ingested observations snapshot
        live_p = self.root / "data" / "live" / "latest.json"
        if live_p.exists():
            try:
                import json
                data = json.loads(live_p.read_text(encoding="utf-8"))
                readings = data.get("readings") or data.get("latest") or []
                for r in readings:
                    sid = r.get("station_id") or r.get("canonical_station_id")
                    if sid == station_id and (r.get("temperature_c") is not None or r.get("temperature") is not None):
                        t = r.get("temperature_c") if r.get("temperature_c") is not None else r.get("temperature")
                        p = r.get("pressure_hpa") if r.get("pressure_hpa") is not None else r.get("pressure")
                        rh = r.get("relative_humidity_pct") if r.get("relative_humidity_pct") is not None else r.get("humidity")
                        lat, lon = self.get_station_coords(station_id)
                        return ObservationRecord(
                            provider=r.get("provider", "IMD_AWS"),
                            source_type=SourceType.OBSERVED.value,
                            station_id=station_id,
                            canonical_station_id=station_id,
                            timestamp_utc=r.get("timestamp_utc") or r.get("observation_timestamp_utc") or "",
                            latitude=lat or r.get("latitude"),
                            longitude=lon or r.get("longitude"),
                            elevation_m=r.get("elevation_m"),
                            temperature_c=float(t) if t is not None else None,
                            pressure_hpa=float(p) if p is not None else None,
                            relative_humidity_pct=float(rh) if rh is not None else None,
                            is_direct_observation=True,
                        )
            except Exception:
                pass

        # 1. Check the credentialed IMD AWS/ARG API.
        rec = self.imd_api.fetch_current(station_id)
        if rec and rec.temperature_c is not None:
            return rec

        # 2. Check IMD WIS 2.0.
        rec = self.wis2.fetch_current(station_id)
        if rec and rec.temperature_c is not None:
            return rec

        # 3. Check METAR
        rec = self.metar.fetch_current(station_id)
        if rec and rec.temperature_c is not None:
            return rec

        # 4. Check Meteostat
        rec = self.meteostat.fetch_current(station_id)
        if rec and rec.temperature_c is not None:
            return rec

        return None

    def fetch_reference(self, station_id: str) -> Optional[ObservationRecord]:
        """Fetch the independent numerical reference model field."""
        lat, lon = self.get_station_coords(station_id)
        return self.reference.fetch_current(station_id, lat=lat, lon=lon)

    def fetch_history_triplet(
        self,
        station_id: str,
        hours: int = 24,
    ) -> Dict[str, List[ObservationRecord]]:
        """Fetch synchronous history traces: observed and independent reference model."""
        lat, lon = self.get_station_coords(station_id)

        # 0. Check durable ObservationStore for genuine live telemetry history
        observed_list: List[ObservationRecord] = []
        try:
            from skyguard.storage.observations import ObservationStore
            store = ObservationStore(root=self.root)
            hist = store.paginated_history(station_id, hours=hours, limit=1000, relative_to_latest=True)
            items = hist.get("items") or []
            if items:
                observed_list = [
                    ObservationRecord(
                        provider=h.get("provider", "IMD_AWS"),
                        source_type=SourceType.OBSERVED.value,
                        station_id=station_id,
                        canonical_station_id=station_id,
                        timestamp_utc=h.get("observation_timestamp_utc") or h.get("timestamp_utc") or "",
                        latitude=lat,
                        longitude=lon,
                        elevation_m=h.get("elevation_m"),
                        temperature_c=float(h["temperature_c"]) if h.get("temperature_c") is not None else None,
                        pressure_hpa=float(h["pressure_hpa"]) if h.get("pressure_hpa") is not None else None,
                        relative_humidity_pct=float(h["relative_humidity_pct"]) if h.get("relative_humidity_pct") is not None else None,
                        is_direct_observation=True,
                    )
                    for h in items
                    if h.get("temperature_c") is not None or h.get("pressure_hpa") is not None or h.get("relative_humidity_pct") is not None
                ]
        except Exception:
            pass

        # If empty, try WIS2
        if not observed_list:
            observed_list = self.wis2.fetch_history(station_id, hours=hours)
        # If empty, try METAR
        if not observed_list:
            observed_list = self.metar.fetch_history(station_id, hours=hours)
        # If empty, try Meteostat
        if not observed_list:
            observed_list = self.meteostat.fetch_history(station_id, hours=hours)

        # 2. Reference Model history
        ref_list = self.reference.fetch_history(station_id, lat=lat, lon=lon, hours=hours)

        return {
            "observed": observed_list,
            "reference_model": ref_list,
        }

    def providers_health(self) -> Dict[str, Any]:
        return {name: p.healthcheck() for name, p in self._providers.items()}

"""Open-Meteo Independent Reference Weather Provider.

Provides gridded numerical weather prediction and global reanalysis/forecast fields.
IMPORTANT SCIENTIFIC GOVERNANCE:
Tagged strictly as SourceType.REFERENCE_MODEL.
`is_direct_observation = False`
`is_model_field = True`
`is_interpolated = True`
Never presented as physical in-situ IMD AWS hardware sensor telemetry.
"""
from __future__ import annotations

import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request

from skyguard.providers.base import (
    ObservationRecord,
    PressureType,
    ProviderName,
    RHSource,
    SourceType,
    WeatherProvider,
)

OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = ROOT / "data" / "reference_weather"
CACHE_TTL_SECONDS = 3600  # 1 hour


class ReferenceWeatherProvider(WeatherProvider):
    """Independent reference NWP model provider using Open-Meteo."""

    def __init__(
        self,
        endpoint: str = OPEN_METEO_ENDPOINT,
        cache_dir: Path = CACHE_DIR,
        timeout_seconds: float = 10.0,
    ):
        super().__init__(name=ProviderName.OPEN_METEO_REFERENCE.value, source_type=SourceType.REFERENCE_MODEL)
        self.endpoint = endpoint
        self.cache_dir = cache_dir
        self.timeout_seconds = timeout_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._station_coords: Dict[str, tuple[float, float]] = {}

    def register_station_coordinates(self, station_id: str, lat: float, lon: float) -> None:
        self._station_coords[station_id] = (lat, lon)

    def fetch_current(self, station_id: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[ObservationRecord]:
        history = self.fetch_history(station_id, lat=lat, lon=lon, hours=3)
        return history[0] if history else None

    def fetch_history(
        self,
        station_id: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        hours: int = 24,
    ) -> List[ObservationRecord]:
        if lat is None or lon is None:
            if station_id in self._station_coords:
                lat, lon = self._station_coords[station_id]
            else:
                return []

        # Check local cache
        cache_file = self.cache_dir / f"{station_id.replace('/', '_')}.json"
        now = time.time()
        raw_data = None

        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                if (now - cached.get("cached_at", 0)) < CACHE_TTL_SECONDS:
                    raw_data = cached.get("data")
            except Exception:
                raw_data = None

        if not raw_data:
            # Fetch from Open-Meteo with past_hours
            url = (
                f"{self.endpoint}?latitude={round(lat, 4)}&longitude={round(lon, 4)}"
                f"&hourly=temperature_2m,relative_humidity_2m,surface_pressure"
                f"&past_hours={min(hours, 48)}&forecast_hours=1"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "SkyGuard-AI/2.0"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    raw_data = json.loads(resp.read().decode("utf-8"))
                    # Save to cache
                    cache_file.write_text(
                        json.dumps({"cached_at": now, "data": raw_data}),
                        encoding="utf-8",
                    )
            except Exception:
                # If network fails, try stale cache if it exists
                if cache_file.exists():
                    try:
                        cached = json.loads(cache_file.read_text(encoding="utf-8"))
                        raw_data = cached.get("data")
                    except Exception:
                        raw_data = None

        if not raw_data or "hourly" not in raw_data:
            return []

        hourly = raw_data["hourly"]
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        rhs = hourly.get("relative_humidity_2m", [])
        pressures = hourly.get("surface_pressure", [])

        records: List[ObservationRecord] = []
        for i in range(len(times)):
            iso_time = times[i]
            if not iso_time.endswith("Z") and "+" not in iso_time:
                iso_time += "Z"

            t_val = float(temps[i]) if i < len(temps) and temps[i] is not None else None
            rh_val = float(rhs[i]) if i < len(rhs) and rhs[i] is not None else None
            p_val = float(pressures[i]) if i < len(pressures) and pressures[i] is not None else None

            rec = ObservationRecord(
                provider=self.name,
                source_type=self.source_type.value,
                station_id=station_id,
                timestamp_utc=iso_time,
                latitude=lat,
                longitude=lon,
                temperature_c=t_val,
                relative_humidity_pct=rh_val,
                pressure_hpa=p_val,
                is_direct_observation=False,
                is_interpolated=True,
                is_model_field=True,
                rh_source=RHSource.DERIVED.value if rh_val is not None else RHSource.UNAVAILABLE.value,
                provider_station_id=station_id,
                canonical_station_id=station_id,
                pressure_type=PressureType.STATION_PRESSURE.value,
                source_quality_flags=("MODEL_FIELD_REFERENCE_ONLY",),
                source_url=self.endpoint,
                message_id=f"open-meteo|{station_id}|{iso_time}",
                raw_source_hash=hashlib.sha256(
                    json.dumps(
                        {"time": iso_time, "temperature_2m": t_val, "relative_humidity_2m": rh_val, "surface_pressure": p_val},
                        sort_keys=True,
                    ).encode("utf-8")
                ).hexdigest(),
            )
            records.append(rec)

        records.sort(key=lambda r: r.timestamp_utc, reverse=True)
        return records[:hours]

    def station_metadata(self) -> List[Dict[str, Any]]:
        return [
            {
                "station_id": sid,
                "latitude": coords[0],
                "longitude": coords[1],
                "provider": self.name,
                "source_type": self.source_type.value,
            }
            for sid, coords in self._station_coords.items()
        ]

    def healthcheck(self) -> Dict[str, Any]:
        t0 = time.time()
        try:
            url = f"{self.endpoint}?latitude=28.58&longitude=77.20&current=temperature_2m"
            req = urllib.request.Request(url, headers={"User-Agent": "SkyGuard-AI/2.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latency_ms = round((time.time() - t0) * 1000, 1)
                return {
                    "provider": self.name,
                    "status": "healthy" if "current" in data else "degraded",
                    "latency_ms": latency_ms,
                    "endpoint": self.endpoint,
                }
        except Exception as exc:
            return {
                "provider": self.name,
                "status": "unreachable",
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "error": str(exc),
            }

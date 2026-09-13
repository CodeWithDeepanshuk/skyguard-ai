"""METAR Weather Provider wrapping AviationWeather.gov.

Fetches genuine direct aerodrome routine meteorological reports across Indian airports.
Strictly tagged as SourceType.OBSERVED with is_direct_observation=True.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
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

METAR_ENDPOINT = "https://aviationweather.gov/api/data/metar"
ROOT = Path(__file__).resolve().parents[3]
CACHE_PATH = ROOT / "data" / "runtime" / "metar_provider_cache.json"
CACHE_TTL = 900  # 15 minutes


def calc_relative_humidity(temp_c: Optional[float], dewp_c: Optional[float]) -> Optional[float]:
    if temp_c is None or dewp_c is None:
        return None
    try:
        a, b = 17.625, 243.04
        alpha_t = (a * temp_c) / (b + temp_c)
        alpha_d = (a * dewp_c) / (b + dewp_c)
        rh = 100.0 * math.exp(alpha_d - alpha_t)
        return round(max(0.0, min(100.0, rh)), 1)
    except Exception:
        return None


class MetarWeatherProvider(WeatherProvider):
    """Provider for official METAR airport surface observations."""

    def __init__(
        self,
        endpoint: str = METAR_ENDPOINT,
        cache_path: Path = CACHE_PATH,
        timeout_seconds: float = 10.0,
    ):
        super().__init__(name=ProviderName.METAR.value, source_type=SourceType.OBSERVED)
        self.endpoint = endpoint
        self.cache_path = cache_path
        self.timeout_seconds = timeout_seconds
        self._station_lookup: Dict[str, Dict[str, Any]] = {}
        self._icao_lookup: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        for fname in ["all_india_aws_network.csv", "stations.csv"]:
            p = ROOT / "config" / fname
            if p.exists():
                try:
                    with p.open("r", encoding="utf-8", newline="") as f:
                        for row in csv.DictReader(f):
                            sid = row.get("station_id", "").strip()
                            icao = row.get("icao", "").strip().upper()
                            if sid:
                                self._station_lookup[sid] = row
                            if icao:
                                self._icao_lookup[icao] = row
                                self._icao_lookup[sid] = row
                except Exception:
                    pass

    def _resolve_icao(self, station_id: str) -> Optional[str]:
        sid = station_id.strip()
        if len(sid) == 4 and sid.startswith("V"):
            return sid.upper()
        if sid in self._icao_lookup and self._icao_lookup[sid].get("icao"):
            return self._icao_lookup[sid]["icao"].upper()
        if sid.upper() in self._icao_lookup:
            return self._icao_lookup[sid.upper()].get("icao", "").upper() or None
        return None

    def fetch_current(self, station_id: str) -> Optional[ObservationRecord]:
        icao = self._resolve_icao(station_id)
        if not icao:
            return None

        records = self.fetch_history(station_id, hours=3)
        return records[0] if records else None

    def fetch_history(self, station_id: str, hours: int = 24) -> List[ObservationRecord]:
        icao = self._resolve_icao(station_id)
        if not icao:
            return []

        url = f"{self.endpoint}?ids={icao}&format=json&hours={min(hours, 72)}"
        raw_data: Any = None
        try:
            raw_data = self._fetch_json(url)
        except Exception:
            # Fallback to local cache if present
            if self.cache_path.exists():
                try:
                    cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
                    raw_data = cache.get(icao)
                except Exception:
                    raw_data = None

        if not raw_data or not isinstance(raw_data, list):
            return []
        return self._normalize(raw_data, requested_station_id=station_id)

    def fetch_network_history(self, hours: int = 24) -> List[ObservationRecord]:
        """Fetch all configured Indian aerodromes in one bounded bulk request."""
        identifiers = sorted({key for key in self._icao_lookup if len(key) == 4 and key.startswith("V")})
        if not identifiers:
            return []
        url = f"{self.endpoint}?ids={','.join(identifiers)}&format=json&hours={min(hours, 72)}"
        try:
            payload = self._fetch_json(url)
        except Exception:
            return []
        return self._normalize(payload if isinstance(payload, list) else [])

    def _fetch_json(self, url: str) -> Any:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SkyGuard-AI/2.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _normalize(
        self,
        raw_data: List[Dict[str, Any]],
        *,
        requested_station_id: Optional[str] = None,
    ) -> List[ObservationRecord]:
        records: List[ObservationRecord] = []
        requested_icao = self._resolve_icao(requested_station_id) if requested_station_id else None

        for item in raw_data:
            if not isinstance(item, dict):
                continue
            icao = str(item.get("icaoId") or requested_icao or "").strip().upper()
            if not icao or icao not in self._icao_lookup:
                continue
            meta = (
                self._station_lookup.get(requested_station_id or "")
                or self._icao_lookup.get(icao)
                or {}
            )
            canonical_station_id = str(meta.get("station_id") or requested_station_id or icao)
            lat = float(meta.get("latitude", 0.0)) if meta.get("latitude") else 0.0
            lon = float(meta.get("longitude", 0.0)) if meta.get("longitude") else 0.0
            elev = float(meta.get("elevation_m", 0.0)) if meta.get("elevation_m") else None
            rep_time = item.get("reportTime") or ""
            if not rep_time and item.get("obsTime"):
                try:
                    rep_time = datetime.fromtimestamp(
                        float(item["obsTime"]), timezone.utc
                    ).isoformat().replace("+00:00", "Z")
                except Exception:
                    continue

            if not rep_time:
                continue

            item_lat = float(item.get("lat", lat or 0.0))
            item_lon = float(item.get("lon", lon or 0.0))
            item_elev = float(item.get("elev", elev or 0.0)) if item.get("elev") is not None else elev

            temp = item.get("temp")
            dewp = item.get("dewp")
            altim = item.get("altim")  # In hPa / mb

            t_val = float(temp) if temp is not None else None
            td_val = float(dewp) if dewp is not None else None
            p_val = float(altim) if altim is not None else None
            rh_val = calc_relative_humidity(t_val, td_val)
            raw_payload_json = json.dumps(item, sort_keys=True, separators=(",", ":"))
            raw_hash = hashlib.sha256(raw_payload_json.encode("utf-8")).hexdigest()
            source_flags = tuple(
                [str(item.get("qcField"))] if item.get("qcField") not in (None, "") else []
            )

            rec = ObservationRecord(
                provider=self.name,
                source_type=self.source_type.value,
                station_id=canonical_station_id,
                timestamp_utc=str(rep_time),
                latitude=item_lat,
                longitude=item_lon,
                elevation_m=item_elev,
                temperature_c=t_val,
                relative_humidity_pct=rh_val,
                pressure_hpa=p_val,
                is_direct_observation=True,
                is_interpolated=False,
                is_model_field=False,
                rh_source=RHSource.DERIVED.value if rh_val is not None else RHSource.UNAVAILABLE.value,
                raw_source_hash=raw_hash,
                provider_station_id=icao,
                canonical_station_id=canonical_station_id,
                icao_code=icao,
                station_name=str(meta.get("station_name") or meta.get("name") or canonical_station_id),
                provider_publication_timestamp_utc=str(item.get("receiptTime") or ""),
                pressure_type=PressureType.ALTIMETER_QNH.value,
                source_quality_flags=source_flags,
                source_url=self.endpoint,
                message_id=str(item.get("rawOb") or f"{icao}|{rep_time}"),
                raw_payload_json=raw_payload_json,
            )
            records.append(rec)

        # Sort by timestamp descending
        records.sort(key=lambda r: r.timestamp_utc, reverse=True)
        return records

    def station_metadata(self) -> List[Dict[str, Any]]:
        results = []
        for sid, meta in self._station_lookup.items():
            if meta.get("icao"):
                results.append({
                    "station_id": sid,
                    "name": meta.get("name", sid),
                    "icao": meta.get("icao"),
                    "latitude": float(meta.get("latitude", 0)),
                    "longitude": float(meta.get("longitude", 0)),
                    "elevation_m": float(meta.get("elevation_m", 0)),
                    "provider": self.name,
                    "source_type": self.source_type.value,
                })
        return results

    def healthcheck(self) -> Dict[str, Any]:
        t0 = time.time()
        try:
            url = f"{self.endpoint}?ids=VIDP&format=json&hours=1"
            req = urllib.request.Request(url, headers={"User-Agent": "SkyGuard-AI/2.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latency_ms = round((time.time() - t0) * 1000, 1)
                return {
                    "provider": self.name,
                    "status": "healthy" if isinstance(data, list) else "degraded",
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

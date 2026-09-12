"""Official IMD WIS 2.0 (wis2box) Adapter for SYNOP surface observations.

Connects to the official public IMD WIS 2.0 endpoint at https://wis2box.imd.gov.in/oapi.
Exposes WIGOS station metadata. Observation decoding remains disabled until a
canonical WIS2 notification/data payload is retrieved and validated.
"""
from __future__ import annotations

import json
import logging
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from skyguard.providers.base import (
    ObservationRecord,
    ProviderName,
    RHSource,
    SourceType,
    WeatherProvider,
)

logger = logging.getLogger(__name__)

WIS2_BASE_URL = "https://wis2box.imd.gov.in/oapi"
SYNOP_COLLECTION = "urn:wmo:md:in-imd:surface-based-observations.synop"


def kelvin_to_celsius(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    # If reported in Kelvin (> 100), convert to Celsius
    if value > 100:
        return round(value - 273.15, 2)
    return round(value, 2)


def calculate_rh_from_dewpoint(temp_c: float, dew_c: float) -> float:
    """Magnus formula approximation for Relative Humidity from T and Td."""
    a = 17.625
    b = 243.04
    alpha = (a * temp_c) / (b + temp_c)
    beta = (a * dew_c) / (b + dew_c)
    rh = 100.0 * math.exp(beta - alpha)
    return max(1.0, min(100.0, round(rh, 1)))


class IMDWIS2Provider(WeatherProvider):
    """Adapter for official IMD WIS 2.0 public wis2box node."""

    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 12):
        super().__init__(
            name=ProviderName.IMD_WIS2.value,
            source_type=SourceType.OBSERVED,
        )
        self.timeout = timeout
        self.cache_dir = cache_dir or Path("data/raw/wis2")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cached_stations: List[Dict[str, Any]] = []

    def healthcheck(self) -> Dict[str, Any]:
        """Check wis2box availability."""
        url = f"{WIS2_BASE_URL}/collections"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SkyGuard-AI-SIH26073-Academic/1.0", "Accept": "application/json"}
            )
            start = datetime.now(timezone.utc)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                body = resp.read()
            latency_ms = round((datetime.now(timezone.utc) - start).total_seconds() * 1000, 1)
            data = json.loads(body)
            collections = [c.get("id") for c in data.get("collections", [])]
            return {
                "status": "healthy" if status == 200 else "degraded",
                "http_status": status,
                "latency_ms": latency_ms,
                "collections": collections,
                "endpoint": WIS2_BASE_URL,
            }
        except Exception as exc:
            return {
                "status": "offline",
                "error": str(exc),
                "endpoint": WIS2_BASE_URL,
            }

    def station_metadata(self) -> List[Dict[str, Any]]:
        """Fetch official station metadata; count is whatever the endpoint returns."""
        cache_file = self.cache_dir / "stations_metadata.json"
        url = f"{WIS2_BASE_URL}/collections/stations/items?limit=500"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SkyGuard-AI-SIH26073-Academic/1.0", "Accept": "application/geo+json,application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            stations = []
            for feat in data.get("features", []):
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                coords = geom.get("coordinates", [0, 0])
                wigos_id = props.get("wigos_station_identifier") or feat.get("id")
                trad_id = props.get("traditional_station_identifier")
                name = props.get("name", "").strip().title()

                stations.append({
                    "wigos_id": wigos_id,
                    "traditional_id": trad_id,
                    "station_name": name,
                    "latitude": float(coords[1]) if len(coords) > 1 else None,
                    "longitude": float(coords[0]) if len(coords) > 0 else None,
                    "elevation_m": props.get("barometer_height"),
                    "territory": props.get("territory_name", "IND"),
                    "status": props.get("status", "operational"),
                    "oscar_url": props.get("url"),
                    "metadata_source": "IMD_WIS2_BOX",
                })

            if stations:
                self._cached_stations = stations
                cache_file.write_text(json.dumps(stations, indent=2), encoding="utf-8")
            return self._cached_stations
        except Exception as exc:
            logger.warning("Could not retrieve online WIS2 stations (%s)", exc)
            if cache_file.exists():
                try:
                    cached = json.loads(cache_file.read_text(encoding="utf-8"))
                    return cached if isinstance(cached, list) else []
                except Exception:
                    pass
            return []

    def fetch_current(self, station_id: str) -> Optional[ObservationRecord]:
        """Fetch latest SYNOP observation for an IMD WIGOS or traditional station ID."""
        records = self.fetch_history(station_id, hours=6)
        return records[0] if records else None

    def fetch_history(self, station_id: str, hours: int = 24) -> List[ObservationRecord]:
        """No rows until MQTT/canonical WIS2 payload decoding is validated.

        The discovery collection is metadata, not a queryable observation-feature
        collection. Returning zero is scientifically safer than inventing a schema.
        """
        return []

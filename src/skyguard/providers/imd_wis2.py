"""Official IMD WIS 2.0 (wis2box) Adapter for SYNOP surface observations.

Connects to the official public IMD WIS 2.0 endpoint at https://wis2box.imd.gov.in/oapi.
Exposes WIGOS station metadata. Observation decoding remains disabled until a
canonical WIS2 notification/data payload is retrieved and validated.
"""
from __future__ import annotations

import json
import hashlib
import logging
import math
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
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
        """Fetch decoded OGC SYNOP parameters and group them into reports.

        The collection contains one feature per parameter, so values are grouped by
        reportId. Only actual features returned by IMD become OBSERVED records.
        """
        stations = self.station_metadata()
        target = next((s for s in stations if station_id in {
            str(s.get("wigos_id") or ""), str(s.get("traditional_id") or "")
        }), None)
        wigos_id = str(target.get("wigos_id")) if target else station_id
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=max(1, min(hours, 72)))
        params = {
            "f": "json", "limit": 1000, "wigos_station_identifier": wigos_id,
            "datetime": f"{start.isoformat().replace('+00:00', 'Z')}/{end.isoformat().replace('+00:00', 'Z')}",
        }
        collection = urllib.parse.quote(SYNOP_COLLECTION, safe=":")
        url = f"{WIS2_BASE_URL}/collections/{collection}/items?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "SkyGuard-AI-SIH26073-Academic/1.0", "Accept": "application/geo+json,application/json"
            })
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("WIS2 observation query failed for %s: %s", wigos_id, exc)
            return []

        reports: Dict[str, Dict[str, Any]] = {}
        for feature in payload.get("features", []):
            props = feature.get("properties") or {}
            if str(props.get("wigos_station_identifier") or "") != wigos_id:
                continue
            report_id = str(props.get("reportId") or props.get("reportTime") or "")
            report_time = str(props.get("reportTime") or props.get("phenomenonTime") or "")
            name = str(props.get("name") or "")
            if not report_id or not report_time or not name:
                continue
            bucket = reports.setdefault(report_id, {"timestamp": report_time, "values": {}, "features": []})
            bucket["values"][name] = props.get("value")
            bucket["features"].append(feature)

        records: List[ObservationRecord] = []
        for report in reports.values():
            values = report["values"]
            temp_c = kelvin_to_celsius(_number(values.get("air_temperature")))
            dew_c = kelvin_to_celsius(_number(values.get("dewpoint_temperature")))
            pressure = _number(values.get("pressure_reduced_to_mean_sea_level"))
            if pressure is None:
                pressure = _number(values.get("non_coordinate_pressure"))
            rh = _number(values.get("relative_humidity"))
            rh_source = RHSource.OBSERVED.value if rh is not None else RHSource.UNAVAILABLE.value
            if rh is None and temp_c is not None and dew_c is not None:
                rh = calculate_rh_from_dewpoint(temp_c, dew_c)
                rh_source = RHSource.DERIVED.value
            if temp_c is None and pressure is None and rh is None:
                continue
            coords = ((report["features"][0].get("geometry") or {}).get("coordinates") or [])
            lat = float(coords[1]) if len(coords) > 1 else float((target or {}).get("latitude") or 0)
            lon = float(coords[0]) if coords else float((target or {}).get("longitude") or 0)
            raw = json.dumps(report["features"], sort_keys=True, separators=(",", ":")).encode("utf-8")
            records.append(ObservationRecord(
                provider=self.name, source_type=SourceType.OBSERVED.value, station_id=wigos_id,
                timestamp_utc=report["timestamp"], latitude=lat, longitude=lon,
                elevation_m=(target or {}).get("elevation_m"), temperature_c=temp_c,
                relative_humidity_pct=rh, pressure_hpa=round(pressure, 2) if pressure is not None else None,
                is_direct_observation=True, is_interpolated=False, is_model_field=False,
                rh_source=rh_source, raw_source_hash=hashlib.sha256(raw).hexdigest(),
            ))
        records.sort(key=lambda item: item.timestamp_utc, reverse=True)
        return records

    def fetch_network_history(self, hours: int = 24, max_pages: int = 50) -> tuple[List[ObservationRecord], Dict[str, Any]]:
        """Download a bounded national time window by following OGC `next` links."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=max(1, min(hours, 72)))
        collection = urllib.parse.quote(SYNOP_COLLECTION, safe=":")
        params = {"f": "json", "limit": 1000,
                  "datetime": f"{start.isoformat().replace('+00:00', 'Z')}/{end.isoformat().replace('+00:00', 'Z')}"}
        url: Optional[str] = f"{WIS2_BASE_URL}/collections/{collection}/items?{urllib.parse.urlencode(params)}"
        features: List[Dict[str, Any]] = []
        pages = 0
        number_matched: Optional[int] = None
        seen_urls = set()
        while url and pages < max_pages and url not in seen_urls:
            seen_urls.add(url)
            req = urllib.request.Request(url, headers={
                "User-Agent": "SkyGuard-AI-SIH26073-Academic/1.0", "Accept": "application/geo+json,application/json"
            })
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                return _decode_features(features, self.station_metadata()), {
                    "complete": False, "pages": pages, "features_downloaded": len(features),
                    "number_matched": number_matched, "error": str(exc), "window_start_utc": start.isoformat(),
                    "window_end_utc": end.isoformat(),
                }
            pages += 1
            if number_matched is None:
                number_matched = payload.get("numberMatched")
            features.extend(payload.get("features", []))
            url = next((link.get("href") for link in payload.get("links", []) if link.get("rel") == "next"), None)
        complete = not url
        records = _decode_features(features, self.station_metadata())
        return records, {
            "complete": complete, "pages": pages, "features_downloaded": len(features),
            "number_matched": number_matched, "decoded_reports": len(records),
            "reporting_stations": len({row.station_id for row in records}),
            "window_start_utc": start.isoformat(), "window_end_utc": end.isoformat(),
            "max_pages": max_pages,
        }


def _number(value: Any) -> Optional[float]:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _decode_features(features: List[Dict[str, Any]], stations: List[Dict[str, Any]]) -> List[ObservationRecord]:
    metadata = {str(row.get("wigos_id")): row for row in stations if row.get("wigos_id")}
    reports: Dict[tuple[str, str], Dict[str, Any]] = {}
    for feature in features:
        props = feature.get("properties") or {}
        station_id = str(props.get("wigos_station_identifier") or "")
        report_id = str(props.get("reportId") or props.get("reportTime") or "")
        timestamp = str(props.get("reportTime") or props.get("phenomenonTime") or "")
        name = str(props.get("name") or "")
        if not station_id or not report_id or not timestamp or not name:
            continue
        bucket = reports.setdefault((station_id, report_id), {"timestamp": timestamp, "values": {}, "features": []})
        bucket["values"][name] = props.get("value")
        bucket["features"].append(feature)
    output: List[ObservationRecord] = []
    for (station_id, _), report in reports.items():
        values = report["values"]
        temperature = kelvin_to_celsius(_number(values.get("air_temperature")))
        dewpoint = kelvin_to_celsius(_number(values.get("dewpoint_temperature")))
        pressure = _number(values.get("pressure_reduced_to_mean_sea_level"))
        if pressure is None:
            pressure = _number(values.get("non_coordinate_pressure"))
        humidity = _number(values.get("relative_humidity"))
        humidity_source = RHSource.OBSERVED.value if humidity is not None else RHSource.UNAVAILABLE.value
        if humidity is None and temperature is not None and dewpoint is not None:
            humidity = calculate_rh_from_dewpoint(temperature, dewpoint)
            humidity_source = RHSource.DERIVED.value
        if temperature is None and pressure is None and humidity is None:
            continue
        coordinates = ((report["features"][0].get("geometry") or {}).get("coordinates") or [])
        station = metadata.get(station_id, {})
        latitude = float(coordinates[1]) if len(coordinates) > 1 else float(station.get("latitude") or 0)
        longitude = float(coordinates[0]) if coordinates else float(station.get("longitude") or 0)
        raw = json.dumps(report["features"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        output.append(ObservationRecord(
            provider=ProviderName.IMD_WIS2.value, source_type=SourceType.OBSERVED.value,
            station_id=station_id, timestamp_utc=report["timestamp"], latitude=latitude, longitude=longitude,
            elevation_m=station.get("elevation_m"), temperature_c=temperature,
            relative_humidity_pct=humidity, pressure_hpa=round(pressure, 2) if pressure is not None else None,
            is_direct_observation=True, is_interpolated=False, is_model_field=False,
            rh_source=humidity_source, raw_source_hash=hashlib.sha256(raw).hexdigest(),
        ))
    output.sort(key=lambda item: (item.timestamp_utc, item.station_id), reverse=True)
    return output

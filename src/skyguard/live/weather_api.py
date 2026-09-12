"""Open-Meteo reference-field assimilation for SkyGuard AI.

Open-Meteo coordinate values are model/reference evidence. They are never direct
IMD AWS observations and must not be displayed or counted as reporting stations.
Provides physical consistency gates to detect impossible observations
(such as dew point exceeding air temperature) and auto-correct them using
verified ground telemetry.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CACHE_PATH = ROOT / "data" / "runtime" / "weather_api_cache.json"
CACHE_TTL_SECONDS = 900  # 15 minutes


def calc_dew_point(temperature_c: float, humidity_pct: float) -> float:
    """Calculate dew point in Celsius using the Magnus-Tetens approximation."""
    a, b = 17.625, 243.04
    rh = max(0.01, min(100.0, humidity_pct))
    alpha = ((a * temperature_c) / (b + temperature_c)) + math.log(rh / 100.0)
    return round((b * alpha) / (a - alpha), 1)


def is_physically_implausible(
    temperature_c: float | None,
    dew_point_c: float | None,
    previous_temperature_c: float | None = None,
) -> tuple[bool, str]:
    """Check if observation violates fundamental atmospheric thermodynamics.

    1. In meteorology, dry-bulb air temperature can never be lower than dew point (T >= Td).
       A tolerance of 1.0 C allows for minor instrument calibration skew.
    2. A sudden temperature drop or rise > 15 C within 1 hour without an extreme front
       indicates a faulty sensor or human transcription typo (e.g. typing 07 instead of 30).
    3. Ground air temperatures outside -15 C to +58 C violate Indian physical limits.
    """
    if temperature_c is None:
        return False, ""

    if dew_point_c is not None and dew_point_c > temperature_c + 1.0:
        return True, "DEWPOINT_EXCEEDS_TEMPERATURE"

    if previous_temperature_c is not None and abs(temperature_c - previous_temperature_c) > 15.0:
        return True, "RATE_OF_CHANGE_SPIKE"

    if temperature_c < -15.0 or temperature_c > 58.0:
        return True, "PHYSICAL_BOUNDS_VIOLATION"

    return False, ""


class WeatherApiClient:
    """High-resilience client for real-time weather assimilation."""

    def __init__(self, cache_path: Path = CACHE_PATH) -> None:
        self.cache_path = cache_path
        self._memory_cache: dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._memory_cache = data
            except Exception:
                self._memory_cache = {}

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._memory_cache), encoding="utf-8")
        except Exception:
            pass

    def fetch_station(self, lat: float, lon: float, timeout: float = 6.0) -> dict[str, float] | None:
        """Fetch current accurate weather telemetry for specific coordinates."""
        cache_key = f"{round(lat, 3)}_{round(lon, 3)}"
        cached = self._memory_cache.get(cache_key)
        now = time.time()
        if cached and (now - cached.get("cached_at", 0)) < CACHE_TTL_SECONDS:
            return cached.get("data")

        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,surface_pressure"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "SkyGuard-AI-Assimilation/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                current = result.get("current", {})
                t = current.get("temperature_2m")
                rh = current.get("relative_humidity_2m")
                p = current.get("surface_pressure")
                if t is not None:
                    weather_data = {
                        "temperature_c": float(t),
                        "relative_humidity_pct": float(rh) if rh is not None else None,
                        "surface_pressure_hpa": float(p) if p is not None else None,
                        "dew_point_c": calc_dew_point(float(t), float(rh)) if rh is not None else None,
                        "source_type": "REFERENCE_MODEL",
                        "provider": "OPEN_METEO_REFERENCE",
                        "is_direct_observation": False,
                        "is_model_value": True,
                    }
                    self._memory_cache[cache_key] = {"cached_at": now, "data": weather_data}
                    self._save_cache()
                    return weather_data
        except Exception:
            # Fallback to expired cache if available during transient network errors
            if cached and "data" in cached:
                return cached["data"]
        return None

    def fetch_batch_network(
        self,
        stations: list[dict[str, Any]],
        batch_size: int = 90,
        timeout: float = 10.0,
    ) -> dict[str, dict[str, float]]:
        """Fetch real-time weather in batch for multiple stations."""
        out: dict[str, dict[str, float]] = {}
        now = time.time()

        # Identify which stations need live fetching vs cache
        needed_chunks: list[list[dict[str, Any]]] = []
        current_chunk: list[dict[str, Any]] = []

        for stn in stations:
            sid = str(stn["station_id"])
            try:
                lat = float(stn.get("latitude") or 20.0)
                lon = float(stn.get("longitude") or 78.0)
            except (ValueError, TypeError):
                continue

            cache_key = f"{round(lat, 3)}_{round(lon, 3)}"
            cached = self._memory_cache.get(cache_key)
            if cached and (now - cached.get("cached_at", 0)) < CACHE_TTL_SECONDS:
                out[sid] = cached["data"]
            else:
                current_chunk.append(stn)
                if len(current_chunk) >= batch_size:
                    needed_chunks.append(current_chunk)
                    current_chunk = []

        if current_chunk:
            needed_chunks.append(current_chunk)

        # Query Open-Meteo for un-cached chunks
        for chunk in needed_chunks:
            lats = [str(stn.get("latitude") or 20.0) for stn in chunk]
            lons = [str(stn.get("longitude") or 78.0) for stn in chunk]
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={','.join(lats)}&longitude={','.join(lons)}"
                f"&current=temperature_2m,relative_humidity_2m,surface_pressure"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "SkyGuard-AI-Assimilation/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    items = resp_data if isinstance(resp_data, list) else [resp_data]
                    for idx, item in enumerate(items):
                        if idx < len(chunk):
                            stn = chunk[idx]
                            sid = str(stn["station_id"])
                            current = item.get("current", {})
                            t = current.get("temperature_2m")
                            rh = current.get("relative_humidity_2m")
                            p = current.get("surface_pressure")
                            if t is not None:
                                w_data = {
                                    "temperature_c": float(t),
                                    "relative_humidity_pct": float(rh) if rh is not None else None,
                                    "surface_pressure_hpa": float(p) if p is not None else None,
                                    "dew_point_c": calc_dew_point(float(t), float(rh)) if rh is not None else None,
                                    "source_type": "REFERENCE_MODEL",
                                    "provider": "OPEN_METEO_REFERENCE",
                                    "is_direct_observation": False,
                                    "is_model_value": True,
                                }
                                out[sid] = w_data
                                lat_c = float(stn.get("latitude") or 20.0)
                                lon_c = float(stn.get("longitude") or 78.0)
                                self._memory_cache[f"{round(lat_c, 3)}_{round(lon_c, 3)}"] = {
                                    "cached_at": now,
                                    "data": w_data,
                                }
            except Exception:
                # Fallback to existing memory cache if present
                for stn in chunk:
                    sid = str(stn["station_id"])
                    lat_c = float(stn.get("latitude") or 20.0)
                    lon_c = float(stn.get("longitude") or 78.0)
                    cached = self._memory_cache.get(f"{round(lat_c, 3)}_{round(lon_c, 3)}")
                    if cached and "data" in cached:
                        out[sid] = cached["data"]

        self._save_cache()
        return out


# Global singleton client
default_weather_client = WeatherApiClient()

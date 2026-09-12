"""Base abstractions and standardized schemas for weather data providers.

Enforces strict scientific provenance separating direct station observations
(IMD AWS, IMD WIS2, METAR, Meteostat observed) from reference models (Open-Meteo).
"""
from __future__ import annotations

import abc
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    OBSERVED = "OBSERVED"
    REFERENCE_MODEL = "REFERENCE_MODEL"
    INTERPOLATED_REFERENCE = "INTERPOLATED_REFERENCE"
    CONTROLLED_SIMULATION = "CONTROLLED_SIMULATION"


class ProviderName(str, Enum):
    IMD_AWS = "IMD_AWS"
    IMD_WIS2 = "IMD_WIS2"
    METAR = "METAR"
    METEOSTAT = "METEOSTAT"
    OPEN_METEO_REFERENCE = "OPEN_METEO_REFERENCE"


class RHSource(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    UNAVAILABLE = "UNAVAILABLE"


class StalenessStatus(str, Enum):
    CURRENT = "CURRENT"      # < 60 min
    DELAYED = "DELAYED"      # 60 - 180 min
    STALE = "STALE"          # > 180 min
    OFFLINE = "OFFLINE"      # No recent data


@dataclass
class ObservationRecord:
    provider: str
    source_type: str
    station_id: str
    timestamp_utc: str
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    is_direct_observation: bool = True
    is_interpolated: bool = False
    is_model_field: bool = False
    rh_source: str = RHSource.OBSERVED.value
    retrieved_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_source_hash: str = ""
    observation_age_minutes: Optional[float] = None
    quality_status: str = StalenessStatus.CURRENT.value

    def __post_init__(self):
        if self.source_type == SourceType.OBSERVED.value and not self.is_direct_observation:
            raise ValueError("OBSERVED requires a direct station observation")
        if self.source_type == SourceType.REFERENCE_MODEL.value and not self.is_model_field:
            raise ValueError("REFERENCE_MODEL requires is_model_field=True")
        if self.is_direct_observation and (self.is_model_field or self.is_interpolated):
            raise ValueError("Direct observations cannot be modelled or interpolated")
        # Calculate observation age and staleness
        if self.timestamp_utc:
            try:
                obs_dt = datetime.fromisoformat(self.timestamp_utc.replace("Z", "+00:00"))
                now_dt = datetime.now(timezone.utc)
                age = (now_dt - obs_dt).total_seconds() / 60.0
                self.observation_age_minutes = max(0.0, round(age, 1))
                if self.observation_age_minutes < 60:
                    self.quality_status = StalenessStatus.CURRENT.value
                elif self.observation_age_minutes < 180:
                    self.quality_status = StalenessStatus.DELAYED.value
                else:
                    self.quality_status = StalenessStatus.STALE.value
            except Exception:
                self.observation_age_minutes = None
                self.quality_status = StalenessStatus.OFFLINE.value

        # This is a normalized-record fingerprint, not a substitute for hashing raw bytes.
        if not self.raw_source_hash:
            fingerprint = f"{self.provider}|{self.station_id}|{self.timestamp_utc}|{self.temperature_c}|{self.pressure_hpa}|{self.relative_humidity_pct}"
            self.raw_source_hash = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WeatherProvider(abc.ABC):
    """Abstract base provider for all meteorological data sources."""

    def __init__(self, name: str, source_type: SourceType):
        self.name = name
        self.source_type = source_type

    @abc.abstractmethod
    def fetch_current(self, station_id: str) -> Optional[ObservationRecord]:
        """Fetch the latest available observation for a given station."""
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_history(self, station_id: str, hours: int = 24) -> List[ObservationRecord]:
        """Fetch historical observations up to N hours for a station."""
        raise NotImplementedError

    @abc.abstractmethod
    def station_metadata(self) -> List[Dict[str, Any]]:
        """Return list of supported station metadata dicts."""
        raise NotImplementedError

    @abc.abstractmethod
    def healthcheck(self) -> Dict[str, Any]:
        """Check provider connectivity, latency and status."""
        raise NotImplementedError

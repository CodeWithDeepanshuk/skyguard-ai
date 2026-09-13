"""Base abstractions and normalized schemas for weather data providers.

The provider contract is deliberately stricter than the model feature contract.
Models may only see temperature, pressure and relative humidity, while the
operational platform also needs identifiers, timestamps and provenance to avoid
mixing unlike observations.  In particular, pressure semantics are explicit:
station pressure, mean-sea-level pressure and aviation QNH are never silently
treated as interchangeable.
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


class HumidityObservationType(str, Enum):
    DIRECT = "DIRECT"
    DERIVED = "DERIVED"
    UNAVAILABLE = "UNAVAILABLE"


class PressureType(str, Enum):
    STATION_PRESSURE = "STATION_PRESSURE"
    MEAN_SEA_LEVEL_PRESSURE = "MEAN_SEA_LEVEL_PRESSURE"
    ALTIMETER_QNH = "ALTIMETER_QNH"
    UNKNOWN = "UNKNOWN"


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
    provider_station_id: str = ""
    canonical_station_id: str = ""
    wigos_id: str = ""
    icao_code: str = ""
    station_name: str = ""
    state: str = ""
    district: str = ""
    provider_publication_timestamp_utc: str = ""
    ingestion_timestamp_utc: str = ""
    pressure_type: str = PressureType.UNKNOWN.value
    humidity_observation_type: str = HumidityObservationType.UNAVAILABLE.value
    source_quality_flags: tuple[str, ...] = ()
    source_url: str = ""
    message_id: str = ""
    schema_version: str = "1.0"
    raw_payload_json: str = field(default="", repr=False)

    def __post_init__(self):
        self.provider_station_id = self.provider_station_id or self.station_id
        self.canonical_station_id = self.canonical_station_id or self.station_id
        self.ingestion_timestamp_utc = self.ingestion_timestamp_utc or self.retrieved_at_utc

        if not self.humidity_observation_type or self.humidity_observation_type == HumidityObservationType.UNAVAILABLE.value:
            if self.relative_humidity_pct is None:
                self.humidity_observation_type = HumidityObservationType.UNAVAILABLE.value
            elif self.rh_source == RHSource.DERIVED.value:
                self.humidity_observation_type = HumidityObservationType.DERIVED.value
            else:
                self.humidity_observation_type = HumidityObservationType.DIRECT.value

        allowed_pressure_types = {item.value for item in PressureType}
        if self.pressure_type not in allowed_pressure_types:
            raise ValueError(f"Unsupported pressure_type: {self.pressure_type}")

        allowed_humidity_types = {item.value for item in HumidityObservationType}
        if self.humidity_observation_type not in allowed_humidity_types:
            raise ValueError(
                f"Unsupported humidity_observation_type: {self.humidity_observation_type}"
            )

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

        # This fallback is only a normalized-record fingerprint. Providers that
        # have the raw message must supply its SHA-256 and raw_payload_json.
        if not self.raw_source_hash:
            fingerprint = f"{self.provider}|{self.station_id}|{self.timestamp_utc}|{self.temperature_c}|{self.pressure_hpa}|{self.relative_humidity_pct}"
            self.raw_source_hash = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
            if "NORMALIZED_FINGERPRINT_ONLY" not in self.source_quality_flags:
                self.source_quality_flags = (*self.source_quality_flags, "NORMALIZED_FINGERPRINT_ONLY")

        if self.pressure_hpa is not None and self.pressure_type == PressureType.UNKNOWN.value:
            if "PRESSURE_SEMANTICS_UNKNOWN" not in self.source_quality_flags:
                self.source_quality_flags = (*self.source_quality_flags, "PRESSURE_SEMANTICS_UNKNOWN")

    @property
    def observation_key(self) -> str:
        # A WIS2 report can be relayed by more than one Global Cache.  The raw
        # GeoJSON envelope can therefore differ even though the authoritative
        # provider message is the same.  Prefer the provider message ID for an
        # idempotency key; fall back to the normalized three-parameter payload
        # only when the source has no stable message identifier.
        source_identity = self.message_id or "|".join(
            (
                str(self.temperature_c), str(self.pressure_hpa), self.pressure_type,
                str(self.relative_humidity_pct), self.humidity_observation_type,
            )
        )
        identity = (
            f"{self.provider}|{self.provider_station_id}|{self.timestamp_utc}|"
            f"{source_identity}"
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    @property
    def measurement_confidence_factor(self) -> float:
        """Return a provenance factor, not a probability of sensor health."""
        if self.relative_humidity_pct is not None and self.humidity_observation_type == HumidityObservationType.DERIVED.value:
            return 0.85
        return 1.0

    def to_dict(self, *, include_raw: bool = False) -> Dict[str, Any]:
        payload = asdict(self)
        payload["observation_key"] = self.observation_key
        payload["measurement_confidence_factor"] = self.measurement_confidence_factor
        if not include_raw:
            payload.pop("raw_payload_json", None)
        return payload


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

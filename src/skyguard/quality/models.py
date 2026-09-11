"""Core observation, alert, and threshold contracts for quality control."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Mapping


def optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@dataclass(frozen=True)
class Observation:
    station_id: str
    timestamp: datetime
    temperature_c: float | None
    pressure_hpa: float | None
    relative_humidity_pct: float | None
    dew_point_c: float | None = None
    temperature_quality: str = ""
    pressure_quality: str = ""
    pressure_source: str = ""
    dew_point_quality: str = ""
    cluster: str = ""
    evaluation_role: str = ""

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "Observation":
        timestamp = str(row["timestamp_utc"]).removesuffix("Z")
        return cls(
            station_id=str(row["station_id"]),
            timestamp=datetime.fromisoformat(timestamp),
            temperature_c=optional_float(row.get("temperature_c")),
            pressure_hpa=optional_float(row.get("pressure_hpa")),
            relative_humidity_pct=optional_float(row.get("relative_humidity_pct")),
            dew_point_c=optional_float(row.get("dew_point_c")),
            temperature_quality=str(row.get("temperature_quality", "")),
            pressure_quality=str(row.get("pressure_quality", "")),
            pressure_source=str(row.get("pressure_source", "")),
            dew_point_quality=str(row.get("dew_point_quality", "")),
            cluster=str(row.get("cluster", "")),
            evaluation_role=str(row.get("evaluation_role", "")),
        )


@dataclass(frozen=True)
class Alert:
    alert_id: str
    station_id: str
    timestamp_utc: str
    rule_code: str
    sensor: str
    severity: str
    score: float
    observed_value: str
    expected_condition: str
    explanation: str

    @classmethod
    def create(
        cls,
        observation: Observation,
        rule_code: str,
        sensor: str,
        severity: str,
        score: float,
        observed_value: object,
        expected_condition: str,
        explanation: str,
    ) -> "Alert":
        timestamp = observation.timestamp.isoformat(timespec="seconds") + "Z"
        identity = f"{observation.station_id}|{timestamp}|{rule_code}|{sensor}|{observed_value}"
        alert_id = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]
        return cls(
            alert_id=alert_id,
            station_id=observation.station_id,
            timestamp_utc=timestamp,
            rule_code=rule_code,
            sensor=sensor,
            severity=severity,
            score=round(max(0.0, min(1.0, score)), 4),
            observed_value="" if observed_value is None else str(observed_value),
            expected_condition=expected_condition,
            explanation=explanation,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class QualityThresholds:
    temperature_min_c: float = -60.0
    temperature_max_c: float = 60.0
    pressure_min_hpa: float = 870.0
    pressure_max_hpa: float = 1075.0
    # Broad configurable envelope for station/unknown pressure, not sea-level QC.
    station_pressure_min_hpa: float = 300.0
    station_pressure_max_hpa: float = 1100.0
    humidity_min_pct: float = 0.0
    humidity_max_pct: float = 100.0
    dew_point_margin_c: float = 1.0
    max_temperature_change_c_per_hour: float = 8.0
    max_pressure_change_hpa_per_hour: float = 8.0
    max_humidity_change_pct_per_hour: float = 35.0
    max_rate_interval_hours: float = 6.0
    gap_multiplier: float = 4.0
    minimum_gap_hours: float = 6.0
    frozen_duration_hours: float = 12.0
    frozen_min_readings: int = 4
    temperature_equality_tolerance: float = 0.05
    pressure_equality_tolerance: float = 0.05
    humidity_equality_tolerance: float = 0.05
    suspicious_quality_codes: frozenset[str] = frozenset({"2", "6"})
    erroneous_quality_codes: frozenset[str] = frozenset({"3", "7"})

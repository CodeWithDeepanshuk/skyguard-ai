"""Contracts for synthetic fault and genuine-weather scenario episodes."""

from __future__ import annotations

from dataclasses import asdict, dataclass


FAULT_TYPES = (
    "spike",
    "sudden_drop",
    "bias",
    "drift",
    "noise",
    "frozen_sensor",
    "dropout",
    "duplicate_packet",
    "timestamp_error",
    "unit_error",
    "scaling_error",
    "communication_corruption",
    "multi_sensor_failure",
)


@dataclass(frozen=True)
class Episode:
    split: str
    episode_id: str
    label_category: str
    anomaly_type: str
    sensors: str
    stations: str
    start_utc: str
    end_utc: str
    severity: str
    affected_rows: int
    stream_action: str
    random_seed: int
    description: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

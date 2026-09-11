"""Replay event and alert contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class StreamAlert:
    alert_id: str
    station_id: str
    timestamp_utc: str
    alert_type: str
    severity: str
    explanation: str
    target_episode_id: str = ""

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

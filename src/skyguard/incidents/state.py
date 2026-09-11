"""Causal k-of-n incident lifecycle with instant, persistence, and recovery paths."""

from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .triage import ThreeWayTriage, TriageConfig, TriageResult


def _timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class IncidentConfig:
    candidate_threshold: float = 0.35
    instant_threshold: float = 0.96
    confirm_k: int = 3
    confirm_n: int = 5
    maximum_evidence_window_minutes: float = 360.0
    maximum_incident_gap_minutes: float = 360.0
    recovery_threshold: float = 0.22
    recovery_points: int = 3
    drift_candidate_threshold: float = 0.55

    def __post_init__(self) -> None:
        if not 1 <= self.confirm_k <= self.confirm_n:
            raise ValueError("confirm_k must be between one and confirm_n")
        if self.recovery_points < 1:
            raise ValueError("recovery_points must be positive")


@dataclass(frozen=True)
class IncidentEvidence:
    station_id: str
    timestamp_utc: str | datetime
    fault_probability: float
    weather_probability: float
    normal_probability: float
    affected_sensors: tuple[str, ...] = ()
    hard_fault_codes: tuple[str, ...] = ()
    communication_codes: tuple[str, ...] = ()
    neighbour_station_count: int = 0
    neighbour_agreement: float = 0.0
    regional_extent: float = 0.0
    sensor_consistency: float = 0.0
    station_isolation: float | None = None
    drift_score: float = 0.0


@dataclass(frozen=True)
class IncidentDecision:
    station_id: str
    timestamp_utc: str
    state: str
    lifecycle: str
    incident_id: str
    confidence: float
    severity: str
    start_utc: str | None
    evidence_count: int
    evidence_window_count: int
    affected_sensors: tuple[str, ...]
    weather_gate_supported: bool
    explanation: str


@dataclass
class _StationIncidentState:
    last_timestamp: datetime | None = None
    evidence: deque[tuple[datetime, bool]] = field(default_factory=deque)
    incident_id: str = ""
    incident_start: datetime | None = None
    peak_confidence: float = 0.0
    evidence_count: int = 0
    low_evidence_run: int = 0
    affected_sensors: set[str] = field(default_factory=set)


class IncidentStateEngine:
    """Stateful causal incident aggregator suitable for replay and live streams."""

    def __init__(
        self,
        config: IncidentConfig | None = None,
        triage_config: TriageConfig | None = None,
    ) -> None:
        self.config = config or IncidentConfig()
        self.triage = ThreeWayTriage(triage_config)
        self.states: dict[str, _StationIncidentState] = {}

    @staticmethod
    def _id(station: str, start: datetime) -> str:
        identity = f"{station}|{start.isoformat()}"
        return "I10-" + hashlib.sha1(identity.encode("utf-8")).hexdigest()[:14].upper()

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return None if value is None else value.isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _severity(confidence: float, deterministic: bool = False) -> str:
        if deterministic or confidence >= 0.95:
            return "critical"
        if confidence >= 0.80:
            return "high"
        if confidence >= 0.60:
            return "medium"
        return "low"

    def _decision(
        self,
        evidence: IncidentEvidence,
        state: _StationIncidentState,
        triage: TriageResult,
        operational_state: str,
        lifecycle: str,
        explanation: str,
    ) -> IncidentDecision:
        timestamp = _timestamp(evidence.timestamp_utc)
        deterministic = bool(evidence.hard_fault_codes or evidence.communication_codes)
        confidence = (
            state.peak_confidence if operational_state == "confirmed_fault"
            else triage.weather_probability if operational_state == "genuine_weather"
            else triage.fault_probability if operational_state in {"candidate_fault", "advisory"}
            else triage.normal_probability
        )
        return IncidentDecision(
            station_id=evidence.station_id,
            timestamp_utc=self._iso(timestamp) or "",
            state=operational_state,
            lifecycle=lifecycle,
            incident_id=state.incident_id,
            confidence=float(confidence),
            severity=self._severity(float(confidence), deterministic),
            start_utc=self._iso(state.incident_start),
            evidence_count=int(state.evidence_count),
            evidence_window_count=int(sum(item[1] for item in state.evidence)),
            affected_sensors=tuple(sorted(state.affected_sensors)),
            weather_gate_supported=triage.weather_gate_supported,
            explanation=explanation,
        )

    def process(self, evidence: IncidentEvidence) -> IncidentDecision:
        timestamp = _timestamp(evidence.timestamp_utc)
        state = self.states.setdefault(evidence.station_id, _StationIncidentState())
        hard_fault = bool(evidence.hard_fault_codes)
        communication_fault = bool(evidence.communication_codes)
        triage = self.triage.classify(
            normal_probability=evidence.normal_probability,
            weather_probability=evidence.weather_probability,
            fault_probability=evidence.fault_probability,
            neighbour_station_count=evidence.neighbour_station_count,
            neighbour_agreement=evidence.neighbour_agreement,
            regional_extent=evidence.regional_extent,
            sensor_consistency=evidence.sensor_consistency,
            station_isolation=evidence.station_isolation,
            drift_score=evidence.drift_score,
            hard_fault=hard_fault,
            communication_fault=communication_fault,
        )

        # An out-of-order event is diagnosed immediately but must not corrupt
        # the causal state built from later timestamps.
        if state.last_timestamp is not None and timestamp < state.last_timestamp:
            temporary = _StationIncidentState(
                incident_id=self._id(evidence.station_id, timestamp), incident_start=timestamp,
                peak_confidence=max(triage.fault_probability, 0.995), evidence_count=1,
                affected_sensors=set(evidence.affected_sensors) or {"communication"},
            )
            return self._decision(
                evidence, temporary, triage, "confirmed_fault", "opened",
                "Out-of-order transport evidence created an immediate incident without changing later stream state.",
            )

        if state.last_timestamp is not None:
            elapsed = (timestamp - state.last_timestamp).total_seconds() / 60.0
            if elapsed > self.config.maximum_incident_gap_minutes and state.incident_id:
                # A stale open incident is reset before handling the new row.
                state.incident_id = ""
                state.incident_start = None
                state.peak_confidence = 0.0
                state.evidence_count = 0
                state.low_evidence_run = 0
                state.affected_sensors.clear()
                state.evidence.clear()
        state.last_timestamp = timestamp

        while state.evidence and (
            (timestamp - state.evidence[0][0]).total_seconds() / 60.0
            > self.config.maximum_evidence_window_minutes
        ):
            state.evidence.popleft()

        candidate = (
            triage.fault_probability >= self.config.candidate_threshold
            or float(evidence.drift_score) >= self.config.drift_candidate_threshold
            or hard_fault
            or communication_fault
        ) and triage.state != "genuine_weather"
        state.evidence.append((timestamp, candidate))
        while len(state.evidence) > self.config.confirm_n:
            state.evidence.popleft()

        if triage.state == "genuine_weather" and not state.incident_id:
            state.evidence.clear()
            return self._decision(
                evidence, state, triage, "genuine_weather", "none", triage.explanation,
            )

        immediate = hard_fault or communication_fault or triage.fault_probability >= self.config.instant_threshold
        persistent = sum(item[1] for item in state.evidence) >= self.config.confirm_k

        if state.incident_id:
            if candidate or triage.fault_probability >= self.config.recovery_threshold:
                state.low_evidence_run = 0
                state.evidence_count += int(candidate)
                state.peak_confidence = max(state.peak_confidence, triage.fault_probability, float(evidence.drift_score))
                state.affected_sensors.update(evidence.affected_sensors)
                return self._decision(
                    evidence, state, triage, "confirmed_fault", "updated",
                    f"Incident remains active; peak confidence {state.peak_confidence:.3f}. {triage.explanation}",
                )
            state.low_evidence_run += 1
            if state.low_evidence_run >= self.config.recovery_points:
                decision = self._decision(
                    evidence, state, triage, "normal", "closed",
                    f"Incident closed after {state.low_evidence_run} consecutive recovery observations.",
                )
                state.incident_id = ""
                state.incident_start = None
                state.peak_confidence = 0.0
                state.evidence_count = 0
                state.low_evidence_run = 0
                state.affected_sensors.clear()
                state.evidence.clear()
                return decision
            return self._decision(
                evidence, state, triage, "confirmed_fault", "updated",
                f"Incident is in recovery hysteresis ({state.low_evidence_run}/{self.config.recovery_points}).",
            )

        if immediate or persistent:
            state.incident_start = state.evidence[0][0] if persistent and state.evidence else timestamp
            state.incident_id = self._id(evidence.station_id, state.incident_start)
            state.peak_confidence = max(triage.fault_probability, float(evidence.drift_score))
            state.evidence_count = int(sum(item[1] for item in state.evidence))
            state.low_evidence_run = 0
            state.affected_sensors.update(evidence.affected_sensors)
            route = "instant deterministic path" if immediate else f"{self.config.confirm_k}-of-{self.config.confirm_n} persistence path"
            return self._decision(
                evidence, state, triage, "confirmed_fault", "opened",
                f"Incident opened through the {route}. {triage.explanation}",
            )

        if candidate:
            state.affected_sensors.update(evidence.affected_sensors)
            return self._decision(
                evidence, state, triage, "candidate_fault", "none",
                f"Weak evidence is accumulating ({sum(item[1] for item in state.evidence)}/{self.config.confirm_k}); no automatic alert yet.",
            )
        operational = "advisory" if triage.state == "advisory" else "normal"
        return self._decision(evidence, state, triage, operational, "none", triage.explanation)

    def snapshot(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for station, state in sorted(self.states.items()):
            rows.append({
                "station_id": station, "incident_id": state.incident_id,
                "start_utc": self._iso(state.incident_start),
                "last_timestamp_utc": self._iso(state.last_timestamp),
                "peak_confidence": state.peak_confidence,
                "evidence_count": state.evidence_count,
                "affected_sensors": sorted(state.affected_sensors),
                "active": bool(state.incident_id),
            })
        return rows

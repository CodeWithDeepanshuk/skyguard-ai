"""Dedicated causal drift/degradation state machine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np


def _time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class DriftConfig:
    history_hours: float = 24.0
    minimum_span_hours: float = 3.0
    minimum_points: int = 4
    slope_z_per_hour: float = 0.10
    cusum_threshold: float = 5.0
    monotonic_run_threshold: int = 3
    confirm_k: int = 3
    confirm_n: int = 4
    recovery_residual_z: float = 1.0
    recovery_points: int = 3
    minimum_neighbours: int = 1


@dataclass(frozen=True)
class DriftEvidence:
    station_id: str
    sensor: str
    timestamp_utc: str | datetime
    neighbour_residual_z: float
    cusum_positive: float
    cusum_negative: float
    monotonic_run: int
    neighbour_count: int


@dataclass(frozen=True)
class DriftDecision:
    state: str
    score: float
    slope_z_per_hour: float
    duration_hours: float
    persistence_count: int
    explanation: str


@dataclass
class _DriftState:
    history: deque[tuple[datetime, float]] = field(default_factory=deque)
    evidence: deque[bool] = field(default_factory=deque)
    active: bool = False
    active_since: datetime | None = None
    recovery_run: int = 0


class DriftStateMachine:
    def __init__(self, config: DriftConfig | None = None) -> None:
        self.config = config or DriftConfig()
        self.states: dict[tuple[str, str], _DriftState] = {}

    @staticmethod
    def _slope(history: deque[tuple[datetime, float]]) -> tuple[float, float]:
        if len(history) < 2:
            return 0.0, 0.0
        origin = history[0][0]
        x = np.asarray([(item[0] - origin).total_seconds() / 3600.0 for item in history], dtype=float)
        y = np.asarray([item[1] for item in history], dtype=float)
        span = float(x[-1] - x[0])
        centered = x - x.mean()
        denominator = float(np.dot(centered, centered))
        slope = 0.0 if denominator <= 1e-12 else float(np.dot(centered, y - y.mean()) / denominator)
        return slope, span

    def update(self, item: DriftEvidence) -> DriftDecision:
        config = self.config
        timestamp = _time(item.timestamp_utc)
        key = (item.station_id, item.sensor)
        state = self.states.setdefault(key, _DriftState())
        if state.history and timestamp <= state.history[-1][0]:
            return DriftDecision(
                "ignored_out_of_order", 0.0, 0.0, 0.0, sum(state.evidence),
                "Out-of-order evidence was ignored so future state cannot alter the causal drift baseline.",
            )
        state.history.append((timestamp, float(item.neighbour_residual_z)))
        cutoff = timestamp.timestamp() - config.history_hours * 3600.0
        while state.history and state.history[0][0].timestamp() < cutoff:
            state.history.popleft()
        slope, span = self._slope(state.history)
        cusum = max(abs(float(item.cusum_positive)), abs(float(item.cusum_negative)))
        slope_strength = min(1.0, abs(slope) / max(config.slope_z_per_hour * 2.0, 1e-9))
        cusum_strength = min(1.0, cusum / max(config.cusum_threshold * 2.0, 1e-9))
        monotonic_strength = min(1.0, abs(int(item.monotonic_run)) / max(config.monotonic_run_threshold * 2.0, 1))
        neighbour_strength = min(1.0, int(item.neighbour_count) / max(config.minimum_neighbours, 1))
        score = 0.35 * slope_strength + 0.35 * cusum_strength + 0.20 * monotonic_strength + 0.10 * neighbour_strength
        qualifies = (
            len(state.history) >= config.minimum_points
            and span >= config.minimum_span_hours
            and abs(slope) >= config.slope_z_per_hour
            and cusum >= config.cusum_threshold
            and abs(int(item.monotonic_run)) >= config.monotonic_run_threshold
            and int(item.neighbour_count) >= config.minimum_neighbours
        )
        state.evidence.append(bool(qualifies))
        while len(state.evidence) > config.confirm_n:
            state.evidence.popleft()

        if not state.active and sum(state.evidence) >= config.confirm_k:
            state.active = True
            state.active_since = timestamp
            state.recovery_run = 0
            decision_state = "drift_confirmed"
        elif state.active:
            if abs(float(item.neighbour_residual_z)) <= config.recovery_residual_z and not qualifies:
                state.recovery_run += 1
            else:
                state.recovery_run = 0
            if state.recovery_run >= config.recovery_points:
                state.active = False
                state.active_since = None
                state.evidence.clear()
                state.recovery_run = 0
                decision_state = "drift_recovered"
            else:
                decision_state = "drift_active"
        elif qualifies:
            decision_state = "drift_candidate"
        else:
            decision_state = "normal"
        explanation = (
            f"Causal neighbour-residual slope={slope:.3f} z/hour over {span:.1f} hours; "
            f"CUSUM={cusum:.2f}; monotonic run={int(item.monotonic_run)}; "
            f"persistence={sum(state.evidence)}/{config.confirm_k}."
        )
        return DriftDecision(decision_state, float(score), slope, span, int(sum(state.evidence)), explanation)

"""Stateful, streaming-compatible quality-control engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite

from .models import Alert, Observation, QualityThresholds
from .rules import run_stateless_rules


@dataclass
class FrozenState:
    value: float | None = None
    started_at: datetime | None = None
    count: int = 0
    emitted: bool = False


@dataclass
class StationState:
    last_observation: Observation | None = None
    seen_timestamps: set[datetime] = field(default_factory=set)
    frozen: dict[str, FrozenState] = field(default_factory=lambda: {
        "temperature": FrozenState(),
        "pressure": FrozenState(),
        "humidity": FrozenState(),
    })
    multi_freeze_emitted: bool = False


class QualityControlEngine:
    def __init__(
        self,
        expected_interval_minutes: dict[str, float] | None = None,
        thresholds: QualityThresholds | None = None,
        heartbeat_sla_minutes: dict[str, float] | None = None,
    ) -> None:
        self.expected_interval_minutes = expected_interval_minutes or {}
        self.thresholds = thresholds or QualityThresholds()
        self.heartbeat_sla_minutes = heartbeat_sla_minutes or {}
        self.states: dict[str, StationState] = {}

    def process(self, observation: Observation) -> list[Alert]:
        alerts = run_stateless_rules(observation, self.thresholds)
        state = self.states.setdefault(observation.station_id, StationState())
        timestamp_alerts = self._check_timestamp(observation, state)
        alerts.extend(timestamp_alerts)
        if any(alert.rule_code in {"DUPLICATE_TIMESTAMP", "OUT_OF_ORDER_TIMESTAMP"} for alert in timestamp_alerts):
            return alerts
        alerts.extend(self._check_changes(observation, state))
        alerts.extend(self._check_frozen(observation, state))

        state.seen_timestamps.add(observation.timestamp)
        if state.last_observation is None or observation.timestamp >= state.last_observation.timestamp:
            state.last_observation = observation
        return alerts

    def _check_timestamp(self, observation: Observation, state: StationState) -> list[Alert]:
        alerts: list[Alert] = []
        if observation.timestamp in state.seen_timestamps:
            alerts.append(Alert.create(
                observation, "DUPLICATE_TIMESTAMP", "communication", "medium", 0.8,
                observation.timestamp.isoformat(), "One record per station and timestamp.",
                "This station timestamp has already been processed.",
            ))
        previous = state.last_observation
        if previous is None:
            return alerts
        delta_minutes = (observation.timestamp - previous.timestamp).total_seconds() / 60.0
        if delta_minutes < 0:
            alerts.append(Alert.create(
                observation, "OUT_OF_ORDER_TIMESTAMP", "communication", "high", 0.9,
                observation.timestamp.isoformat(), f"Timestamp after {previous.timestamp.isoformat()}.",
                "The observation arrived earlier than the latest processed timestamp.",
            ))
            return alerts

        expected = self.expected_interval_minutes.get(observation.station_id)
        heartbeat_sla = self.heartbeat_sla_minutes.get(observation.station_id)
        advisory_limit = max(
            self.thresholds.minimum_gap_hours * 60.0,
            expected * self.thresholds.gap_multiplier if expected else 0.0,
        )
        if expected and heartbeat_sla and delta_minutes > heartbeat_sla:
            alerts.append(Alert.create(
                observation, "COMMUNICATION_GAP", "communication", "high",
                min(1.0, 0.7 + delta_minutes / max(heartbeat_sla * 5.0, 1.0)),
                f"{delta_minutes:.1f} minutes", f"Verified heartbeat SLA no longer than {heartbeat_sla:.1f} minutes.",
                f"No station reading was received for {delta_minutes / 60.0:.1f} hours; the verified heartbeat SLA was exceeded.",
            ))
        elif (not expected or not heartbeat_sla) and delta_minutes > advisory_limit:
            alerts.append(Alert.create(
                observation, "UNVERIFIED_DATA_GAP", "communication", "low", 0.35,
                f"{delta_minutes:.1f} minutes", "Source adapter must supply expected cadence and heartbeat SLA for an automatic fault alert.",
                f"A {delta_minutes / 60.0:.1f}-hour data gap was observed without a verified heartbeat contract. Advisory only.",
            ))
        return alerts

    def _check_changes(self, observation: Observation, state: StationState) -> list[Alert]:
        previous = state.last_observation
        if previous is None:
            return []
        hours = (observation.timestamp - previous.timestamp).total_seconds() / 3600.0
        if hours <= 0 or hours > self.thresholds.max_rate_interval_hours:
            return []
        definitions = (
            ("temperature", observation.temperature_c, previous.temperature_c, self.thresholds.max_temperature_change_c_per_hour, "°C/hour", True),
            (
                "pressure", observation.pressure_hpa, previous.pressure_hpa,
                self.thresholds.max_pressure_change_hpa_per_hour, "hPa/hour",
                bool(observation.pressure_source and observation.pressure_source == previous.pressure_source),
            ),
            ("humidity", observation.relative_humidity_pct, previous.relative_humidity_pct, self.thresholds.max_humidity_change_pct_per_hour, "%/hour", True),
        )
        alerts: list[Alert] = []
        for sensor, current, prior, limit, unit, comparable in definitions:
            if not comparable or current is None or prior is None or not isfinite(current) or not isfinite(prior):
                continue
            rate = abs(current - prior) / hours
            if rate > limit:
                alerts.append(Alert.create(
                    observation, "RATE_OF_CHANGE", sensor, "high", min(1.0, 0.65 + 0.35 * rate / limit),
                    f"{rate:.3f} {unit}", f"Absolute change no greater than {limit:g} {unit}.",
                    f"{sensor.capitalize()} changed from {prior:g} to {current:g} in {hours:.2f} hours.",
                ))
        return alerts

    def _check_frozen(self, observation: Observation, state: StationState) -> list[Alert]:
        previous = state.last_observation
        if previous is not None:
            gap_minutes = (observation.timestamp - previous.timestamp).total_seconds() / 60
            expected = self.expected_interval_minutes.get(observation.station_id)
            limit = (expected * self.thresholds.gap_multiplier if expected
                     else self.thresholds.minimum_gap_hours * 60)
            if gap_minutes > limit:
                state.frozen = {sensor: FrozenState() for sensor in state.frozen}
                state.multi_freeze_emitted = False
            elif observation.pressure_source != previous.pressure_source:
                state.frozen["pressure"] = FrozenState()
                state.multi_freeze_emitted = False
        definitions = (
            ("temperature", observation.temperature_c, self.thresholds.temperature_equality_tolerance),
            ("pressure", observation.pressure_hpa, self.thresholds.pressure_equality_tolerance),
            ("humidity", observation.relative_humidity_pct, self.thresholds.humidity_equality_tolerance),
        )
        alerts: list[Alert] = []
        frozen_now: list[str] = []
        for sensor, value, tolerance in definitions:
            item = state.frozen[sensor]
            if value is None or not isfinite(value):
                state.frozen[sensor] = FrozenState()
                state.multi_freeze_emitted = False
                continue
            if item.value is not None and abs(value - item.value) <= tolerance:
                item.count += 1
            else:
                state.frozen[sensor] = item = FrozenState(value=value, started_at=observation.timestamp, count=1)
                state.multi_freeze_emitted = False
            duration = 0.0 if item.started_at is None else (observation.timestamp - item.started_at).total_seconds() / 3600.0
            qualifies = item.count >= self.thresholds.frozen_min_readings and duration >= self.thresholds.frozen_duration_hours
            if qualifies:
                frozen_now.append(sensor)
                if not item.emitted:
                    saturated = sensor == "humidity" and abs(value - 100.0) <= tolerance
                    alerts.append(Alert.create(
                        observation, "SATURATION_REVIEW" if saturated else "FROZEN_SENSOR",
                        sensor, "low" if saturated else "medium",
                        0.35 if saturated else min(1.0, 0.7 + duration / 120.0),
                        value, f"Value should vary within {self.thresholds.frozen_duration_hours:g} hours.",
                        ("Persistent 100% humidity can be genuine atmospheric saturation or sensor clipping; "
                         "additional evidence is required before identifying a sensor fault." if saturated else
                         f"{sensor.capitalize()} has remained unchanged for {duration:.1f} hours across {item.count} readings."),
                    ))
                    item.emitted = True

        if len(frozen_now) == 3 and not state.multi_freeze_emitted:
            alerts.append(Alert.create(
                observation, "MULTI_SENSOR_FREEZE", "station", "high", 0.95,
                ",".join(frozen_now), "At least one primary variable should change over the freeze window.",
                "Temperature, pressure, and humidity are all frozen, suggesting station or communication failure.",
            ))
            state.multi_freeze_emitted = True
        return alerts

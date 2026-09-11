"""Readable explanations, severity, and sensor-health state."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from collections.abc import Mapping

from .estimators import SENSORS, VALUE_COLUMNS, number, sensor_evidence


FAULT_TEXT = {
    "spike": "sudden isolated spike",
    "sudden_drop": "sudden isolated drop",
    "frozen_sensor": "reading has remained unusually constant",
    "bias": "persistent offset from expected conditions",
    "drift": "gradual deviation from temporal and neighbouring-station behaviour",
    "noise": "unusually high short-term variability",
    "unit_error": "probable unit conversion error",
    "scaling_error": "probable scaling error",
    "communication_corruption": "corrupted multi-sensor transmission",
    "multi_sensor_failure": "multiple sensors show coordinated failure evidence",
    "unknown_fault": "abnormal sensor behaviour with uncertain root cause",
}


def severity(fault_probability: float, predicted_root: str, evidence_score: float) -> str:
    if predicted_root in {"communication_corruption", "unit_error", "scaling_error"} or fault_probability >= 0.90 or evidence_score >= 8:
        return "critical"
    if fault_probability >= 0.70 or evidence_score >= 4:
        return "high"
    if fault_probability >= 0.50 or evidence_score >= 2:
        return "medium"
    return "low"


def recommendation(level: str, health_score: float) -> str:
    if level == "critical" or health_score < 40:
        return "Quarantine the reading and inspect or calibrate the sensor immediately."
    if level == "high" or health_score < 70:
        return "Inspect and calibrate the sensor within seven days."
    if level == "medium" or health_score < 85:
        return "Monitor the next readings and schedule preventive inspection."
    return "Monitor; no immediate maintenance action is required."


def explain(row: Mapping[str, object], sensors: list[str], predicted_root: str, fault_probability: float) -> tuple[str, list[dict[str, object]]]:
    evidence_rows: list[dict[str, object]] = []
    for sensor in sensors or list(SENSORS):
        evidence = sensor_evidence(row, sensor)
        strongest = sorted(evidence.items(), key=lambda item: item[1], reverse=True)[:2]
        evidence_rows.extend({"sensor": sensor, "signal": name, "score": round(score, 3)} for name, score in strongest)
    strongest_text = ", ".join(
        f"{item['sensor']} {item['signal']}={item['score']}" for item in sorted(evidence_rows, key=lambda item: item["score"], reverse=True)[:3]
    )
    description = FAULT_TEXT.get(predicted_root, FAULT_TEXT["unknown_fault"])
    sensor_text = ", ".join(sensors) if sensors else "station stream"
    text = f"Probable {description} affecting {sensor_text}. Evidence: {strongest_text}. Calibrated fault probability: {fault_probability:.1%}."
    return text, evidence_rows


@dataclass
class HealthState:
    risk: float = 0.0
    last_timestamp: datetime | None = None
    incident_count: int = 0
    severity_counts: dict[str, int] = field(default_factory=dict)
    history: list[tuple[datetime, float]] = field(default_factory=list)


class SensorHealthTracker:
    def __init__(self, half_life_days: float = 14.0) -> None:
        self.half_life_days = half_life_days
        self.states: dict[tuple[str, str], HealthState] = {}

    def update(self, station: str, sensor: str, timestamp: str, level: str, confidence: float) -> float:
        key = (station, sensor)
        state = self.states.setdefault(key, HealthState())
        current = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        repeated = False
        if state.last_timestamp is not None:
            elapsed_days = max(0.0, (current - state.last_timestamp).total_seconds() / 86400.0)
            state.risk *= 0.5 ** (elapsed_days / self.half_life_days)
            repeated = elapsed_days < 0.25
        increments = {"low": 2.0, "medium": 5.0, "high": 11.0, "critical": 20.0}
        increment = increments[level] * max(0.25, confidence)
        if repeated:
            increment *= 0.20
        state.risk = min(100.0, state.risk + increment)
        state.last_timestamp = current
        state.incident_count += 1
        state.severity_counts[level] = state.severity_counts.get(level, 0) + 1
        score = round(100.0 - state.risk, 2)
        state.history.append((current, score))
        state.history = state.history[-50:]
        return score

    @staticmethod
    def _forecast(state: HealthState, score: float) -> dict[str, object]:
        """Project the recent health trajectory without claiming calibrated failure probability."""
        history = state.history
        slope: float | None = None
        confidence = 0.0
        if len(history) >= 3:
            cutoff = history[-1][0].timestamp() - 30.0 * 86400.0
            recent = [(timestamp, value) for timestamp, value in history if timestamp.timestamp() >= cutoff]
            span_days = (recent[-1][0] - recent[0][0]).total_seconds() / 86400.0
            if len(recent) >= 3 and span_days >= 1.0:
                x = [(timestamp - recent[0][0]).total_seconds() / 86400.0 for timestamp, _ in recent]
                y = [value for _, value in recent]
                x_mean = sum(x) / len(x)
                y_mean = sum(y) / len(y)
                denominator = sum((value - x_mean) ** 2 for value in x)
                if denominator > 1e-9:
                    slope = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y)) / denominator
                    slope = max(-20.0, min(20.0, slope))
                    confidence = min(1.0, (len(recent) / 8.0) * (span_days / 14.0))
        projected_7d = score if slope is None else max(0.0, min(100.0, score + 7.0 * slope))
        horizon: float | None = None
        if score <= 40.0:
            horizon = 0.0
        elif slope is not None and slope < -0.05:
            horizon = min(365.0, (score - 40.0) / -slope)
        trend = "insufficient_history" if slope is None else "degrading" if slope < -0.25 else "recovering" if slope > 0.25 else "stable"
        return {
            "health_trend": trend,
            "degradation_slope_points_per_day": None if slope is None else round(slope, 3),
            "projected_health_7d": round(projected_7d, 2),
            "degradation_risk_7d": round(100.0 - projected_7d, 2),
            "maintenance_horizon_days": None if horizon is None else round(horizon, 1),
            "forecast_confidence": round(confidence, 3),
            "forecast_method": "30-day health trajectory; heuristic decision support, not a calibrated failure probability",
        }

    def snapshot(self, station: str, sensor: str) -> dict[str, object]:
        state = self.states.get((station, sensor), HealthState())
        score = round(100.0 - state.risk, 2)
        status = "healthy" if score >= 85 else "monitor" if score >= 70 else "degrading" if score >= 40 else "critical"
        forecast = self._forecast(state, score)
        action = recommendation("low", score)
        horizon = forecast["maintenance_horizon_days"]
        if horizon is not None and horizon <= 7 and score >= 40:
            action = "Health is degrading rapidly; inspect and calibrate the sensor within seven days."
        return {
            "station_id": station, "sensor": sensor, "health_score": score, "status": status,
            "incident_count": state.incident_count, "severity_counts": dict(state.severity_counts),
            "last_incident_utc": state.last_timestamp.isoformat().replace("+00:00", "Z") if state.last_timestamp else None,
            "recommended_action": action,
            **forecast,
        }

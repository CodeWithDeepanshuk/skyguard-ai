"""Mutually exclusive normal/weather/fault triage for candidate incidents.

This guard is deliberately model-agnostic.  It receives calibrated base class
probabilities and spatial evidence, then prevents a weather decision unless
independent neighbour coherence is available.  A high fault score can never
increase weather probability.
"""

from __future__ import annotations

from dataclasses import dataclass


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class TriageConfig:
    minimum_neighbours: int = 2
    minimum_neighbour_agreement: float = 0.55
    minimum_regional_extent: float = 0.40
    minimum_sensor_consistency: float = 0.34
    minimum_decision_confidence: float = 0.55
    hard_fault_floor: float = 0.995


@dataclass(frozen=True)
class TriageResult:
    state: str
    normal_probability: float
    weather_probability: float
    fault_probability: float
    confidence: float
    weather_gate_supported: bool
    spatial_coherence: float
    explanation: str


class ThreeWayTriage:
    """Convert base evidence into one mutually exclusive operational state."""

    def __init__(self, config: TriageConfig | None = None) -> None:
        self.config = config or TriageConfig()

    def classify(
        self,
        *,
        normal_probability: float,
        weather_probability: float,
        fault_probability: float,
        neighbour_station_count: int = 0,
        neighbour_agreement: float = 0.0,
        regional_extent: float = 0.0,
        sensor_consistency: float = 0.0,
        station_isolation: float | None = None,
        drift_score: float = 0.0,
        hard_fault: bool = False,
        communication_fault: bool = False,
    ) -> TriageResult:
        normal = _clip(normal_probability)
        weather = _clip(weather_probability)
        fault = _clip(fault_probability)
        total = normal + weather + fault
        if total <= 1e-12:
            normal, weather, fault = 1.0, 0.0, 0.0
        else:
            normal, weather, fault = normal / total, weather / total, fault / total

        agreement = _clip(neighbour_agreement)
        extent = _clip(regional_extent)
        consistency = _clip(sensor_consistency)
        weather_gate = (
            int(neighbour_station_count) >= self.config.minimum_neighbours
            and agreement >= self.config.minimum_neighbour_agreement
            and extent >= self.config.minimum_regional_extent
            and consistency >= self.config.minimum_sensor_consistency
            and not hard_fault
            and not communication_fault
        )
        spatial_coherence = agreement * extent * consistency if weather_gate else 0.0

        # Weather must earn support independently.  Unsupported weather mass is
        # reassigned between normal and fault in proportion to their evidence.
        weather_evidence = weather * (0.30 + 0.70 * spatial_coherence) if weather_gate else 0.0
        isolation = _clip(1.0 - agreement if station_isolation is None else station_isolation)
        fault_evidence = fault * (0.80 + 0.20 * isolation)
        fault_evidence = max(fault_evidence, _clip(drift_score) * 0.85)
        if hard_fault or communication_fault:
            fault_evidence = max(fault_evidence, self.config.hard_fault_floor)
            weather_evidence = 0.0
        normal_evidence = normal * max(0.15, 1.0 - 0.55 * max(fault_evidence, weather_evidence))
        if not weather_gate:
            residual = weather
            denominator = normal + fault
            if denominator <= 1e-12:
                normal_evidence += residual
            else:
                normal_evidence += residual * normal / denominator
                fault_evidence += residual * fault / denominator

        denominator = normal_evidence + weather_evidence + fault_evidence
        if denominator <= 1e-12:
            normal_score, weather_score, fault_score = 1.0, 0.0, 0.0
        else:
            normal_score = normal_evidence / denominator
            weather_score = weather_evidence / denominator
            fault_score = fault_evidence / denominator

        scores = {
            "normal": normal_score,
            "genuine_weather": weather_score,
            "sensor_fault": fault_score,
        }
        state = max(scores, key=scores.get)
        confidence = float(scores[state])
        if confidence < self.config.minimum_decision_confidence:
            state = "advisory"

        if hard_fault or communication_fault:
            explanation = "Deterministic physical or transport evidence forces the fault path; weather veto is disabled."
        elif state == "genuine_weather":
            explanation = (
                f"Regional weather is supported by {int(neighbour_station_count)} recent neighbours, "
                f"agreement {agreement:.2f}, regional extent {extent:.2f}, and sensor consistency {consistency:.2f}."
            )
        elif not weather_gate and weather > 0.0:
            explanation = "Weather probability was not accepted because independent spatial-coherence requirements were not met."
        elif state == "sensor_fault":
            explanation = f"Station-isolated fault evidence dominates after spatial consistency checks; isolation={isolation:.2f}."
        else:
            explanation = "No class has sufficient causal evidence for an automatic fault or regional-weather decision."
        return TriageResult(
            state=state,
            normal_probability=float(normal_score),
            weather_probability=float(weather_score),
            fault_probability=float(fault_score),
            confidence=confidence,
            weather_gate_supported=weather_gate,
            spatial_coherence=float(spatial_coherence),
            explanation=explanation,
        )

"""Incident-level hierarchical probable-root diagnosis with abstention."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


COMMUNICATION = {"dropout", "duplicate_packet", "timestamp_error", "communication_corruption"}
ABRUPT = {"spike", "sudden_drop", "unit_error", "scaling_error"}
PERSISTENT = {"bias", "drift", "frozen_sensor", "noise"}
STATION = {"multi_sensor_failure", "multi_sensor_freeze", "power_failure"}
DETERMINISTIC_CODE_MAP = {
    "COMMUNICATION_GAP": "dropout",
    "DUPLICATE_PACKET": "duplicate_packet",
    "DUPLICATE_TIMESTAMP": "duplicate_packet",
    "TIMESTAMP_DISORDER": "timestamp_error",
    "OUT_OF_ORDER_TIMESTAMP": "timestamp_error",
    "UNIT_ERROR": "unit_error",
    "SCALING_ERROR": "scaling_error",
    "MULTI_SENSOR_FREEZE": "multi_sensor_freeze",
    "COMMUNICATION_CORRUPTION": "communication_corruption",
}


def broad_family(label: str) -> str:
    if label in COMMUNICATION:
        return "communication_data_order"
    if label in ABRUPT:
        return "abrupt_sensor_fault"
    if label in PERSISTENT:
        return "persistent_sensor_degradation"
    if label in STATION:
        return "multi_sensor_station_fault"
    return "unknown_fault"


@dataclass(frozen=True)
class DiagnosticEvidence:
    root_probabilities: Mapping[str, float] = field(default_factory=dict)
    deterministic_codes: tuple[str, ...] = ()
    affected_sensors: tuple[str, ...] = ()
    weight: float = 1.0
    drift_score: float = 0.0
    frozen_score: float = 0.0
    noise_score: float = 0.0
    bias_score: float = 0.0


@dataclass(frozen=True)
class IncidentDiagnosis:
    broad_family: str
    probable_root_cause: str
    confidence: float
    accepted: bool
    affected_sensors: tuple[str, ...]
    evidence_rows: int
    explanation: str


def diagnose_incident(
    rows: Sequence[DiagnosticEvidence],
    broad_threshold: float = 0.55,
    subtype_threshold: float = 0.55,
) -> IncidentDiagnosis:
    if not rows:
        return IncidentDiagnosis("unknown_fault", "unknown_fault", 0.0, False, (), 0, "No diagnostic evidence was available.")

    deterministic_votes: dict[str, float] = {}
    probabilities: dict[str, float] = {}
    sensors: set[str] = set()
    total_weight = 0.0
    for row in rows:
        weight = max(float(row.weight), 1e-6)
        total_weight += weight
        sensors.update(row.affected_sensors)
        for code in row.deterministic_codes:
            label = DETERMINISTIC_CODE_MAP.get(code.upper())
            if label:
                deterministic_votes[label] = deterministic_votes.get(label, 0.0) + weight
        for label, value in row.root_probabilities.items():
            probabilities[str(label)] = probabilities.get(str(label), 0.0) + weight * max(0.0, float(value))
        probabilities["drift"] = probabilities.get("drift", 0.0) + weight * max(0.0, float(row.drift_score))
        probabilities["frozen_sensor"] = probabilities.get("frozen_sensor", 0.0) + weight * max(0.0, float(row.frozen_score))
        probabilities["noise"] = probabilities.get("noise", 0.0) + weight * max(0.0, float(row.noise_score))
        probabilities["bias"] = probabilities.get("bias", 0.0) + weight * max(0.0, float(row.bias_score))

    if deterministic_votes:
        label = max(deterministic_votes, key=deterministic_votes.get)
        confidence = min(1.0, deterministic_votes[label] / max(total_weight, 1e-6))
        confidence = max(confidence, 0.99)
        return IncidentDiagnosis(
            broad_family(label), label, confidence, True, tuple(sorted(sensors)), len(rows),
            f"Deterministic transport/physical evidence selected {label}; learned subtype votes were secondary.",
        )

    total_probability = sum(probabilities.values())
    if total_probability <= 1e-12:
        return IncidentDiagnosis(
            "unknown_fault", "unknown_fault", 0.0, False, tuple(sorted(sensors)), len(rows),
            "Root-cause specialists supplied no usable probability mass.",
        )
    probabilities = {label: value / total_probability for label, value in probabilities.items()}
    family_scores: dict[str, float] = {}
    for label, value in probabilities.items():
        family = broad_family(label)
        family_scores[family] = family_scores.get(family, 0.0) + value
    family = max(family_scores, key=family_scores.get)
    family_confidence = family_scores[family]
    compatible = {label: value for label, value in probabilities.items() if broad_family(label) == family}
    label = max(compatible, key=compatible.get) if compatible else "unknown_fault"
    conditional = 0.0 if not compatible else compatible[label] / max(family_confidence, 1e-12)
    confidence = min(family_confidence, conditional)
    accepted = family != "unknown_fault" and family_confidence >= broad_threshold and conditional >= subtype_threshold
    probable = label if accepted else "unknown_fault"
    return IncidentDiagnosis(
        family if accepted else "unknown_fault", probable, float(confidence), accepted,
        tuple(sorted(sensors)), len(rows),
        f"Incident aggregation selected family={family} ({family_confidence:.3f}) and subtype={label} "
        f"(conditional confidence {conditional:.3f}); accepted={accepted}.",
    )

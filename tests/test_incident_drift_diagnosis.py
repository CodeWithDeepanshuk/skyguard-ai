from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.incidents import (  # noqa: E402
    DiagnosticEvidence, DriftConfig, DriftEvidence, DriftStateMachine, diagnose_incident,
)


class DriftAndDiagnosisTests(unittest.TestCase):
    def test_sustained_slope_and_cusum_confirm_drift(self) -> None:
        machine = DriftStateMachine(DriftConfig(
            minimum_span_hours=2.0, minimum_points=3, confirm_k=2, confirm_n=3,
            slope_z_per_hour=.10, cusum_threshold=3.0, monotonic_run_threshold=2,
        ))
        states = []
        for hour in range(5):
            result = machine.update(DriftEvidence(
                station_id="A", sensor="pressure", timestamp_utc=f"2023-01-01T0{hour}:00:00Z",
                neighbour_residual_z=.3 * hour, cusum_positive=1.8 * hour,
                cusum_negative=0.0, monotonic_run=hour + 1, neighbour_count=3,
            ))
            states.append(result.state)
        self.assertIn("drift_confirmed", states)
        self.assertEqual(states[-1], "drift_active")

    def test_out_of_order_drift_row_is_ignored(self) -> None:
        machine = DriftStateMachine()
        machine.update(DriftEvidence("A", "temperature", "2023-01-01T02:00:00Z", 0, 0, 0, 0, 2))
        result = machine.update(DriftEvidence("A", "temperature", "2023-01-01T01:00:00Z", 5, 8, 0, 5, 2))
        self.assertEqual(result.state, "ignored_out_of_order")

    def test_deterministic_communication_diagnosis_has_priority(self) -> None:
        result = diagnose_incident([
            DiagnosticEvidence(
                root_probabilities={"drift": .9, "duplicate_packet": .1},
                deterministic_codes=("DUPLICATE_PACKET",), affected_sensors=("communication",),
            )
        ])
        self.assertEqual(result.probable_root_cause, "duplicate_packet")
        self.assertEqual(result.broad_family, "communication_data_order")
        self.assertTrue(result.accepted)

    def test_persistent_specialist_votes_are_aggregated_per_incident(self) -> None:
        rows = [
            DiagnosticEvidence({"drift": .75, "bias": .20, "spike": .05}, affected_sensors=("pressure",), weight=.8),
            DiagnosticEvidence({"drift": .70, "bias": .25, "spike": .05}, affected_sensors=("pressure",), weight=.9),
        ]
        result = diagnose_incident(rows, broad_threshold=.50, subtype_threshold=.50)
        self.assertEqual(result.probable_root_cause, "drift")
        self.assertEqual(result.broad_family, "persistent_sensor_degradation")
        self.assertTrue(result.accepted)


if __name__ == "__main__":
    unittest.main()

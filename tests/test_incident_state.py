from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.incidents import IncidentConfig, IncidentEvidence, IncidentStateEngine  # noqa: E402


def evidence(
    minute: int,
    *,
    fault: float = 0.05,
    weather: float = 0.05,
    normal: float = 0.90,
    neighbours: int = 0,
    agreement: float = 0.0,
    extent: float = 0.0,
    consistency: float = 0.0,
    hard: tuple[str, ...] = (),
    drift: float = 0.0,
) -> IncidentEvidence:
    return IncidentEvidence(
        station_id="A", timestamp_utc=f"2023-01-01T00:{minute:02d}:00Z",
        fault_probability=fault, weather_probability=weather, normal_probability=normal,
        affected_sensors=("pressure",), hard_fault_codes=hard,
        neighbour_station_count=neighbours, neighbour_agreement=agreement,
        regional_extent=extent, sensor_consistency=consistency, drift_score=drift,
    )


class IncidentStateTests(unittest.TestCase):
    def test_k_of_n_confirms_weak_persistent_fault(self) -> None:
        engine = IncidentStateEngine(IncidentConfig(confirm_k=3, confirm_n=5))
        decisions = [engine.process(evidence(index * 10, fault=.48, normal=.47)) for index in range(3)]
        self.assertEqual(decisions[0].state, "candidate_fault")
        self.assertEqual(decisions[1].state, "candidate_fault")
        self.assertEqual(decisions[2].state, "confirmed_fault")
        self.assertEqual(decisions[2].lifecycle, "opened")

    def test_hard_fault_uses_instant_path(self) -> None:
        decision = IncidentStateEngine().process(evidence(0, fault=.20, normal=.70, hard=("UNIT_ERROR",)))
        self.assertEqual(decision.state, "confirmed_fault")
        self.assertEqual(decision.lifecycle, "opened")
        self.assertEqual(decision.severity, "critical")

    def test_coherent_regional_event_is_not_accumulated_as_fault(self) -> None:
        engine = IncidentStateEngine()
        decision = engine.process(evidence(
            0, fault=.20, weather=.72, normal=.08, neighbours=4,
            agreement=.90, extent=.85, consistency=.95,
        ))
        self.assertEqual(decision.state, "genuine_weather")
        self.assertTrue(decision.weather_gate_supported)
        self.assertFalse(decision.incident_id)

    def test_weather_without_neighbours_cannot_veto_fault(self) -> None:
        decision = IncidentStateEngine().process(evidence(0, fault=.40, weather=.55, normal=.05))
        self.assertNotEqual(decision.state, "genuine_weather")
        self.assertFalse(decision.weather_gate_supported)

    def test_recovery_hysteresis_closes_incident(self) -> None:
        engine = IncidentStateEngine(IncidentConfig(recovery_points=2))
        opened = engine.process(evidence(0, fault=.99, normal=.005))
        first = engine.process(evidence(10))
        second = engine.process(evidence(20))
        self.assertEqual(opened.lifecycle, "opened")
        self.assertEqual(first.state, "confirmed_fault")
        self.assertEqual(second.lifecycle, "closed")
        self.assertEqual(second.state, "normal")

    def test_future_rows_do_not_change_prefix_decisions(self) -> None:
        first = IncidentStateEngine(IncidentConfig(confirm_k=2, confirm_n=3))
        prefix = [evidence(0, fault=.45, normal=.50), evidence(10, fault=.45, normal=.50)]
        expected = [first.process(item) for item in prefix]
        first.process(evidence(20, fault=.99, normal=.005))
        second = IncidentStateEngine(IncidentConfig(confirm_k=2, confirm_n=3))
        actual = [second.process(item) for item in prefix]
        self.assertEqual([(x.state, x.lifecycle, x.incident_id) for x in expected],
                         [(x.state, x.lifecycle, x.incident_id) for x in actual])


if __name__ == "__main__":
    unittest.main()

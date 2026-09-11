from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.correction.estimators import correction_candidates, infer_affected_sensors  # noqa: E402
from skyguard.correction.incidents import SensorHealthTracker  # noqa: E402
from skyguard.correction.policy import correct_value, fit_correction_policy  # noqa: E402


class CorrectionTests(unittest.TestCase):
    def test_candidates_are_causal_and_reject_impossible_values(self) -> None:
        row = {
            "temperature_rolling_median_24h": "30", "temperature_ewma_prior": "31",
            "temperature_lag1": "200", "neighbor_temperature_median": "29",
            "neighbor_temperature_weighted_mean": "29.5",
        }
        candidates = correction_candidates(row, "temperature")
        self.assertNotIn("lag1", candidates)
        self.assertEqual(candidates["temporal_median"], 30.0)

    def test_multi_sensor_fault_selects_all_sensors(self) -> None:
        self.assertEqual(
            infer_affected_sensors({}, "multi_sensor_failure"),
            ["temperature", "pressure", "humidity"],
        )

    def test_evidence_remains_finite_when_mad_is_missing(self) -> None:
        from skyguard.correction.estimators import sensor_evidence
        evidence = sensor_evidence({"temperature_ewma_residual": "2", "temperature_rolling_mad_24h": ""}, "temperature")
        self.assertEqual(evidence["ewma"], 4.0)

    def test_uncertainty_expands_when_candidates_disagree(self) -> None:
        from skyguard.correction.estimators import uncertainty_scale
        stable = {
            "humidity_rolling_median_24h": "50", "humidity_ewma_prior": "51",
            "neighbor_humidity_median": "50", "neighbor_humidity_weighted_mean": "51",
        }
        disagreement = dict(stable, neighbor_humidity_median="90")
        self.assertGreater(uncertainty_scale(disagreement, "humidity"), uncertainty_scale(stable, "humidity"))

    def test_regional_weather_is_not_a_repair_target(self) -> None:
        from data.run_safe_repair import changed_target
        frame = pd.DataFrame([{
            "anomaly_sensor": "temperature", "temperature_value": 40.0,
            "original_temperature_c": 30.0, "is_anomaly": 0,
            "anomaly_type": "regional_temperature_event",
        }])
        self.assertEqual(int(changed_target(frame, "temperature")[0]), 0)

    def test_validation_policy_selects_lowest_mae_method(self) -> None:
        rows = []
        for _ in range(10):
            rows.append({
                "anomaly_type": "bias", "anomaly_sensor": "temperature", "available_to_detector": "1",
                "original_temperature_c": "30", "temperature_rolling_median_24h": "30.1",
                "temperature_ewma_prior": "35", "temperature_lag1": "35",
                "neighbor_temperature_median": "31", "neighbor_temperature_weighted_mean": "31",
            })
        policy = fit_correction_policy(rows)
        self.assertEqual(policy["sensors"]["temperature"]["bias"]["method"], "temporal_median")
        corrected = correct_value(rows[0], "temperature", "bias", policy)
        self.assertAlmostEqual(corrected["estimate"], 30.1)

    def test_health_score_decreases_after_incident(self) -> None:
        tracker = SensorHealthTracker()
        score = tracker.update("A", "temperature", "2024-01-01T00:00:00Z", "high", 0.9)
        self.assertLess(score, 100.0)
        self.assertEqual(tracker.snapshot("A", "temperature")["incident_count"], 1)

    def test_health_tracker_forecasts_repeated_degradation(self) -> None:
        tracker = SensorHealthTracker()
        for day in (1, 5, 9, 13):
            tracker.update("A", "pressure", f"2024-01-{day:02d}T00:00:00Z", "high", 0.95)
        snapshot = tracker.snapshot("A", "pressure")
        self.assertEqual(snapshot["health_trend"], "degrading")
        self.assertLess(snapshot["degradation_slope_points_per_day"], 0)
        self.assertLess(snapshot["projected_health_7d"], snapshot["health_score"])
        self.assertIsNotNone(snapshot["maintenance_horizon_days"])
        self.assertIn("heuristic", snapshot["forecast_method"])


if __name__ == "__main__":
    unittest.main()

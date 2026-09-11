from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.evaluation.incident_metrics import calibration_metrics, incident_metrics  # noqa: E402


class IncidentMetricTests(unittest.TestCase):
    def test_one_to_one_incident_matching_and_latency(self) -> None:
        truth = pd.DataFrame([
            {"station_id": "A", "start_utc": "2023-01-01T00:00:00Z", "end_utc": "2023-01-01T02:00:00Z", "root_cause": "drift"},
            {"station_id": "A", "start_utc": "2023-01-02T00:00:00Z", "end_utc": "2023-01-02T01:00:00Z", "root_cause": "spike"},
        ])
        predictions = pd.DataFrame([
            {"station_id": "A", "start_utc": "2023-01-01T00:30:00Z", "end_utc": "2023-01-01T02:10:00Z", "first_alert_utc": "2023-01-01T00:40:00Z", "root_cause": "drift"},
            {"station_id": "A", "start_utc": "2023-01-03T00:00:00Z", "end_utc": "2023-01-03T01:00:00Z", "first_alert_utc": "2023-01-03T00:00:00Z", "root_cause": "spike"},
        ])
        result = incident_metrics(truth, predictions, station_days=10)
        self.assertEqual(result["tp"], 1)
        self.assertEqual(result["fp"], 1)
        self.assertEqual(result["fn"], 1)
        self.assertEqual(result["median_latency_minutes"], 40.0)
        self.assertEqual(result["matched_root_accuracy"], 1.0)

    def test_calibration_metrics_are_zero_for_perfect_predictions(self) -> None:
        result = calibration_metrics(np.array([0, 0, 1, 1]), np.array([0, 0, 1, 1]), bins=4)
        self.assertEqual(result["brier_score"], 0.0)
        self.assertEqual(result["expected_calibration_error"], 0.0)


if __name__ == "__main__":
    unittest.main()

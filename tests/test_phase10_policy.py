from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.models.phase10 import aggregate_incident_roots, causal_persistence_scores, constrained_threshold  # noqa: E402


class Phase10PolicyTests(unittest.TestCase):
    def test_persistence_is_causal_and_station_local(self) -> None:
        frame = pd.DataFrame({
            "station_id": ["A", "A", "B"],
            "emitted_timestamp_utc": ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z", "2024-01-01T01:00:00Z"],
        })
        result = causal_persistence_scores(frame, np.array([0.9, 0.1, 0.1]), 0.8)
        self.assertAlmostEqual(result[1], 0.72)
        self.assertAlmostEqual(result[2], 0.1)

    def test_duplicate_packet_has_deterministic_priority(self) -> None:
        frame = pd.DataFrame({
            "station_id": ["A"], "emitted_timestamp_utc": ["2024-01-01T00:00:00Z"],
            "time_since_previous_minutes": [0.0],
        })
        classes = np.array(["drift", "duplicate_packet"])
        labels, confidence, incidents = aggregate_incident_roots(
            frame, np.array([True]), np.array([0.8]), np.array([[0.9, 0.1]]), classes,
        )
        self.assertEqual(labels[0], "duplicate_packet")
        self.assertEqual(confidence[0], 1.0)
        self.assertTrue(incidents[0])

    def test_threshold_obeys_false_alarm_constraint(self) -> None:
        frame = pd.DataFrame({
            "station_id": ["A"] * 4,
            "emitted_timestamp_utc": [f"2024-01-0{i + 1}T00:00:00Z" for i in range(4)],
        })
        result = constrained_threshold(
            np.array([1, 1, 0, 0]), np.array([0.9, 0.8, 0.7, 0.1]), frame,
            np.array([0, 0, 0, 0]), false_alarm_limit=0.0,
        )
        self.assertGreater(result["threshold"], 0.7)
        self.assertEqual(result["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()

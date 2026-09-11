from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.evaluation.metrics import choose_threshold, episode_metrics, point_metrics  # noqa: E402


class MetricTests(unittest.TestCase):
    def test_threshold_is_selected_from_validation_scores(self) -> None:
        result = choose_threshold(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.9]))
        self.assertGreater(result["threshold"], 0.2)
        self.assertEqual(result["f1"], 1.0)

    def test_point_metrics_count_false_alarms(self) -> None:
        result = point_metrics(
            np.array([0, 1]), np.array([0.8, 0.9]), 0.85,
            ["A", "A"], ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"], np.array([0, 0]),
        )
        self.assertEqual(result["tp"], 1)
        self.assertEqual(result["fp"], 0)

    def test_episode_latency_uses_first_detection(self) -> None:
        result = episode_metrics(
            np.array([1, 1]), np.array([False, True]), ["E1", "E1"],
            ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"], ["drift", "drift"],
        )
        self.assertEqual(result["detected_episodes"], 1)
        self.assertEqual(result["median_detection_latency_minutes"], 60.0)


if __name__ == "__main__":
    unittest.main()

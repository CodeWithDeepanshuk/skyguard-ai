from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.evaluation.classification import (  # noqa: E402
    choose_selective_threshold, choose_threshold_for_precision, episode_balanced_weights,
    expected_calibration_error,
)
from skyguard.models.classification import CLASSIFIER_FEATURES  # noqa: E402


class ClassificationUtilityTests(unittest.TestCase):
    def test_absolute_calendar_shortcuts_are_excluded(self) -> None:
        self.assertNotIn("day_of_year_sin", CLASSIFIER_FEATURES)
        self.assertNotIn("hour_cos", CLASSIFIER_FEATURES)

    def test_episode_weights_equalize_long_and_short_episodes(self) -> None:
        labels = np.array(["fault", "fault", "fault", "fault"])
        episodes = np.array(["long", "long", "long", "short"])
        weights = episode_balanced_weights(labels, episodes)
        self.assertAlmostEqual(float(np.sum(weights[:3])), float(weights[3]))

    def test_calibration_error_is_zero_for_correct_certainty(self) -> None:
        probabilities = np.array([[1.0, 0.0], [0.0, 1.0]])
        labels = np.array(["a", "b"])
        self.assertEqual(expected_calibration_error(probabilities, labels, np.array(["a", "b"])), 0.0)

    def test_selective_threshold_can_remove_uncertain_error(self) -> None:
        labels = np.array(["a", "b", "a", "b"])
        predictions = np.array(["a", "b", "a", "a"])
        confidence = np.array([0.99, 0.95, 0.90, 0.40])
        policy = choose_selective_threshold(labels, predictions, confidence, target_accuracy=1.0)
        self.assertGreater(policy["threshold"], 0.40)
        self.assertEqual(policy["accepted_accuracy"], 1.0)

    def test_precision_target_threshold_prefers_recall(self) -> None:
        labels = np.array([0, 0, 1, 1])
        scores = np.array([0.1, 0.3, 0.8, 0.9])
        policy = choose_threshold_for_precision(labels, scores, 0.95)
        self.assertEqual(policy["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()

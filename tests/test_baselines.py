from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.models.baselines import combined_score, ewma_score, hampel_score, neighbor_score, qc_rule_score  # noqa: E402


class BaselineScoreTests(unittest.TestCase):
    def test_hampel_uses_largest_sensor_score(self) -> None:
        row = {"temperature_robust_z_24h": "2", "pressure_robust_z_24h": "-7", "humidity_robust_z_24h": ""}
        self.assertEqual(hampel_score(row), 7.0)

    def test_ewma_has_sensor_specific_robust_scale(self) -> None:
        row = {"temperature_ewma_residual": "3", "temperature_rolling_mad_24h": "1"}
        self.assertAlmostEqual(ewma_score(row), 3 / 1.4826)

    def test_neighbor_score_needs_available_neighbor(self) -> None:
        unavailable = {"neighbor_temperature_count": "0", "neighbor_temperature_residual": "30"}
        available = {"neighbor_temperature_count": "2", "neighbor_temperature_residual": "6"}
        self.assertEqual(neighbor_score(unavailable), 0.0)
        self.assertEqual(neighbor_score(available), 2.0)

    def test_physical_violation_is_high_score(self) -> None:
        self.assertGreaterEqual(qc_rule_score({"humidity_value": "140"}), 4.0)

    def test_combined_catches_large_hampel_score(self) -> None:
        row = {"temperature_robust_z_24h": "12"}
        self.assertGreaterEqual(combined_score(row), 4.0)


if __name__ == "__main__":
    unittest.main()

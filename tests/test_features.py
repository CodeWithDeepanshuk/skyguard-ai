from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.features.builder import FeatureBuilder  # noqa: E402
from skyguard.features.contracts import AUDIT_COLUMNS, LABEL_COLUMNS, MODEL_FEATURE_COLUMNS, FeatureConfig  # noqa: E402
from skyguard.features.neighbors import NeighborIndex  # noqa: E402
from skyguard.features.temporal import TemporalFeatureBuilder  # noqa: E402


def row(station: str, timestamp: str, temperature: float, action: str = "emit") -> dict[str, str]:
    return {
        "station_id": station,
        "timestamp_utc": timestamp,
        "split": "test",
        "cluster": "cluster",
        "evaluation_role": "development",
        "temperature_c": str(temperature),
        "pressure_hpa": "1000.0",
        "relative_humidity_pct": "60.0",
        "dew_point_c": "16.0",
        "stream_action": action,
        "timestamp_offset_seconds": "0",
        "is_anomaly": "0",
        "is_weather_event": "0",
        "anomaly_type": "normal",
        "anomaly_sensor": "",
        "anomaly_severity": "",
        "episode_id": "",
        "label_category": "normal",
        "label_source": "none",
        "injection_seed": "",
        "original_timestamp_utc": timestamp,
        "original_temperature_c": str(temperature),
        "original_pressure_hpa": "1000.0",
        "original_relative_humidity_pct": "60.0",
    }


STATIONS = {
    "A": {"cluster": "cluster", "latitude": "10.0", "longitude": "77.0"},
    "B": {"cluster": "cluster", "latitude": "10.1", "longitude": "77.1"},
    "C": {"cluster": "cluster", "latitude": "10.2", "longitude": "77.2"},
}


class FeatureTests(unittest.TestCase):
    def test_rolling_features_exclude_current_value(self) -> None:
        temporal = TemporalFeatureBuilder({"A": 60.0})
        first = temporal.transform(row("A", "2024-01-01T00:00:00Z", 10.0))
        second = temporal.transform(row("A", "2024-01-01T01:00:00Z", 30.0))
        self.assertEqual(first["temperature_rolling_count_24h"], 0)
        self.assertEqual(second["temperature_rolling_median_24h"], 10.0)
        self.assertEqual(second["temperature_lag1"], 10.0)

    def test_dropped_row_does_not_update_state(self) -> None:
        temporal = TemporalFeatureBuilder({"A": 60.0})
        temporal.transform(row("A", "2024-01-01T00:00:00Z", 10.0))
        dropped = temporal.transform(row("A", "2024-01-01T01:00:00Z", 99.0, "drop"))
        after = temporal.transform(row("A", "2024-01-01T02:00:00Z", 20.0))
        self.assertEqual(dropped["available_to_detector"], "0")
        self.assertEqual(after["temperature_lag1"], 10.0)

    def test_neighbor_alignment_never_uses_future_value(self) -> None:
        context = [
            row("B", "2024-01-01T00:00:00Z", 20.0),
            row("B", "2024-01-01T02:00:00Z", 100.0),
        ]
        neighbors = NeighborIndex(context, STATIONS, FeatureConfig(neighbor_tolerance_minutes=180.0))
        features = neighbors.features(row("A", "2024-01-01T01:00:00Z", 25.0))
        self.assertEqual(features["neighbor_temperature_median"], 20.0)
        self.assertGreaterEqual(features["neighbor_min_age_minutes"], 0.0)

    def test_future_only_neighbor_is_not_available(self) -> None:
        context = [row("B", "2024-01-01T02:00:00Z", 100.0)]
        neighbors = NeighborIndex(context, STATIONS)
        features = neighbors.features(row("A", "2024-01-01T01:00:00Z", 25.0))
        self.assertEqual(features["neighbor_station_count"], 0)

    def test_model_features_exclude_labels_and_audit_fields(self) -> None:
        forbidden = set(LABEL_COLUMNS + AUDIT_COLUMNS)
        self.assertEqual(set(MODEL_FEATURE_COLUMNS) & forbidden, set())

    def test_combined_builder_produces_complete_row(self) -> None:
        source = row("A", "2024-01-01T01:00:00Z", 25.0)
        builder = FeatureBuilder(
            TemporalFeatureBuilder({"A": 60.0}),
            NeighborIndex([row("B", "2024-01-01T00:00:00Z", 20.0)], STATIONS),
        )
        output = builder.transform(source)
        self.assertTrue(MODEL_FEATURE_COLUMNS)
        self.assertTrue(all(column in output for column in MODEL_FEATURE_COLUMNS))
        self.assertEqual(output["is_anomaly"], "0")


if __name__ == "__main__":
    unittest.main()

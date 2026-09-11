from __future__ import annotations

import copy
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.faults.injector import FaultInjector  # noqa: E402
from skyguard.faults.models import FAULT_TYPES  # noqa: E402


def sample_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    start = datetime(2024, 1, 1)
    for station_number in range(3):
        for offset in range(500):
            timestamp = start + timedelta(hours=offset)
            rows.append({
                "station_id": f"TEST{station_number}",
                "timestamp_utc": timestamp.isoformat(timespec="seconds") + "Z",
                "year": "2024",
                "cluster": "test_cluster",
                "evaluation_role": "development",
                "temperature_c": f"{25.0 + station_number + (offset % 24) / 20.0:.4f}",
                "temperature_quality": "1",
                "pressure_hpa": f"{1005.0 + (offset % 12) / 10.0:.4f}",
                "pressure_quality": "1",
                "relative_humidity_pct": f"{60.0 + (offset % 10):.4f}",
                "dew_point_c": "16.0000",
                "dew_point_quality": "1",
                "pressure_source": "slp",
            })
    return rows


class FaultInjectorTests(unittest.TestCase):
    def test_suite_contains_every_fault_type_and_weather_event(self) -> None:
        injector = FaultInjector(sample_rows(), "test", 12345)
        episodes = injector.inject_suite(1, 1)
        fault_types = {episode.anomaly_type for episode in episodes if episode.label_category == "sensor_fault"}
        self.assertEqual(fault_types, set(FAULT_TYPES))
        self.assertEqual(sum(episode.label_category == "genuine_weather_scenario" for episode in episodes), 1)
        self.assertTrue(any(row["is_anomaly"] == "1" for row in injector.rows))
        self.assertTrue(any(row["is_weather_event"] == "1" for row in injector.rows))

    def test_original_values_are_preserved(self) -> None:
        rows = sample_rows()
        injector = FaultInjector(rows, "test", 19)
        injector.inject_suite(1, 0)
        for row in injector.rows:
            self.assertIn("original_temperature_c", row)
            self.assertIn("original_pressure_hpa", row)
            self.assertIn("original_relative_humidity_pct", row)
            self.assertIn("original_timestamp_utc", row)

    def test_same_seed_is_deterministic(self) -> None:
        first = FaultInjector(copy.deepcopy(sample_rows()), "test", 26073)
        second = FaultInjector(copy.deepcopy(sample_rows()), "test", 26073)
        first.inject_suite(1, 1)
        second.inject_suite(1, 1)
        first_labels = [(row["episode_id"], row["anomaly_type"], row["temperature_c"], row["stream_action"]) for row in first.rows]
        second_labels = [(row["episode_id"], row["anomaly_type"], row["temperature_c"], row["stream_action"]) for row in second.rows]
        self.assertEqual(first_labels, second_labels)

    def test_rows_belong_to_at_most_one_episode(self) -> None:
        injector = FaultInjector(sample_rows(), "test", 77)
        injector.inject_suite(2, 2)
        labelled = [row for row in injector.rows if row["episode_id"]]
        self.assertEqual(len(labelled), len({(row["station_id"], row["timestamp_utc"]) for row in labelled}))


if __name__ == "__main__":
    unittest.main()

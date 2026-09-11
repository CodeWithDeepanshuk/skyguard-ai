from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.features.phase10 import (  # noqa: E402
    PHASE10_FEATURES, RollingSlope, add_phase10_features, assert_phase10_compliance, fit_climatology,
)


class Phase10FeatureTests(unittest.TestCase):
    def test_contract_excludes_dew_point_and_calendar_shortcuts(self) -> None:
        assert_phase10_compliance()
        self.assertFalse(any("dew" in value for value in PHASE10_FEATURES))
        self.assertNotIn("hour_sin", PHASE10_FEATURES)

    def test_rolling_slope_detects_linear_change(self) -> None:
        state = RollingSlope(6)
        values = [state.push(float(hour), 2.0 * hour + 1.0) for hour in range(5)]
        self.assertAlmostEqual(values[-1], 2.0, places=6)

    def test_features_are_causal_and_add_trend(self) -> None:
        rows = []
        for hour, temperature in enumerate((10.0, 11.0, 12.0, 13.0)):
            row = {
                "station_id": "A", "cluster": "X", "emitted_timestamp_utc": f"2022-01-01T0{hour}:00:00Z",
                "is_anomaly": 0, "is_weather_event": 0,
                "temperature_value": temperature, "pressure_value": 1000.0, "humidity_value": 50.0,
            }
            for sensor in ("temperature", "pressure", "humidity"):
                row[f"{sensor}_robust_z_24h"] = 0.0
                row[f"neighbor_{sensor}_residual"] = 0.0
                row[f"neighbor_{sensor}_mad"] = 1.0
                row[f"neighbor_{sensor}_agreement_fraction"] = 1.0
            rows.append(row)
        frame = pd.DataFrame(rows)
        profiles = fit_climatology(frame)
        enhanced = add_phase10_features(frame.iloc[:3], profiles)
        self.assertAlmostEqual(enhanced.iloc[-1]["temperature_slope_3h"], 1.0, places=6)
        self.assertEqual(enhanced.iloc[-1]["regional_agreeing_sensor_count"], 3.0)

    def test_corrupted_packet_timestamp_cannot_reorder_arrival_state(self) -> None:
        rows = []
        for order, (arrival, emitted, temperature) in enumerate((
            ("2022-01-01T00:00:00Z", "2022-01-01T00:00:00Z", 10.0),
            ("2022-01-01T01:00:00Z", "2022-01-01T05:00:00Z", 11.0),
            ("2022-01-01T02:00:00Z", "2022-01-01T02:00:00Z", 12.0),
        )):
            row = {
                "station_id": "A", "cluster": "X", "emitted_timestamp_utc": emitted,
                "causal_arrival_timestamp_utc": arrival, "stream_order": order,
                "is_anomaly": 0, "is_weather_event": 0,
                "temperature_value": temperature, "pressure_value": 1000.0,
                "humidity_value": 50.0,
            }
            for sensor in ("temperature", "pressure", "humidity"):
                row[f"{sensor}_robust_z_24h"] = 0.0
                row[f"neighbor_{sensor}_residual"] = 0.0
                row[f"neighbor_{sensor}_mad"] = 1.0
                row[f"neighbor_{sensor}_agreement_fraction"] = 1.0
            rows.append(row)
        frame = pd.DataFrame(rows)
        profiles = fit_climatology(frame)
        enhanced = add_phase10_features(frame, profiles)
        self.assertAlmostEqual(enhanced.iloc[2]["temperature_slope_3h"], 1.0, places=6)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.quality.engine import QualityControlEngine  # noqa: E402
from skyguard.quality.models import Observation, QualityThresholds  # noqa: E402


def observation(
    hour: float,
    temperature: float | None = 25.0,
    pressure: float | None = 1005.0,
    humidity: float | None = 60.0,
    dew_point: float | None = 16.7,
) -> Observation:
    return Observation(
        station_id="TEST001",
        timestamp=datetime(2024, 1, 1) + timedelta(hours=hour),
        temperature_c=temperature,
        pressure_hpa=pressure,
        relative_humidity_pct=humidity,
        dew_point_c=dew_point,
        temperature_quality="1",
        pressure_quality="1",
        pressure_source="slp",
        dew_point_quality="1",
    )


class QualityEngineTests(unittest.TestCase):
    def test_healthy_observation_has_no_alert(self) -> None:
        engine = QualityControlEngine({"TEST001": 60.0})
        self.assertEqual(engine.process(observation(0)), [])

    def test_missing_and_physical_bounds(self) -> None:
        engine = QualityControlEngine()
        alerts = engine.process(observation(0, temperature=None, pressure=1200.0))
        self.assertIn("MISSING_VALUE", {alert.rule_code for alert in alerts})
        self.assertIn("PHYSICAL_BOUNDS", {alert.rule_code for alert in alerts})

    def test_duplicate_and_out_of_order_timestamp(self) -> None:
        engine = QualityControlEngine()
        engine.process(observation(2))
        duplicate = engine.process(observation(2))
        older = engine.process(observation(1))
        self.assertIn("DUPLICATE_TIMESTAMP", {alert.rule_code for alert in duplicate})
        self.assertIn("OUT_OF_ORDER_TIMESTAMP", {alert.rule_code for alert in older})

    def test_communication_gap(self) -> None:
        engine = QualityControlEngine(
            {"TEST001": 60.0},
            heartbeat_sla_minutes={"TEST001": 360.0},
        )
        engine.process(observation(0))
        alerts = engine.process(observation(7))
        self.assertIn("COMMUNICATION_GAP", {alert.rule_code for alert in alerts})

    def test_gap_without_heartbeat_contract_is_advisory(self) -> None:
        engine = QualityControlEngine({"TEST001": 60.0})
        engine.process(observation(0))
        alerts = engine.process(observation(7))
        codes = {alert.rule_code for alert in alerts}
        self.assertIn("UNVERIFIED_DATA_GAP", codes)
        self.assertNotIn("COMMUNICATION_GAP", codes)

    def test_rate_of_change(self) -> None:
        engine = QualityControlEngine({"TEST001": 60.0})
        engine.process(observation(0, temperature=20.0))
        alerts = engine.process(observation(1, temperature=40.0))
        self.assertIn("RATE_OF_CHANGE", {alert.rule_code for alert in alerts})

    def test_pressure_rate_skips_source_transition(self) -> None:
        engine = QualityControlEngine({"TEST001": 60.0})
        first = observation(0, pressure=1000.0)
        second = Observation(**{**observation(1, pressure=1040.0).__dict__, "pressure_source": "ma1_altimeter"})
        engine.process(first)
        alerts = engine.process(second)
        pressure_rates = [a for a in alerts if a.rule_code == "RATE_OF_CHANGE" and a.sensor == "pressure"]
        self.assertEqual(pressure_rates, [])

    def test_frozen_sensor_emits_once_per_episode(self) -> None:
        thresholds = QualityThresholds(frozen_duration_hours=12.0, frozen_min_readings=4)
        engine = QualityControlEngine({"TEST001": 180.0}, thresholds)
        alerts = []
        for hour in (0, 3, 6, 9, 12, 15):
            alerts.extend(engine.process(observation(hour)))
        temperature_freezes = [a for a in alerts if a.rule_code == "FROZEN_SENSOR" and a.sensor == "temperature"]
        multi_freezes = [a for a in alerts if a.rule_code == "MULTI_SENSOR_FREEZE"]
        self.assertEqual(len(temperature_freezes), 1)
        self.assertEqual(len(multi_freezes), 1)

    def test_dew_point_consistency(self) -> None:
        engine = QualityControlEngine()
        alerts = engine.process(observation(0, temperature=20.0, dew_point=23.0))
        self.assertIn("DEWPOINT_ABOVE_TEMPERATURE", {alert.rule_code for alert in alerts})


if __name__ == "__main__":
    unittest.main()

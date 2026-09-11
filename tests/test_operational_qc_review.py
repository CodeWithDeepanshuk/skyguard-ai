"""Regressions for the operational-QC reference review."""
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from skyguard.quality.models import Observation
from skyguard.quality.engine import QualityControlEngine


def row(hour, **kwargs):
    base = Observation('A', datetime(2023, 1, 1) + timedelta(hours=hour),
                       25., 1000., 60., pressure_source='slp')
    return replace(base, **kwargs)


class OperationalQCReviewTests(unittest.TestCase):
    def test_statistical_qc_cannot_confirm_live_incident(self):
        from skyguard.live.metar import MetarLiveService
        soft = ('SATURATION_REVIEW', 'RATE_OF_CHANGE', 'FROZEN_SENSOR', 'SOURCE_QUALITY_FLAG')
        alerts = [dict(station_id='A', timestamp_utc='2023-01-01T00:00:00Z', rule_code=c) for c in soft]
        self.assertEqual(MetarLiveService._quality_codes(alerts), {})
        alerts.append(dict(station_id='A', timestamp_utc='2023-01-01T00:00:00Z', rule_code='NONFINITE_VALUE'))
        grouped = MetarLiveService._quality_codes(alerts)
        self.assertEqual(next(iter(grouped.values()))[0], ('NONFINITE_VALUE',))

    def test_high_altitude_pressure_is_not_sea_level(self):
        for source in ('ma1_station', 'station_pressure', ''):
            alerts = QualityControlEngine().process(row(0, pressure_hpa=650., pressure_source=source))
            self.assertFalse(any(a.rule_code == 'PHYSICAL_BOUNDS' for a in alerts))
        alerts = QualityControlEngine().process(row(0, pressure_hpa=650.))
        self.assertTrue(any(a.rule_code == 'PHYSICAL_BOUNDS' for a in alerts))

    def test_nonfinite_values_are_explicit(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            alerts = QualityControlEngine().process(row(0, temperature_c=value))
            self.assertEqual([a.rule_code for a in alerts], ['NONFINITE_VALUE'])

    def test_gap_does_not_count_as_observed_persistence(self):
        engine = QualityControlEngine({'A': 60.})
        alerts = []
        for hour in (0, 1, 2, 24):
            alerts += engine.process(row(hour))
        self.assertFalse(any(a.rule_code in ('FROZEN_SENSOR', 'MULTI_SENSOR_FREEZE') for a in alerts))

    def test_pressure_source_change_resets_freeze(self):
        engine = QualityControlEngine({'A': 180.})
        for hour in (0, 3, 6, 9):
            engine.process(row(hour))
        alerts = engine.process(row(12, pressure_source='ma1_station'))
        self.assertFalse(any(a.sensor == 'pressure' and a.rule_code == 'FROZEN_SENSOR' for a in alerts))

    def test_fog_is_review_and_other_sensor_freeze_still_detected(self):
        engine = QualityControlEngine({'A': 180.})
        alerts = []
        for hour in (0, 3, 6, 9, 12):
            alerts += engine.process(row(hour, relative_humidity_pct=100., pressure_hpa=1000.+hour/10))
        self.assertTrue(any(a.rule_code == 'SATURATION_REVIEW' for a in alerts))
        self.assertFalse(any(a.sensor == 'humidity' and a.rule_code == 'FROZEN_SENSOR' for a in alerts))
        self.assertTrue(any(a.sensor == 'temperature' and a.rule_code == 'FROZEN_SENSOR' for a in alerts))


if __name__ == '__main__':
    unittest.main()

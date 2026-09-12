from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.live.metar import (  # noqa: E402
    LIVE_INCIDENT_POLICY_MODE, LIVE_PRESENTATION_CONTRACT, MetarLiveService, relative_humidity,
)


class LiveFeedTests(unittest.TestCase):
    def test_status_ages_increase_without_refresh_or_cache_mutation(self):
        service = MetarLiveService(ROOT)
        service.payload = {"status": "cached", "is_cached": True, "source_age_minutes": 2,
                           "latest_observation_utc": "2026-09-01T10:00:00Z", "fetched_at_utc": "2026-09-01T10:05:00Z"}
        now = datetime(2026, 9, 1, 11, tzinfo=timezone.utc)
        first, second = service.status(now), service.status(now + timedelta(minutes=30))
        self.assertEqual(first["source_age_minutes"], 60)
        self.assertEqual(second["source_age_minutes"], 90)
        self.assertEqual(second["fetch_age_minutes"], 85)
        self.assertEqual(service.payload["source_age_minutes"], 2)
        self.assertEqual(first["status"], "cached")

    def test_status_missing_invalid_naive_and_future_times_are_not_fresh(self):
        service = MetarLiveService(ROOT)
        now = datetime(2026, 9, 1, 11, tzinfo=timezone.utc)
        for value in (None, "bad timestamp", "2026-09-01T10:00:00"):
            service.payload = {"latest_observation_utc": value}
            self.assertIsNone(service.status(now)["source_age_minutes"])
        service.payload = {"latest_observation_utc": "2026-09-01T12:00:00Z"}
        self.assertEqual(service.status(now)["source_age_minutes"], -60)
        self.assertTrue(service.status(now)["source_clock_issue"])

    def test_normal_or_simulated_normal_row_does_not_invent_healthy_incident(self):
        row = {"event_decision": "normal"}
        self.assertIsNone(MetarLiveService._live_evidence_record(row, {}, (), ()))
        self.assertIsNone(MetarLiveService._live_evidence_record(row, {}, (), (), simulation=True))

    def test_evidence_keeps_real_scores_and_has_no_fabricated_repairs_or_shap(self):
        row = {"event_decision": "normal", "station_id": "A", "timestamp_utc": "2026-09-01T10:00:00Z",
               "fault_probability": 0.012, "root_cause": "not_a_fault", "root_cause_confidence": 0.99}
        record = MetarLiveService._live_evidence_record(row, {}, ("PHYSICAL_BOUNDS",), (), simulation=True)
        self.assertEqual(record["fault_probability"], 0.012)
        self.assertIsNone(record["root_cause_confidence"])
        self.assertTrue(record["simulation"])
        self.assertEqual(record["root_cause"], "physical_bounds")
        self.assertEqual(record["affected_sensors"], [])
        self.assertEqual(record["model_feature_contributions"], [])
        self.assertEqual(record["corrections"], [])
        self.assertFalse(record["active"])

    def test_model_diagnosis_is_from_same_row_not_injected_ground_truth(self):
        row = {"event_decision": "sensor_fault", "station_id": "B", "timestamp_utc": "2026-09-01T10:00:00Z",
               "fault_probability": 0.65, "root_cause": "pressure_drift", "root_cause_confidence": 0.72}
        record = MetarLiveService._live_evidence_record(row, {}, (), (), simulation=True)
        self.assertEqual(record["root_cause"], "pressure_drift")
        self.assertEqual(record["root_cause_confidence"], 0.72)

    def test_relative_humidity_is_derived_from_temperature_and_dew_point(self) -> None:
        self.assertAlmostEqual(relative_humidity(30.0, 24.0), 70.29, places=1)
        self.assertIsNone(relative_humidity(30.0, None))

    def test_metar_normalization_preserves_official_values(self) -> None:
        service = MetarLiveService(ROOT)
        rows = service._normalize([{  # noqa: SLF001 - focused parser contract test
            "icaoId": "VIDP", "reportTime": "2026-08-26T06:30:00Z",
            "temp": 33, "dewp": 26, "altim": 1005, "rawOb": "METAR VIDP TEST",
        }])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["station_id"], "42181099999")
        self.assertEqual(rows[0]["temperature_c"], 33.0)
        self.assertEqual(rows[0]["pressure_hpa"], 1005.0)
        self.assertGreater(rows[0]["relative_humidity_pct"], 60.0)
        self.assertEqual(rows[0]["pressure_source"], "METAR_QNH")

    def test_live_detector_bundle_uses_only_sih_parameters(self) -> None:
        service = MetarLiveService(ROOT)
        bundle = service._model_bundle()  # noqa: SLF001 - deployment contract test
        self.assertEqual(bundle["policy"]["input_contract"], ["temperature_c", "pressure_hpa", "relative_humidity_pct"])
        self.assertFalse(bundle["policy"]["dew_point_used_by_detector"])
        self.assertFalse(any("dew" in feature.lower() for feature in bundle["event_features"]))

    def test_refresh_has_cached_offline_fallback_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = MetarLiveService(ROOT)
            service.cache_path = Path(directory) / "latest.json"
            source = [{
                "icaoId": "VIDP", "reportTime": "2026-08-26T06:30:00Z",
                "temp": 33, "dewp": 26, "altim": 1005, "rawOb": "METAR VIDP TEST",
            }]
            normalized = service._normalize(source)  # noqa: SLF001
            scored = [{
                **normalized[0], "temperature": 33.0, "pressure": 1005.0, "humidity": 66.2,
                "event_decision": "normal", "fault_probability": 0.02,
                "weather_probability": 0.01, "root_cause": "not_a_fault",
            }]
            with patch.object(service, "_score", return_value=(scored, [])), patch.object(service, "_quality_alerts", return_value=[]):
                status = service.refresh(6, fetcher=lambda hours: source)
            self.assertEqual(status["status"], "live")
            self.assertEqual(status["reporting_stations"], 1)
            self.assertEqual(status["observation_count"], 1)
            self.assertTrue(service.cache_path.exists())
            # Re-processing an existing source copy must preserve source age.
            old_fetch = datetime(2026, 8, 26, 6, 35, tzinfo=timezone.utc)
            with patch.object(service, "_score", return_value=(scored, [])), patch.object(service, "_quality_alerts", return_value=[]):
                rescored = service.refresh(6, fetcher=lambda hours: source, source_fetched_at=old_fetch)
            self.assertEqual(rescored["fetched_at_utc"], "2026-08-26T06:35:00Z")
            self.assertEqual(rescored["simulation_active"], False)

    def test_unvalidated_model_and_drift_cannot_confirm_live_incident(self) -> None:
        model_probability, drift_score = MetarLiveService._incident_shadow_inputs(0.999, 1.0)  # noqa: SLF001
        self.assertEqual(model_probability, 0.0)
        self.assertEqual(drift_score, 0.0)

    def test_incident_endpoint_contract_is_explicitly_evidence_only(self) -> None:
        service = MetarLiveService(ROOT)
        service.payload = {
            "incidents": [{"station_id": "A", "incident_id": "I10-X", "active": True}],
            "incident_policy_mode": LIVE_INCIDENT_POLICY_MODE,
        }
        self.assertEqual(service.incidents(active_only=True)[0]["incident_id"], "I10-X")
        self.assertEqual(service.status()["incident_policy_mode"], LIVE_INCIDENT_POLICY_MODE)

    def test_old_cached_incident_policy_is_invalidated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = MetarLiveService(ROOT)
            service.cache_path = Path(directory) / "latest.json"
            service.cache_path.write_text(
                '{"incident_policy_mode":"shadow_not_automatic","incidents":'
                '[{"station_id":"A","active":true}],"readings":[],"latest":[]}',
                encoding="utf-8",
            )
            migrated = service._load_cache()  # noqa: SLF001
        self.assertEqual(migrated["incidents"], [])
        self.assertEqual(migrated["incident_shadow_active_count"], 0)
        self.assertEqual(migrated["incident_policy_mode"], LIVE_INCIDENT_POLICY_MODE)
        self.assertEqual(migrated["presentation_contract"], LIVE_PRESENTATION_CONTRACT)
        self.assertIsNone(migrated["simulation_active"])


    def test_physical_consistency_gate_repairs_corrupt_dewpoint_exceeds_temperature(self) -> None:
        service = MetarLiveService(ROOT)
        # Corrupted report where dew point (24 C) exceeds temperature (7 C)
        corrupted = [{
            "icaoId": "VIGR", "reportTime": "2026-09-12T11:30:00Z",
            "temp": 7, "dewp": 24, "altim": 1006, "rawOb": "METAR VIGR 121130Z 07/24 Q1006 NOSIG",
        }]
        normalized = service._normalize(corrupted)
        self.assertEqual(len(normalized), 1)
        # Repaired temperature must be physically consistent (>= dew point 24 C)
        self.assertGreaterEqual(normalized[0]["temperature_c"], 24.0)
        self.assertIn("PHYSICAL_QC", normalized[0]["source_quality"])
        self.assertEqual(normalized[0]["raw_observation"], "METAR VIGR 121130Z 07/24 Q1006 NOSIG")


if __name__ == "__main__":
    unittest.main()


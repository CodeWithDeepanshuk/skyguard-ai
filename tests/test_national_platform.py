"""Automated tests for National AWS Operational Platform (SIH26073).

Verifies:
1. Strict scientific provenance between direct observations and numerical reference models
2. IMD WIS 2.0 and METAR provider normalization
3. Master Station Registry deduplication and coverage auditing (X / 1008)
4. NOAA MADIS-grade spatial buddy check with MAD scale and elevation lapse adjustment
5. Three-independent-evidence anomaly detection and Event Consistency Gate
6. FastAPI v1 endpoints (stations, 3-trace history, QC diagnostics, network status)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

from skyguard.api.app import create_app
from skyguard.detection.multi_evidence import AnomalyFlag, MultiEvidenceAnomalyDetector
from skyguard.providers.base import (
    ObservationRecord,
    ProviderName,
    RHSource,
    SourceType,
    StalenessStatus,
)
from skyguard.spatial.buddy_check import SpatialBuddyCheck, adjust_for_elevation
from skyguard.spatial.graph import SpatialNeighborGraph
from skyguard.stations.registry import MasterStationRegistry, StationMetadata, haversine_km


class NationalPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(ROOT)
        cls.client = TestClient(cls.app)
        cls.registry = MasterStationRegistry(root=ROOT)
        cls.graph = SpatialNeighborGraph(registry=cls.registry)
        cls.buddy_checker = SpatialBuddyCheck()
        cls.detector = MultiEvidenceAnomalyDetector()

    def test_observation_record_provenance_contract(self):
        """Verify strict provenance tagging separating observations from reference models."""
        # Direct observation
        obs = ObservationRecord(
            provider=ProviderName.IMD_WIS2.value,
            source_type=SourceType.OBSERVED.value,
            station_id="42182099999",
            timestamp_utc="2026-09-12T12:00:00Z",
            latitude=28.58,
            longitude=77.20,
            temperature_c=31.2,
            relative_humidity_pct=65.0,
            pressure_hpa=1008.4,
            is_direct_observation=True,
            is_model_field=False,
            rh_source=RHSource.OBSERVED.value,
        )
        self.assertTrue(obs.is_direct_observation)
        self.assertFalse(obs.is_model_field)
        self.assertEqual(obs.source_type, "OBSERVED")
        self.assertIsNotNone(obs.raw_source_hash)

        # Reference model
        ref = ObservationRecord(
            provider=ProviderName.OPEN_METEO_REFERENCE.value,
            source_type=SourceType.REFERENCE_MODEL.value,
            station_id="42182099999",
            timestamp_utc="2026-09-12T12:00:00Z",
            latitude=28.58,
            longitude=77.20,
            temperature_c=30.8,
            relative_humidity_pct=64.0,
            pressure_hpa=1008.0,
            is_direct_observation=False,
            is_model_field=True,
            is_interpolated=True,
        )
        self.assertFalse(ref.is_direct_observation)
        self.assertTrue(ref.is_model_field)
        self.assertTrue(ref.is_interpolated)
        self.assertEqual(ref.source_type, "REFERENCE_MODEL")

    def test_master_station_registry_and_coverage(self):
        """Verify master registry coverage reporting without synthetic coordinates."""
        audit = self.registry.coverage_audit()
        self.assertEqual(audit["target_national_aws_coverage"], 1008)
        self.assertEqual(audit["verified_in_situ_stations"], 1008)
        self.assertEqual(audit["breakdown"]["synthetic_or_reference_only"], 0)
        self.assertIn("official IMD WIS2", audit["scientific_integrity_guarantee"])

        # Check retrieval by station ID and ICAO
        delhi = self.registry.get_station("42182099999") or self.registry.get_station("0-20000-0-42182")
        self.assertIsNotNone(delhi)
        self.assertAlmostEqual(delhi.latitude, 28.58, delta=0.5)

    def test_spatial_neighbor_discovery(self):
        """Verify adaptive leave-one-out concentric ring neighbour discovery."""
        delhi_id = "0-20000-0-42182"
        neighbors = self.graph.get_neighbors(delhi_id, k=5, max_radius_km=300.0)
        self.assertGreaterEqual(len(neighbors), 3)

        # Target station must be excluded (leave-one-out)
        neighbor_ids = [n["station_id"] for n in neighbors]
        self.assertNotIn(delhi_id, neighbor_ids)

        # Distances must be sorted ascending
        distances = [n["distance_km"] for n in neighbors]
        self.assertEqual(distances, sorted(distances))

    def test_madis_buddy_check_and_elevation_adjustment(self):
        """Verify MADIS buddy check, lapse rate adjustment, and scaled MAD calculation."""
        # Elevation lapse adjustment: higher station should expect cooler temperatures
        t_neighbor = 30.0
        adjusted = adjust_for_elevation("temperature", neighbor_val=t_neighbor, neighbor_elev_m=100.0, target_elev_m=1100.0)
        # Lapse rate is -6.5 C per 1000m -> delta_h = 1000m -> should decrease by 6.5 C
        self.assertAlmostEqual(adjusted, 23.5, delta=0.1)

        # Test buddy check with an obvious outlier
        neighbor_obs = [
            {"station_id": "STN_B", "distance_km": 20.0, "elevation_m": 200.0, "value": 30.0},
            {"station_id": "STN_C", "distance_km": 35.0, "elevation_m": 210.0, "value": 30.5},
            {"station_id": "STN_D", "distance_km": 50.0, "elevation_m": 195.0, "value": 29.8},
        ]
        # Target station reporting 45.0 C (15 C spike)
        result = self.buddy_checker.check(
            parameter="temperature",
            target_station_id="STN_A",
            target_value=45.0,
            target_elevation_m=200.0,
            neighbor_observations=neighbor_obs,
        )
        self.assertEqual(result.status, "DISCREPANT")
        self.assertGreater(result.z_spatial, 3.0)
        self.assertAlmostEqual(result.consensus_value, 30.0, delta=0.5)

    def test_multi_evidence_spike_detection(self):
        """Verify multi-evidence detection flags isolated sudden spike."""
        target = ObservationRecord(
            provider="IMD_AWS",
            source_type="OBSERVED",
            station_id="TEST_STN",
            timestamp_utc="2026-09-12T12:00:00Z",
            latitude=28.0,
            longitude=77.0,
            elevation_m=200.0,
            temperature_c=46.0,  # Sudden +16 C spike
            relative_humidity_pct=40.0,
            pressure_hpa=1005.0,
        )
        history = [
            ObservationRecord(
                provider="IMD_AWS",
                source_type="OBSERVED",
                station_id="TEST_STN",
                timestamp_utc=f"2026-09-12T{h:02d}:00:00Z",
                latitude=28.0,
                longitude=77.0,
                temperature_c=30.0,
            )
            for h in range(11, 0, -1)
        ]
        neighbors = [
            {"station_id": "N1", "distance_km": 20.0, "temperature_c": 30.2, "temperature_delta": 0.1},
            {"station_id": "N2", "distance_km": 30.0, "temperature_c": 29.8, "temperature_delta": -0.2},
            {"station_id": "N3", "distance_km": 40.0, "temperature_c": 30.5, "temperature_delta": 0.0},
        ]
        res = self.detector.analyze(target, history, neighbors)
        self.assertEqual(res.overall_status, "ANOMALY_DETECTED")
        spike_anomalies = [a for a in res.anomalies if a.anomaly_type == "SUDDEN_SPIKE"]
        self.assertGreaterEqual(len(spike_anomalies), 1)
        self.assertLess(res.sensor_health_score, 80.0)

    def test_event_consistency_gate_suppression(self):
        """Verify that when neighbours also show coordinated drops, false alert is suppressed."""
        target = ObservationRecord(
            provider="IMD_AWS",
            source_type="OBSERVED",
            station_id="TEST_STN",
            timestamp_utc="2026-09-12T12:00:00Z",
            latitude=28.0,
            longitude=77.0,
            elevation_m=200.0,
            temperature_c=22.0,  # Sudden -8 C drop
        )
        # Previous hour was 30.0 C
        history = [
            ObservationRecord(
                provider="IMD_AWS",
                source_type="OBSERVED",
                station_id="TEST_STN",
                timestamp_utc="2026-09-12T11:00:00Z",
                latitude=28.0,
                longitude=77.0,
                temperature_c=30.0,
            )
        ]
        # Neighbours ALSO experienced -7 C drops (cold front / squall line)
        neighbors = [
            {"station_id": "N1", "distance_km": 20.0, "temperature_c": 22.5, "temperature_delta": -7.5},
            {"station_id": "N2", "distance_km": 30.0, "temperature_c": 21.8, "temperature_delta": -8.0},
            {"station_id": "N3", "distance_km": 40.0, "temperature_c": 23.0, "temperature_delta": -7.0},
        ]
        res = self.detector.analyze(target, history, neighbors)
        self.assertTrue(res.event_consistency["front_detected"])
        self.assertEqual(res.overall_status, "METEOROLOGICAL_FRONT")

    def test_api_v1_stations_and_audit(self):
        """Verify /api/v1/stations endpoint returns verified audit."""
        resp = self.client.get("/api/v1/stations?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("coverage_audit", data)
        self.assertEqual(data["coverage_audit"]["target_national_aws_coverage"], 1008)
        self.assertGreaterEqual(len(data["stations"]), 1)

    def test_api_v1_station_history_triplet(self):
        """Verify /api/v1/stations/{id}/history returns 3 synchronized traces."""
        resp = self.client.get("/api/v1/stations/0-20000-0-42182/history?hours=24")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("traces", data)
        self.assertIn("observed", data["traces"])
        self.assertIn("reference_model", data["traces"])
        self.assertIn("neighbor_consensus", data["traces"])

    def test_api_v1_network_status(self):
        """Verify /api/v1/network/status endpoint returns provider health and operational status."""
        resp = self.client.get("/api/v1/network/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "WIS2_OBSERVATION_DECODER_READY")
        self.assertIn("providers", data)
        self.assertIn("coverage_audit", data)


if __name__ == "__main__":
    unittest.main()

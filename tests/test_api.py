from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.api.app import create_app  # noqa: E402


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app(ROOT, ":memory:"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.app.state.runtime.store.close()
        cls.client.close()

    def test_health_and_scenarios(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertGreaterEqual(len(self.client.get("/api/scenarios").json()), 4)

    def test_phase8_dashboard_is_the_root_page(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SkyGuard AI", response.text)
        self.assertIn("Model accuracy & safety", response.text)
        self.assertEqual(self.client.get("/assets/app.js").status_code, 200)
        self.assertEqual(self.client.get("/assets/styles.css").status_code, 200)

    def test_replay_step_persists_readings(self) -> None:
        self.client.post("/api/replay/load/packet_errors")
        response = self.client.post("/api/replay/step", params={"count": 20})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(self.client.get("/api/readings").json()), 0)

    def test_evidence_endpoints(self) -> None:
        self.assertGreater(len(self.client.get("/api/stations").json()), 0)
        self.assertGreater(len(self.client.get("/api/incidents", params={"limit": 2}).json()), 0)
        self.assertIn("classification", self.client.get("/api/metrics").json())
        readiness = self.client.get("/api/competition-readiness")
        self.assertEqual(readiness.status_code, 200)
        self.assertEqual(readiness.json()["model_version"], "SkyGuard-P10-compliant")

    def test_dashboard_summary_contains_both_locked_holdouts(self) -> None:
        response = self.client.get("/api/dashboard-summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["project"]["phase"], 10)
        self.assertEqual(payload["project"]["model_version"], "SkyGuard-P10-compliant")
        self.assertIn("live METAR", payload["project"]["mode"])
        self.assertEqual(payload["policy"]["detector_inputs"], ["temperature", "pressure", "relative_humidity"])
        self.assertFalse(payload["policy"]["dew_point_used_by_detector"])
        self.assertEqual(payload["dataset"]["summary"]["processed_rows"], 578448)
        self.assertIn("time_test", payload["classification"])
        self.assertIn("station_test", payload["classification"])
        self.assertFalse(payload["policy"]["automatic_replacement"])

    def test_incident_csv_download(self) -> None:
        response = self.client.get("/api/export/incidents.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("skyguard_incidents_2024.csv", response.headers["content-disposition"])
        self.assertIn("incident_id,station_id,timestamp_utc", response.text.splitlines()[0])

    def test_live_incident_shadow_endpoint_exists(self) -> None:
        response = self.client.get("/api/live/incidents")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_live_endpoints_are_available_without_forcing_network(self) -> None:
        status = self.client.get("/api/live/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["mode"], "live")
        self.assertEqual(self.client.get("/api/live/readings").status_code, 200)
        self.assertEqual(self.client.get("/api/live/alerts").status_code, 200)

    def test_health_exposes_compliant_detector_contract(self) -> None:
        payload = self.client.get("/health").json()
        self.assertEqual(payload["model_version"], "SkyGuard-P10-compliant")
        self.assertEqual(payload["detector_inputs"], ["temperature", "pressure", "relative_humidity"])
        self.assertTrue(payload["live_capable"])


if __name__ == "__main__":
    unittest.main()

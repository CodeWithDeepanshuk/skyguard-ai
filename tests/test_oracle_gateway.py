"""Automated tests for Oracle Cloud Always Free IMD Gateway and Render Ingestion Webhook (SIH 26073)."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "oci_gateway"))

from skyguard.api.app import create_app
from skyguard.storage import ObservationStore
from collector import OCIIMDCollector, parse_float


class OracleGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db_path = ROOT / "data" / "runtime" / "test_gateway.db"
        cls.db_path.parent.mkdir(parents=True, exist_ok=True)
        if cls.db_path.exists():
            cls.db_path.unlink()
        cls.app = create_app(ROOT, str(cls.db_path))
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()
        if cls.db_path.exists():
            try:
                cls.db_path.unlink()
            except Exception:
                pass

    def test_ingestion_endpoint_requires_configured_token(self) -> None:
        with patch.dict(os.environ, {"SKYGUARD_INGESTION_TOKEN": ""}, clear=False):
            resp = self.client.post("/api/v1/ingestion/imd", json={"records": []})
            self.assertEqual(resp.status_code, 503)
            self.assertIn("SKYGUARD_INGESTION_TOKEN is not configured", resp.json()["detail"])

    def test_ingestion_endpoint_rejects_unauthorized_token(self) -> None:
        with patch.dict(os.environ, {"SKYGUARD_INGESTION_TOKEN": "secret-token-123"}, clear=False):
            resp = self.client.post(
                "/api/v1/ingestion/imd",
                json={"records": []},
                headers={"X-Ingestion-Token": "wrong-token"},
            )
            self.assertEqual(resp.status_code, 401)
            self.assertIn("Invalid ingestion token", resp.json()["detail"])

    def test_ingestion_endpoint_accepts_valid_payload(self) -> None:
        import time
        token = "secret-gateway-token-xyz"
        unique_suffix = int(time.time() * 1000)
        test_records = [
            {
                "station_id": f"DELHI_TEST_{unique_suffix}",
                "station_name": "DELHI PALAM AIRPORT",
                "latitude": 28.56,
                "longitude": 77.11,
                "temperature_c": 32.5,
                "pressure_hpa": 1008.2,
                "relative_humidity_pct": 58.0,
                "timestamp_utc": "2026-09-24T21:00:00Z",
                "is_direct_observation": True,
            },
            {
                "station_id": f"MUMBAI_TEST_{unique_suffix}",
                "station_name": "MUMBAI SANTACRUZ",
                "latitude": 19.12,
                "longitude": 72.85,
                "temperature_c": 29.8,
                "pressure_hpa": 1011.0,
                "relative_humidity_pct": 82.0,
                "timestamp_utc": "2026-09-24T21:00:00Z",
                "is_direct_observation": True,
            },
        ]
        receipt = {
            "endpoint_name": "aws_data",
            "source_url": "https://api.imd.gov.in/api/v1/aws_data",
            "retrieved_at_utc": "2026-09-24T21:00:00Z",
            "gateway_egress_ip": "140.238.10.20",
            "payload_bytes": 1024,
            "payload_sha256": hashlib.sha256(b"test-bytes").hexdigest(),
            "provenance": "ORACLE_CLOUD_ALWAYS_FREE_GATEWAY",
        }

        with patch.dict(os.environ, {"SKYGUARD_INGESTION_TOKEN": token}, clear=False):
            resp = self.client.post(
                "/api/v1/ingestion/imd",
                json={
                    "receipt": receipt,
                    "records": test_records,
                    "raw_payload_json": json.dumps(test_records),
                },
                headers={"X-Ingestion-Token": token},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "SUCCESS")
            self.assertEqual(data["provider"], "IMD_AWS")
            self.assertEqual(data["gateway_provenance"], "ORACLE_CLOUD_GATEWAY")
            self.assertEqual(data["received"], 2)
            self.assertEqual(data["accepted"], 2)
            self.assertEqual(data["inserted"] + data["duplicates"], 2)
            self.assertGreaterEqual(data["inserted"], 1)

    def test_collector_normalizes_raw_imd_data_correctly(self) -> None:
        collector = OCIIMDCollector(
            api_key="test-key",
            email="test@imd.gov.in",
            password="test",
            render_url="http://localhost:8000/api/v1/ingestion/imd",
            ingest_token="token",
            archive_dir=ROOT / "data" / "runtime" / "test_archives",
        )
        raw_imd_payload = [
            {
                "CALL_SIGN": "BENGALURU_AWS",
                "STATION": "BENGALURU CITY",
                "STATE": "KARNATAKA",
                "DISTRICT": "BENGALURU URBAN",
                "Latitude": "12.97",
                "Longitude": "77.59",
                "CURR_TEMP": "24.5",
                "MSLP": "1012.3",
                "RH": "75.0",
                "DATE": "2026-09-24",
                "TIME": "20:45:00",
            },
            {
                "CALL_SIGN": "INVALID_EMPTY",
                # missing all 3 parameters; should be filtered out
            },
        ]

        normalized = collector.normalize_records(raw_imd_payload)
        self.assertEqual(len(normalized), 1)
        rec = normalized[0]
        self.assertEqual(rec["station_id"], "BENGALURU_AWS")
        self.assertEqual(rec["temperature_c"], 24.5)
        self.assertEqual(rec["pressure_hpa"], 1012.3)
        self.assertEqual(rec["relative_humidity_pct"], 75.0)
        self.assertTrue(rec["is_direct_observation"])
        self.assertFalse(rec["is_synthetic"])

    def test_collector_archive_generates_sha256_receipt(self) -> None:
        archive_dir = ROOT / "data" / "runtime" / "test_archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        collector = OCIIMDCollector(
            api_key="test-key",
            email="test@imd.gov.in",
            password="test",
            render_url="http://localhost:8000/api/v1/ingestion/imd",
            ingest_token="token",
            archive_dir=archive_dir,
        )
        sample_bytes = b'{"status":"ok","records":[{"id":"1","temp":25.0}]}'
        receipt = collector.archive_payload(sample_bytes, "140.238.1.1")
        expected_sha = hashlib.sha256(sample_bytes).hexdigest()
        self.assertEqual(receipt["payload_sha256"], expected_sha)
        self.assertEqual(receipt["payload_bytes"], len(sample_bytes))
        self.assertEqual(receipt["gateway_egress_ip"], "140.238.1.1")


if __name__ == "__main__":
    unittest.main()

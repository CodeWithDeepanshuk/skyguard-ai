"""Tests for Open-Meteo live ingestion service."""
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skyguard.ingestion.open_meteo import OpenMeteoIngestionService


class TestOpenMeteoIngestion(unittest.TestCase):
    def test_catalog_loaded(self):
        svc = OpenMeteoIngestionService()
        self.assertEqual(svc.station_count, 1008)

    @patch("requests.Session.get")
    def test_fetch_live_batch_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "latitude": 28.58,
                "longitude": 77.20,
                "current": {
                    "time": "2026-09-19T17:30",
                    "temperature_2m": 26.5,
                    "relative_humidity_2m": 82,
                    "surface_pressure": 987.3,
                },
            }
        ]
        mock_get.return_value = mock_resp

        svc = OpenMeteoIngestionService()
        batch = [{
            "station_id": "42182099999",
            "station_name": "New Delhi Safdarjung AWS",
            "latitude": 28.58,
            "longitude": 77.20,
            "elevation_m": 216.0,
            "climate_zone": "Indo-Gangetic Plains",
            "cluster": "indo_gangetic_plains",
        }]
        res = svc.fetch_live_batch(batch)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["current"]["temperature_2m"], 26.5)


if __name__ == "__main__":
    unittest.main()

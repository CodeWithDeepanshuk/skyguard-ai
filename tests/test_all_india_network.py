"""Tests for the All-India AWS Station Network Catalog and API Endpoints."""

from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.api.app import create_app
from skyguard.features.spatial_qc import SPATIAL_QC_FEATURES, add_spatial_qc
import pandas as pd
import numpy as np


class AllIndiaNetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app(ROOT, ":memory:"))
        cls.catalog_path = ROOT / "config" / "all_india_aws_network.csv"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.app.state.runtime.store.close()
        cls.client.close()

    def test_catalog_file_integrity(self) -> None:
        self.assertTrue(self.catalog_path.exists(), "Catalog file config/all_india_aws_network.csv must exist")
        with self.catalog_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1008, f"Expected 1008 Indian stations, got {len(rows)}")

        # Check required columns
        required_cols = {"station_id", "station_name", "climate_zone", "latitude", "longitude", "elevation_m", "is_benchmark", "is_active_2024_plus"}
        self.assertTrue(required_cols.issubset(rows[0].keys()), f"Missing columns in catalog: {required_cols - set(rows[0].keys())}")

        # Check all 8 climate zones
        zones = {r["climate_zone"] for r in rows}
        expected_zones = {
            "Central Plateau", "Coastal Plains", "Indo-Gangetic Plains",
            "Deccan Plateau", "Northeast Hills", "Western Arid/Semi-Arid",
            "Northern Himalayas", "Island Territories"
        }
        self.assertTrue(expected_zones.issubset(zones), f"Missing climate zones: {expected_zones - zones}")

        # Check benchmark stations count
        benchmark_count = sum(1 for r in rows if str(r.get("is_benchmark")) == "1")
        self.assertEqual(benchmark_count, 24, f"Expected 24 benchmark stations, got {benchmark_count}")

        # Check active 2024+ stations count
        active_count = sum(1 for r in rows if str(r.get("is_active_2024_plus")) == "1")
        self.assertEqual(active_count, 1008, f"Expected 1008 active 2024+ stations, got {active_count}")

        # Check coordinate bounds (valid geographic coordinates)
        for r in rows:
            lat = float(r["latitude"])
            lon = float(r["longitude"])
            self.assertTrue(-90.0 <= lat <= 90.0, f"Station {r['station_name']} latitude {lat} outside valid bounds")
            self.assertTrue(-180.0 <= lon <= 180.0, f"Station {r['station_name']} longitude {lon} outside valid bounds")

    def test_api_stations_all(self) -> None:
        response = self.client.get("/api/stations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1008, "Default /api/stations must return all 1008 stations")

    def test_api_stations_benchmark_filter(self) -> None:
        response = self.client.get("/api/stations?network=benchmark")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 24, "Benchmark filter must return exactly 24 core stations")

    def test_api_stations_active_filter(self) -> None:
        response = self.client.get("/api/stations?network=active")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1008, "Active filter must return all 1008 stations active into 2024+")

    def test_api_stations_climate_zone_filter(self) -> None:
        response = self.client.get("/api/stations?climate_zone=Indo-Gangetic%20Plains")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 70, "Indo-Gangetic Plains should return at least 70 stations")
        self.assertTrue(all(r["climate_zone"] == "Indo-Gangetic Plains" for r in data))

    def test_api_network_summary(self) -> None:
        response = self.client.get("/api/network/summary")
        self.assertEqual(response.status_code, 200)
        summary = response.json()
        self.assertEqual(summary["total_stations"], 1008)
        self.assertEqual(summary["benchmark_stations"], 24)
        self.assertEqual(summary["active_2024_plus"], 1008)
        self.assertEqual(summary["national_scale_target"], 1008)
        self.assertAlmostEqual(summary["coverage_percentage"], 100.0, places=1)
        self.assertEqual(len(summary["climate_zones"]), 8)

    def test_spatial_qc_features_exported(self) -> None:
        self.assertEqual(len(SPATIAL_QC_FEATURES), 7)
        self.assertIn("qc_spatial_support", SPATIAL_QC_FEATURES)
        self.assertIn("qc_temperature_buddy_z", SPATIAL_QC_FEATURES)
        self.assertIn("qc_pressure_buddy_z", SPATIAL_QC_FEATURES)
        self.assertIn("qc_humidity_buddy_z", SPATIAL_QC_FEATURES)

    def test_spatial_qc_computation(self) -> None:
        # Create minimal synthetic data with neighbour features
        df = pd.DataFrame({
            "station_id": ["42181099999", "42182099999"],
            "emitted_timestamp_utc": ["2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"],
            "temperature_value": [25.0, 25.2],
            "pressure_value": [1013.0, 1012.8],
            "humidity_value": [60.0, 62.0],
            "neighbor_station_count": [3, 3],
            "neighbor_max_age_minutes": [20.0, 20.0],
            "nearest_neighbor_km": [15.0, 15.0],
            "neighbor_temperature_count": [3, 3],
            "neighbor_temperature_residual": [0.2, -0.2],
            "neighbor_temperature_mad": [0.4, 0.4],
            "temperature_robust_z_24h": [0.5, -0.5],
            "neighbor_pressure_count": [3, 3],
            "neighbor_pressure_residual": [0.3, -0.3],
            "neighbor_pressure_mad": [0.5, 0.5],
            "pressure_robust_z_24h": [0.2, -0.2],
            "neighbor_humidity_count": [3, 3],
            "neighbor_humidity_residual": [1.0, -1.0],
            "neighbor_humidity_mad": [2.0, 2.0],
            "humidity_robust_z_24h": [0.1, -0.1],
        })
        enriched = add_spatial_qc(df)
        for col in SPATIAL_QC_FEATURES:
            self.assertIn(col, enriched.columns)
            self.assertFalse(enriched[col].isna().all())


if __name__ == "__main__":
    unittest.main()

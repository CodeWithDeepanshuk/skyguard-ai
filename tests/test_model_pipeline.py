"""Automated tests for Phase 20 Production Model Endpoints."""

import pytest
from fastapi.testclient import TestClient
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.api.app import create_app

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def client():
    app = create_app(root=ROOT)
    return TestClient(app)

def test_model_status_endpoint(client):
    response = client.get("/api/model/status")
    assert response.status_code == 200
    data = response.json()
    assert "model_version" in data
    assert "loaded_models" in data
    assert "training_dataset" in data
    assert "training_period" in data
    assert data["status"] == "OPERATIONAL"

def test_model_metrics_endpoint(client):
    response = client.get("/api/model/metrics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert ("models" in data) or ("project" in data) or ("threshold" in data)

def test_anomaly_predict_endpoint_normal(client):
    payload = {
        "station_data": {
            "station_id": "42181099999",
            "station_name": "New Delhi Safdarjung AWS",
            "timestamp_utc": "2024-05-15T12:00:00Z",
            "temperature_c": 32.5,
            "pressure_hpa": 1002.0,
            "relative_humidity_pct": 55.0,
            "elevation_m": 216.0,
            "latitude": 28.58,
            "longitude": 77.20
        },
        "recent_history": [
            {"temperature_c": 32.2, "pressure_hpa": 1002.5, "relative_humidity_pct": 56.0},
            {"temperature_c": 32.4, "pressure_hpa": 1002.1, "relative_humidity_pct": 55.5}
        ],
        "neighbor_observations": [
            {"station_id": "42182099999", "latitude": 28.56, "longitude": 77.10, "temperature_c": 32.8, "pressure_hpa": 1001.8, "relative_humidity_pct": 54.0, "elevation_m": 236.0}
        ]
    }
    response = client.post("/api/anomaly/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["station_id"] == "42181099999"
    assert "anomaly_score" in data
    assert "decision" in data
    assert data["decision"] in ["NORMAL", "SENSOR_FAULT"]
    assert "root_cause" in data
    assert "evidence" in data
    assert data["confidence_type"] == "empirical_calibrated_evidence_score"

def test_anomaly_predict_endpoint_physical_violation(client):
    payload = {
        "station_data": {
            "station_id": "42181099999",
            "timestamp_utc": "2024-05-15T12:00:00Z",
            "temperature_c": 95.0,  # Physically impossible surface temp
            "pressure_hpa": 1002.0,
            "relative_humidity_pct": 55.0
        },
        "recent_history": [],
        "neighbor_observations": []
    }
    response = client.post("/api/anomaly/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "SENSOR_FAULT"
    assert data["root_cause"] == "temperature_physical_bounds_violation"
    assert data["severity"] == "CRITICAL"

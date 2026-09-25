import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.api.app import create_app
from skyguard.storage import ObservationStore


def test_source_status_endpoint_returns_honest_mode():
    app = create_app(root=ROOT)
    client = TestClient(app)
    
    response = client.get("/api/v1/source/status")
    assert response.status_code == 200
    data = response.json()
    
    assert "effective_source" in data
    assert "is_authorized_live_source" in data
    assert "is_fixture_replay" in data
    assert data["pressure_semantics"] == "MEAN_SEA_LEVEL_PRESSURE (MSLP)"
    assert data["meteorological_inputs"] == ["temperature_c", "pressure_hpa", "relative_humidity_pct"]


def test_evaluation_summary_endpoint_serves_benchmark():
    app = create_app(root=ROOT)
    client = TestClient(app)
    
    response = client.get("/api/v1/evaluation/summary")
    assert response.status_code == 200
    data = response.json()
    
    if data.get("status") != "BENCHMARK_PENDING":
        assert "architecture_comparison" in data
        assert "split_contract" in data
        assert data["leakage_verified"] == "ZERO_LEAKAGE"

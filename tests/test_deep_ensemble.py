import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest
from skyguard.models.deep_ensemble import DeepEnsembleDetector, SpatioTemporalNeuralEngine


def test_neural_engine_forward():
    import torch
    engine = SpatioTemporalNeuralEngine(in_features=6)
    dummy_in = torch.randn(2, 24, 6)
    recon, res, prob = engine(dummy_in)
    assert recon.shape == (2, 24, 6)
    assert res.shape == (2, 6)
    assert prob.shape == (2,)
    assert (prob >= 0.0).all() and (prob <= 1.0).all()


def test_deep_ensemble_nominal_evaluation():
    detector = DeepEnsembleDetector()
    station = {
        "station_id": "42182099999",
        "station_name": "New Delhi Safdarjung AWS",
        "temperature_c": 26.5,
        "pressure_hpa": 1008.2,
        "relative_humidity_pct": 58.0,
        "latitude": 28.58,
        "longitude": 77.20,
        "elevation_m": 216.0,
    }
    peers = [
        {
            "station_id": f"peer_{i}",
            "temperature_c": 26.5 + (i - 2) * 0.2,
            "pressure_hpa": 1008.2 + (i - 2) * 0.1,
            "relative_humidity_pct": 58.0 + (i - 2) * 0.8,
            "latitude": 28.58 + (i - 2) * 0.1,
            "longitude": 77.20 + (i - 2) * 0.1,
            "elevation_m": 216.0,
        }
        for i in range(5)
    ]
    res = detector.evaluate_station(station, [], peers)
    assert res.decision == "NORMAL"
    assert res.root_cause == "nominal_spatial_consensus"
    assert 0.010 <= res.evidence_score <= 0.150
    assert 0.0 <= res.z_scores["max_z"] < 2.0


def test_deep_ensemble_spike_fault():
    detector = DeepEnsembleDetector()
    station = {
        "station_id": "42182099999",
        "station_name": "New Delhi Safdarjung AWS",
        "temperature_c": 42.5,  # Injected severe +16C spike
        "pressure_hpa": 1008.2,
        "relative_humidity_pct": 58.0,
        "latitude": 28.58,
        "longitude": 77.20,
        "elevation_m": 216.0,
    }
    peers = [
        {
            "station_id": f"peer_{i}",
            "temperature_c": 26.5 + (i - 2) * 0.2,
            "pressure_hpa": 1008.2,
            "relative_humidity_pct": 58.0,
            "latitude": 28.58 + (i - 2) * 0.1,
            "longitude": 77.20,
            "elevation_m": 216.0,
        }
        for i in range(5)
    ]
    res = detector.evaluate_station(station, [], peers)
    assert res.decision == "SENSOR_FAULT"
    assert "spike" in res.root_cause
    assert res.evidence_score >= 0.75

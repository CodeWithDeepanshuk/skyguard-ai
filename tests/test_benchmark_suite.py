import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.evaluation.benchmark_suite import BenchmarkSuite


def generate_mock_observations(stations=5, periods=300):
    rows = []
    for j in range(stations):
        for i, ts in enumerate(pd.date_range("2025-01-01", periods=periods, freq="h", tz="UTC")):
            rows.append({
                "station_id": f"TEST_{j}",
                "timestamp_utc": ts,
                "source_snapshot_hash": f"hash_{i}",
                "source_is_genuine": True,
                "temperature_c": 26.0 + 4.0 * np.sin(i / 24.0),
                "pressure_hpa": 1008.0 + 2.0 * np.cos(i / 30.0),
                "relative_humidity_pct": 60.0 - 10.0 * np.sin(i / 24.0),
                "latitude": 20.0 + j * 0.3,
                "longitude": 75.0 + j * 0.3,
            })
    return pd.DataFrame(rows)


def test_benchmark_suite_runs_and_reports_comparison(tmp_path):
    suite = BenchmarkSuite(root=tmp_path, random_seed=42)
    obs = generate_mock_observations(stations=5, periods=250)
    
    report = suite.run_evaluation(obs, events_per_type=1)
    
    assert report["status"] == "VALIDATED"
    assert report["leakage_verified"] == "ZERO_LEAKAGE"
    assert "future_test_performance" in report
    assert "spatial_generalization_performance" in report
    
    arch = report["architecture_comparison"]
    assert "rules_only" in arch
    assert "rules_plus_isolation_forest" in arch
    assert "hybrid_causal_ensemble" in arch
    
    for model_name, metrics in arch.items():
        assert 0.0 <= metrics["precision"] <= 1.0
        assert 0.0 <= metrics["recall"] <= 1.0
        assert 0.0 <= metrics["f1"] <= 1.0
        assert metrics["false_alerts_per_station_day"] >= 0.0

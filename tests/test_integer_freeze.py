"""Unit tests for Phase 6: Quantization-Aware Freeze Detection."""

import pandas as pd
import numpy as np
from src.skyguard.features.freeze import (
    estimate_quantization_resolution,
    compute_freeze_metrics,
)


def test_estimate_quantization_resolution():
    # Integer-quantized series
    int_series = pd.Series([28.0, 29.0, 28.0, 27.0, 30.0, 31.0, 29.0, 28.0])
    res_int = estimate_quantization_resolution(int_series)
    assert res_int == 1.0, f"Expected 1.0 for integer series, got {res_int}"
    
    # Decimals series
    dec_series = pd.Series([28.1, 28.4, 28.7, 29.2, 29.5, 29.1, 28.6])
    res_dec = estimate_quantization_resolution(dec_series)
    assert res_dec <= 0.1, f"Expected <= 0.1 for decimal series, got {res_dec}"


def test_normal_integer_night_dwell_does_not_trigger_freeze():
    # 10 consecutive readings of 28.0 C at night (5 hours at 30m cadence)
    values = pd.Series([29.0, 29.0, 28.0] + [28.0] * 10 + [27.0, 27.0])
    timestamps = pd.date_range("2023-05-01 20:00", periods=len(values), freq="30min")
    
    metrics = compute_freeze_metrics(values, timestamps, min_freeze_run_length=24)
    
    # Run length reached 10, but is_freeze_anomaly MUST be False
    assert not metrics["is_freeze_anomaly"].any(), "Normal 10-reading night dwell was incorrectly flagged as freeze!"


def test_true_stuck_sensor_triggers_freeze():
    # 50 consecutive readings stuck at exactly 28.0 C
    # While neighbour is cycling normally through diurnal temperatures (22 C to 36 C)
    n = 60
    values = pd.Series([28.0] * n)
    timestamps = pd.date_range("2023-05-01 00:00", periods=n, freq="30min")
    
    # Neighbour diurnal wave
    hours = np.linspace(0, 30, n)
    neighbor_values = pd.Series(28.0 + 8.0 * np.sin(2 * np.pi * hours / 24))
    
    metrics = compute_freeze_metrics(values, timestamps, neighbor_series=neighbor_values, min_freeze_run_length=24)
    
    # At late readings (>= 36), is_freeze_anomaly MUST be True
    assert metrics.loc[45:, "is_freeze_anomaly"].any(), "Persistent 48-reading stuck sensor was missed!"

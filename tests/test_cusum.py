"""Unit tests for Phase 7: Slow-Drift Specialist (CUSUM)."""

import numpy as np
import pandas as pd
from src.skyguard.features.drift_cusum import compute_two_sided_cusum


def test_normal_noise_does_not_fire_cusum():
    np.random.seed(42)
    # 100 samples of zero-mean Gaussian noise
    residuals = pd.Series(np.random.normal(0, 0.5, size=100))
    s_pos, s_neg, score, alert = compute_two_sided_cusum(residuals, allowance_k=0.5, threshold_h=4.0)
    
    assert not alert.any(), "Normal stationary noise triggered false CUSUM alarm!"


def test_slow_drift_detected_within_latency_bound():
    # 20 normal samples, then persistent positive calibration drift (+0.6 per step)
    # At 30-min cadence, 4 steps = 120 minutes
    residuals = pd.Series([0.0] * 20 + [0.8] * 10)
    timestamps = pd.date_range("2023-05-01", periods=30, freq="30min")
    
    s_pos, s_neg, score, alert = compute_two_sided_cusum(
        residuals, allowance_k=0.3, threshold_h=3.0, timestamps=timestamps
    )
    
    # Alert must fire between step 23 and 26 (within 120-180 minutes of drift onset)
    first_alert_idx = np.where(alert)[0][0]
    drift_onset_idx = 20
    latency_steps = first_alert_idx - drift_onset_idx
    latency_minutes = latency_steps * 30
    
    assert latency_steps <= 5, f"Drift latency {latency_steps} steps exceeds target!"
    assert latency_minutes <= 150, f"Drift latency {latency_minutes}m exceeds 180m gate!"


def test_cusum_resets_on_transmission_gap():
    # Positive accumulation, then 12-hour gap, then normal values
    residuals = pd.Series([1.0, 1.0, 1.0, 0.0, 0.0])
    timestamps = pd.to_datetime([
        "2023-05-01 00:00:00Z",
        "2023-05-01 00:30:00Z",
        "2023-05-01 01:00:00Z",
        "2023-05-01 13:00:00Z", # 12-hour transmission gap
        "2023-05-01 13:30:00Z",
    ])
    
    s_pos, s_neg, score, alert = compute_two_sided_cusum(
        residuals, allowance_k=0.2, threshold_h=5.0, reset_on_gap_hours=6.0, timestamps=timestamps
    )
    
    # After the 12-hour gap at index 3, s_pos must be reset
    assert s_pos[3] == 0.0, "CUSUM failed to reset after long transmission gap!"

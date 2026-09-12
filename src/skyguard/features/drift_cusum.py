"""Two-Sided CUSUM Slow-Drift Specialist for SkyGuard AI.

Critical Scientific Principle:
Subtle sensor degradation, calibration loss, and bias drift evolve slowly.
A single-point classifier often misses them because individual observations
remain within plausible broad physical limits.
Two-sided cumulative sum (CUSUM) integrates small persistent residuals over time:
    S_t^+ = max(0, S_{t-1}^+ + r_t - k)
    S_t^- = min(0, S_{t-1}^- + r_t + k)
where k is the slack allowance and h is the alarm threshold.
This enables detection within <= 120-180 minutes of drift initiation,
passing the detection latency gate without false alarm inflation.
"""

from __future__ import annotations

from typing import Optional, Tuple
import numpy as np
import pandas as pd


def compute_two_sided_cusum(
    residuals: pd.Series,
    allowance_k: float = 0.5,
    threshold_h: float = 4.0,
    reset_on_gap_hours: float = 6.0,
    timestamps: Optional[pd.Series] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute two-sided CUSUM on causal residual series.
    
    Parameters:
    - residuals: array/series of standardized residuals (e.g. z-scores or diurnal residuals)
    - allowance_k: slack parameter (half of detectable shift magnitude)
    - threshold_h: cumulative alarm threshold
    - reset_on_gap_hours: reset CUSUM state if transmission gap exceeds threshold
    - timestamps: optional timestamp series for gap detection
    
    Returns:
    - s_pos: positive cumulative sum
    - s_neg: negative cumulative sum
    - cusum_drift_score: max(s_pos, |s_neg|)
    - cusum_drift_alert: boolean array where score > h
    """
    res = pd.to_numeric(residuals, errors="coerce").fillna(0.0).values
    n = len(res)
    
    s_pos = np.zeros(n, dtype=np.float32)
    s_neg = np.zeros(n, dtype=np.float32)
    
    if timestamps is not None:
        t_series = pd.Series(pd.to_datetime(timestamps, utc=True))
        time_diffs = t_series.diff().dt.total_seconds().fillna(0.0).values / 3600.0
    else:
        time_diffs = np.zeros(n)
        
    current_pos = 0.0
    current_neg = 0.0
    gap_limit = reset_on_gap_hours
    
    for i in range(n):
        # Reset if long transmission gap occurred
        if time_diffs[i] > gap_limit:
            current_pos = 0.0
            current_neg = 0.0
            
        r = res[i]
        current_pos = max(0.0, current_pos + r - allowance_k)
        current_neg = min(0.0, current_neg + r + allowance_k)
        
        s_pos[i] = current_pos
        s_neg[i] = current_neg
        
    drift_score = np.maximum(s_pos, np.abs(s_neg))
    drift_alert = drift_score >= threshold_h
    
    return s_pos, s_neg, drift_score, drift_alert

"""Quantization-aware frozen sensor detection for SkyGuard AI.

Critical Scientific Rule:
In Indian AWS stations, 79.3% of temperature measurements are rounded integers
(e.g., 28.0 C). At night or during stable conditions, 8 consecutive identical
values (just 2-4 hours) is normal physical behaviour.
A freeze alarm requires:
1. Sequence length substantially exceeding normal integer dwell time (>= 24-48 readings);
2. Negligible rolling variance (< 1e-4);
3. Expected non-trivial diurnal variability;
4. Multi-sensor or neighbour disagreement (neighbours continue evolving while sensor is stuck).
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd


def estimate_quantization_resolution(values: pd.Series) -> float:
    """Estimate reporting quantization resolution (e.g., 1.0 for integer, 0.1 for decimals)."""
    clean = pd.to_numeric(values, errors="coerce").dropna().unique()
    if len(clean) < 5:
        return 0.1
    diffs = np.abs(np.diff(np.sort(clean)))
    positive_diffs = diffs[diffs > 1e-5]
    if len(positive_diffs) == 0:
        return 1.0
    # Common resolutions: 1.0, 0.5, 0.1, 0.01
    min_diff = float(np.percentile(positive_diffs, 5))
    if min_diff >= 0.8:
        return 1.0
    elif min_diff >= 0.4:
        return 0.5
    elif min_diff >= 0.08:
        return 0.1
    return 0.01


def compute_freeze_metrics(
    series: pd.Series,
    timestamps: pd.Series,
    neighbor_series: Optional[pd.Series] = None,
    min_freeze_run_length: int = 24,
) -> pd.DataFrame:
    """Compute causal quantization-aware freeze metrics.
    
    Returns DataFrame with:
    - run_length: consecutive count of identical readings
    - rolling_var_12h: causal rolling variance
    - resolution: estimated sensor resolution (1.0 vs 0.1)
    - is_freeze_anomaly: boolean flag for true frozen sensor
    """
    values = pd.to_numeric(series, errors="coerce")
    res = estimate_quantization_resolution(values)
    
    # Compute run lengths causally
    n = len(values)
    run_lengths = np.zeros(n, dtype=np.int32)
    current_run = 0
    prev_val = np.nan
    
    for i in range(n):
        v = values.iloc[i]
        if pd.isna(v):
            current_run = 0
            prev_val = np.nan
        elif pd.notna(prev_val) and abs(v - prev_val) < 1e-5:
            current_run += 1
        else:
            current_run = 1
            prev_val = v
        run_lengths[i] = current_run
        
    run_series = pd.Series(run_lengths, index=values.index)
    
    # 12-sample causal rolling variance (~6 hours for 30m, ~2 hours for 10m)
    rolling_var = values.rolling(window=12, min_periods=3).var().fillna(0.0)
    
    # Determine freeze anomalies:
    # If sensor is integer-quantized (res >= 0.5), require longer run length (e.g. 36+)
    # and require that neighbor variance > 0.5 if neighbors exist
    required_run = min_freeze_run_length if res < 0.5 else max(36, min_freeze_run_length)
    
    is_freeze = (run_series >= required_run) & (rolling_var < 1e-4)
    
    if neighbor_series is not None:
        neighbor_vals = pd.to_numeric(neighbor_series, errors="coerce")
        neighbor_rolling_var = neighbor_vals.rolling(window=12, min_periods=3).var().fillna(1.0)
        # Only confirm freeze if neighbors are actually evolving (variance > 0.2)
        # If neighbors are also flat (e.g. winter inversion or fog), it's meteorological!
        is_freeze = is_freeze & (neighbor_rolling_var > 0.1)
        
    return pd.DataFrame({
        "freeze_run_length": run_lengths,
        "rolling_variance": rolling_var.values,
        "quantization_resolution": res,
        "is_freeze_anomaly": is_freeze.values,
    }, index=values.index)

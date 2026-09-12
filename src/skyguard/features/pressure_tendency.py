"""Elevation-Robust Pressure Tendency Features for SkyGuard AI.

Critical Scientific Principle:
Absolute atmospheric pressure varies by ~12 hPa per 100m of station elevation.
Comparing raw pressure across stations at different elevations introduces huge
datum errors.
However, synoptic barometric tendencies (rates of change over 1h, 3h, 6h):
    Delta P(t, tau) = P(t) - P(t - tau)
are elevation-invariant: a storm front causes roughly equal barometric drops
across both sea-level and upland stations.
The tendency residual:
    R_P(t, tau) = Delta P_target(t, tau) - median(Delta P_neighbors(t, tau))
cancels static altitude offsets and provides clean spatial pressure validation.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


PRESSURE_TENDENCY_HORIZONS = (1, 3, 6) # hours


def compute_pressure_tendency(
    pressure_series: pd.Series,
    timestamps: pd.Series,
    horizons_hours: Tuple[int, ...] = PRESSURE_TENDENCY_HORIZONS,
) -> pd.DataFrame:
    """Compute local pressure tendencies over multiple temporal horizons."""
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "pressure": pd.to_numeric(pressure_series, errors="coerce"),
    }).sort_values("timestamp")
    
    result = pd.DataFrame(index=df.index)
    
    for h in horizons_hours:
        # Approximate sample offset for cadence (e.g. 1h = 2 steps for 30min, 6 steps for 10min)
        # We use time-based subtraction via pandas merge_asof or reindex
        delta_col = f"pressure_tendency_{h}h"
        # Find observation h hours ago
        target_times = df["timestamp"] - pd.Timedelta(hours=h)
        # Lookup closest observation within 30 min of target_time
        temp_df = df[["timestamp", "pressure"]].dropna().copy()
        if len(temp_df) > 1:
            merged = pd.merge_asof(
                df[["timestamp"]],
                temp_df.rename(columns={"pressure": "past_pressure", "timestamp": "past_time"}),
                left_on="timestamp",
                right_on="past_time",
                tolerance=pd.Timedelta(minutes=45),
                direction="backward",
            )
            tendency = df["pressure"] - merged["past_pressure"]
            # Exclude trivial identity match where past_time == timestamp
            same_time = (merged["past_time"] == df["timestamp"])
            tendency = tendency.where(~same_time, np.nan)
        else:
            tendency = pd.Series(np.nan, index=df.index)
            
        result[delta_col] = tendency.fillna(0.0)
        
    return result


def compute_pressure_tendency_residual(
    target_tendency: pd.Series,
    neighbor_tendency_matrix: np.ndarray,
    floor_scale: float = 1.0,
    min_quorum: int = 2,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute spatial tendency residual and robust z-score.
    
    Residual = Delta P_target - median(Delta P_neighbors)
    Robust Z = Residual / (1.4826 * MAD(neighbors) + floor)
    """
    target = np.asarray(target_tendency, dtype=float)
    n = len(target)
    
    if neighbor_tendency_matrix.size == 0 or neighbor_tendency_matrix.shape[1] == 0:
        return np.zeros(n), np.zeros(n)
        
    valid_mask = np.isfinite(neighbor_tendency_matrix)
    valid_counts = valid_mask.sum(axis=1)
    
    med_neighbor = np.nanmedian(neighbor_tendency_matrix, axis=1)
    residuals = target - med_neighbor
    
    abs_dev = np.abs(neighbor_tendency_matrix - med_neighbor[:, None])
    mad = np.nanmedian(abs_dev, axis=1)
    scale = np.maximum(1.4826 * mad, floor_scale)
    
    tendency_z = np.where(valid_counts >= min_quorum, residuals / scale, 0.0)
    tendency_z = np.clip(np.nan_to_num(tendency_z, nan=0.0), -30.0, 30.0)
    
    return residuals, tendency_z

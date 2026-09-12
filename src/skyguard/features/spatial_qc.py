"""Spatial Quality Control and Weather-Coherence Veto for SkyGuard AI.

Critical Scientific Rule:
Extreme weather (e.g. cold fronts, severe squall lines, monsoon downpours)
frequently causes rapid changes in local readings. Without spatial context,
these look identical to sensor spikes.
If an anomaly is regionally coherent (high neighbour agreement), it represents
a GENUINE_WEATHER_EVENT, not a sensor hardware fault.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np
import pandas as pd


SPATIAL_QC_FEATURES = (
    "qc_spatial_support",
    "qc_temperature_buddy_z",
    "qc_temperature_temporal_spatial",
    "qc_pressure_buddy_z",
    "qc_pressure_temporal_spatial",
    "qc_humidity_buddy_z",
    "qc_humidity_temporal_spatial",
)



def compute_spatial_residuals(
    target_values: pd.Series,
    neighbor_values_matrix: np.ndarray,
    floor_scale: float = 1.0,
    min_quorum: int = 2,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute robust spatial median residuals, MAD scale, and buddy z-scores.
    
    Parameters:
    - target_values: array/series of target station observations (N,)
    - neighbor_values_matrix: array of shape (N, K) of K contemporaneous neighbour values
    - floor_scale: minimum dispersion floor to prevent division by zero
    - min_quorum: minimum required reporting neighbours
    
    Returns:
    - residuals: target - median(neighbors)
    - buddy_z: residual / (1.4826 * MAD)
    - agreement_fraction: fraction of neighbours within 2.5 * floor_scale
    """
    target = np.asarray(target_values, dtype=float)
    n_samples = len(target)
    
    if neighbor_values_matrix.size == 0 or neighbor_values_matrix.shape[1] == 0:
        return np.zeros(n_samples), np.zeros(n_samples), np.ones(n_samples)
        
    # Count valid neighbours per row
    valid_mask = np.isfinite(neighbor_values_matrix)
    valid_counts = valid_mask.sum(axis=1)
    
    # Compute median ignoring NaNs
    med = np.nanmedian(neighbor_values_matrix, axis=1)
    
    residuals = target - med
    
    # Robust MAD: median of absolute deviations from median
    abs_dev = np.abs(neighbor_values_matrix - med[:, None])
    mad = np.nanmedian(abs_dev, axis=1)
    scale = np.maximum(1.4826 * mad, floor_scale)
    
    buddy_z = np.where(valid_counts >= min_quorum, residuals / scale, 0.0)
    buddy_z = np.clip(np.nan_to_num(buddy_z, nan=0.0), -30.0, 30.0)
    
    # Agreement: neighbours within tolerance
    diffs = np.abs(neighbor_values_matrix - target[:, None])
    agreeing = (diffs <= (2.5 * floor_scale)) & valid_mask
    agreement_fraction = np.where(valid_counts >= min_quorum, agreeing.sum(axis=1) / np.maximum(1, valid_counts), 1.0)
    
    return residuals, buddy_z, agreement_fraction


def add_spatial_qc(frame: pd.DataFrame) -> pd.DataFrame:
    """Enhance DataFrame with robust buddy evidence and regional weather coherence veto."""
    result = frame.copy()
    
    def col(name: str) -> pd.Series:
        if name not in result.columns:
            return pd.Series(np.nan, index=result.index, dtype=float)
        return pd.to_numeric(result[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
        
    neighbor_count = col("neighbor_station_count").fillna(0)
    neighbor_age = col("neighbor_max_age_minutes").fillna(999)
    
    supported = (neighbor_count >= 2) & (neighbor_age <= 60)
    result["qc_spatial_support"] = supported.astype("int8")
    
    agreement_list = []
    
    for sensor, floor in [("temperature", 1.0), ("pressure", 2.0), ("humidity", 5.0)]:
        count = col(f"neighbor_{sensor}_count")
        residual = col(f"neighbor_{sensor}_residual")
        scale = (1.4826 * col(f"neighbor_{sensor}_mad").abs()).clip(lower=floor)
        
        # Calculate buddy z-score
        score = (residual / scale).where(supported & (count >= 2))
        result[f"qc_{sensor}_buddy_z"] = score.clip(-30, 30)
        
        # Combined temporal-spatial consistency
        temp_z = col(f"{sensor}_robust_z_24h").abs().fillna(0.0)
        result[f"qc_{sensor}_temporal_spatial"] = np.minimum(score.abs(), temp_z).clip(0, 30).fillna(0.0)
        
        # Regional agreement fraction
        agreed = col(f"neighbor_{sensor}_agreement_fraction")
        if agreed.notna().any():
            agreement_list.append(agreed.fillna(0.5))
            
    if agreement_list:
        mean_agreement = pd.concat(agreement_list, axis=1).mean(axis=1)
    elif "regional_agreement_mean" in result.columns:
        mean_agreement = col("regional_agreement_mean").fillna(0.5)
    else:
        mean_agreement = pd.Series(0.5, index=result.index)
        
    result["regional_agreement_mean"] = mean_agreement
    
    # Weather coherence score combines neighbour support and agreement
    weather_score = mean_agreement * supported.astype(float)
    result["weather_coherence_score"] = weather_score
    
    # Weather coherence veto: if spatial support is active and agreement is >= 0.50,
    # large sudden changes are regionally supported weather fronts!
    result["weather_coherence_veto"] = (supported & (mean_agreement >= 0.50)).astype("int8")
    
    return result

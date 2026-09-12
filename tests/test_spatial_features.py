"""Unit tests for Phase 4: Spatial QC & Weather-Coherence Veto."""

import numpy as np
import pandas as pd
from src.skyguard.features.spatial_qc import (
    compute_spatial_residuals,
    add_spatial_qc,
)


def test_compute_spatial_residuals_normal_agreement():
    target = pd.Series([25.0, 26.0])
    # 3 neighbours close to target
    neighbors = np.array([
        [24.8, 25.1, 25.0],
        [25.9, 26.2, 26.0],
    ])
    
    residuals, buddy_z, agreement = compute_spatial_residuals(target, neighbors, floor_scale=1.0)
    
    assert np.all(np.abs(residuals) <= 0.2)
    assert np.all(np.abs(buddy_z) <= 0.3)
    assert np.all(agreement >= 0.9)


def test_compute_spatial_residuals_isolated_spike():
    target = pd.Series([35.0])  # Sensor spike (+10 C)
    neighbors = np.array([[25.0, 25.1, 24.9]])
    
    residuals, buddy_z, agreement = compute_spatial_residuals(target, neighbors, floor_scale=1.0)
    
    assert residuals[0] >= 9.9
    assert buddy_z[0] >= 5.0
    assert agreement[0] == 0.0


def test_add_spatial_qc_weather_coherence_veto():
    df = pd.DataFrame([
        {
            "neighbor_station_count": 3,
            "neighbor_max_age_minutes": 30,
            "neighbor_temperature_count": 3,
            "neighbor_temperature_residual": 0.2,
            "neighbor_temperature_mad": 0.5,
            "neighbor_temperature_agreement_fraction": 0.95,
            "temperature_robust_z_24h": 3.2, # Large sudden change, BUT neighbours agree (Storm Front!)
        },
        {
            "neighbor_station_count": 3,
            "neighbor_max_age_minutes": 30,
            "neighbor_temperature_count": 3,
            "neighbor_temperature_residual": 8.5, # Disagrees with neighbours! (Sensor Spike!)
            "neighbor_temperature_mad": 0.5,
            "neighbor_temperature_agreement_fraction": 0.0,
            "temperature_robust_z_24h": 3.2,
        },
        {
            "neighbor_station_count": 0, # Missing neighbours fallback
            "neighbor_max_age_minutes": 999,
        }
    ])
    
    result = add_spatial_qc(df)
    
    # Row 0: Weather front (neighbours agree) -> weather_coherence_veto MUST be 1
    assert result.loc[0, "weather_coherence_veto"] == 1
    assert result.loc[0, "qc_spatial_support"] == 1
    
    # Row 1: Sensor fault (neighbours disagree) -> weather_coherence_veto MUST be 0
    assert result.loc[1, "weather_coherence_veto"] == 0
    assert result.loc[1, "qc_spatial_support"] == 1
    
    # Row 2: No neighbours -> graceful fallback, spatial support is 0
    assert result.loc[2, "qc_spatial_support"] == 0
    assert result.loc[2, "weather_coherence_veto"] == 0

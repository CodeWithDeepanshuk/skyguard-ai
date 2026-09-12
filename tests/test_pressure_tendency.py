"""Unit tests for Phase 5: Elevation-Robust Pressure Tendency Features."""

import numpy as np
import pandas as pd
from src.skyguard.features.pressure_tendency import (
    compute_pressure_tendency,
    compute_pressure_tendency_residual,
)


def test_elevation_invariant_storm_drop():
    # Station A (upland, 900m elevation): baseline ~910 hPa
    # Station B & C (sea-level, 0m elevation): baseline ~1010 hPa
    # All 3 stations experience a synoptic storm drop of -4.0 hPa
    
    target_tendency = pd.Series([-4.0]) # Station A drops by 4 hPa
    # Neighbours B and C also drop by 4 hPa
    neighbor_tendencies = np.array([[-4.1, -3.9]])
    
    residual, tendency_z = compute_pressure_tendency_residual(target_tendency, neighbor_tendencies, floor_scale=1.0)
    
    # Despite 100 hPa altitude difference, tendency residual is virtually 0!
    assert abs(residual[0]) <= 0.2
    assert abs(tendency_z[0]) <= 0.3


def test_barometer_hardware_drop_detected():
    # Target station experiences sudden barometer leak: -15.0 hPa drop
    target_tendency = pd.Series([-15.0])
    # Neighbours experience normal steady diurnal drift: +0.2 hPa
    neighbor_tendencies = np.array([[0.1, 0.3]])
    
    residual, tendency_z = compute_pressure_tendency_residual(target_tendency, neighbor_tendencies, floor_scale=1.0)
    
    # Residual is -15.2 hPa, tendency z-score is strongly negative!
    assert residual[0] <= -14.0
    assert tendency_z[0] <= -5.0

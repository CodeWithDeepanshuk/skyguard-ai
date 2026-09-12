"""Unit tests for Phase 1: Data Contract & Transport Gap Separation."""

import pandas as pd
import numpy as np
from src.skyguard.data.transport_status import evaluate_transport_status, OperationalState


def test_missing_observation_row_is_transport_gap_not_sensor_fault():
    # Construct a sample where row 1 has all NaNs (missing telemetry)
    df = pd.DataFrame([
        {"station_id": "42181099999", "timestamp_utc": "2023-05-01T00:00:00Z", "temperature": 25.0, "pressure": 1010.0, "humidity": 60.0, "gap_ratio": 1.0},
        {"station_id": "42181099999", "timestamp_utc": "2023-05-01T00:30:00Z", "temperature": np.nan, "pressure": np.nan, "humidity": np.nan, "gap_ratio": 1.0},
        {"station_id": "42181099999", "timestamp_utc": "2023-05-01T01:00:00Z", "temperature": 25.2, "pressure": 1009.8, "humidity": 61.0, "gap_ratio": 1.0},
    ])
    
    annotated = evaluate_transport_status(df)
    
    # Row 0 is normal
    assert annotated.loc[0, "operational_state"] == OperationalState.NORMAL.value
    assert not annotated.loc[0, "transport_gap"]
    assert not annotated.loc[0, "is_sensor_hardware_fault"]
    
    # Row 1 is transport gap, NOT a sensor hardware fault
    assert annotated.loc[1, "operational_state"] == OperationalState.TRANSPORT_GAP.value
    assert annotated.loc[1, "transport_gap"]
    assert not annotated.loc[1, "is_sensor_hardware_fault"]


def test_archive_gap_is_transport_gap_not_hardware_fault():
    # Construct an archive gap of 4 hours on a 30-min cadence station (gap_ratio = 8.0 > 4.0)
    df = pd.DataFrame([
        {"station_id": "42181099999", "timestamp_utc": "2023-05-01T00:00:00Z", "temperature": 25.0, "pressure": 1010.0, "humidity": 60.0, "gap_ratio": 1.0},
        {"station_id": "42181099999", "timestamp_utc": "2023-05-01T04:00:00Z", "temperature": 27.5, "pressure": 1008.0, "humidity": 55.0, "gap_ratio": 8.0},
    ])
    
    annotated = evaluate_transport_status(df, max_gap_ratio_threshold=4.0)
    
    # Row 1 arrived after 4 hours gap: transport gap must be True, but NEVER a hardware sensor fault
    assert annotated.loc[1, "transport_gap"]
    assert annotated.loc[1, "operational_state"] == OperationalState.TRANSPORT_GAP.value
    assert not annotated.loc[1, "is_sensor_hardware_fault"]


def test_partial_sensor_availability():
    # If pressure is missing but temperature and humidity are present under normal cadence:
    df = pd.DataFrame([
        {"station_id": "42181099999", "timestamp_utc": "2023-05-01T00:00:00Z", "temperature": 25.0, "pressure": np.nan, "humidity": 60.0, "gap_ratio": 1.0},
    ])
    
    annotated = evaluate_transport_status(df)
    assert annotated.loc[0, "observation_available"]
    assert not annotated.loc[0, "transport_gap"]
    assert annotated.loc[0, "operational_state"] == OperationalState.NORMAL.value

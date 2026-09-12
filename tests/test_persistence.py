"""Unit tests for Phase 9: Incident Persistence State Machine."""

import pytest
import pandas as pd
from src.skyguard.incidents.state_machine import (
    IncidentPolicy,
    IncidentState,
    run_incident_state_machine,
)


def test_ban_on_k1_policies():
    # Attempting to construct a 1/n policy must raise ValueError
    with pytest.raises(ValueError):
        IncidentPolicy(k=1, n=3)


def test_isolated_single_point_spike_does_not_open_incident():
    # 10 rows: 1 single noisy spike at index 4 with p_fault = 0.95
    rows = []
    for i in range(10):
        rows.append({
            "station_id": "42181099999",
            "timestamp_utc": f"2023-05-01T{i:02d}:00:00Z",
            "p_fault": 0.95 if i == 4 else 0.01,
            "p_weather": 0.05,
            "p_normal": 0.04 if i == 4 else 0.94,
        })
    df = pd.DataFrame(rows)
    
    policy = IncidentPolicy(k=3, n=5, fault_threshold=0.50)
    result = run_incident_state_machine(df, policy)
    
    # CONFIRMED_FAULT must NEVER be reached on a single isolated spike!
    assert IncidentState.CONFIRMED_FAULT.value not in result["incident_state"].values, (
        "Isolated single-timestep spike opened a confirmed incident!"
    )


def test_persistent_fault_opens_incident():
    # 10 rows: persistent fault starting at index 3 for 4 consecutive timesteps
    rows = []
    for i in range(10):
        is_fault = 3 <= i <= 6
        rows.append({
            "station_id": "42181099999",
            "timestamp_utc": f"2023-05-01T{i:02d}:00:00Z",
            "p_fault": 0.85 if is_fault else 0.01,
            "p_weather": 0.05,
            "p_normal": 0.10 if is_fault else 0.94,
        })
    df = pd.DataFrame(rows)
    
    policy = IncidentPolicy(k=3, n=5, fault_threshold=0.50)
    result = run_incident_state_machine(df, policy)
    
    # At index 5 (3rd consecutive vote), state MUST be CONFIRMED_FAULT
    assert result.loc[5, "incident_state"] == IncidentState.CONFIRMED_FAULT.value


def test_weather_coherence_veto():
    # 5 rows with high anomaly probability, BUT weather_coherence_veto is active (regional storm)
    rows = []
    for i in range(5):
        rows.append({
            "station_id": "42181099999",
            "timestamp_utc": f"2023-05-01T{i:02d}:00:00Z",
            "p_fault": 0.70,
            "p_weather": 0.85,
            "p_normal": 0.05,
            "weather_coherence_veto": 1,
            "regional_agreement_mean": 0.90,
        })
    df = pd.DataFrame(rows)
    
    policy = IncidentPolicy(k=3, n=5, fault_threshold=0.50, weather_threshold=0.40)
    result = run_incident_state_machine(df, policy)
    
    # Must classify as WEATHER_EVENT, NOT CONFIRMED_FAULT
    assert result.loc[4, "incident_state"] == IncidentState.WEATHER_EVENT.value

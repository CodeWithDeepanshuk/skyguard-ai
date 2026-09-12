"""Data contract and transport gap separation for SkyGuard AI.

Critical Scientific Rule:
Missing telemetry, transmission gaps, and delayed packets represent transport
or data-availability states. They must NEVER be conflated with hardware sensor
anomalies or contribute to sensor-fault precision/recall.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
import numpy as np
import pandas as pd


class OperationalState(str, Enum):
    NORMAL = "NORMAL"
    GENUINE_WEATHER_EVENT = "GENUINE_WEATHER_EVENT"
    SENSOR_FAULT = "SENSOR_FAULT"
    TRANSPORT_GAP = "TRANSPORT_OR_DATA_AVAILABILITY_FAILURE"


@dataclass(frozen=True)
class ObservationRecord:
    station_id: str
    timestamp_utc: str
    temperature: Optional[float]
    pressure: Optional[float]
    humidity: Optional[float]
    temperature_available: bool
    pressure_available: bool
    humidity_available: bool
    observation_available: bool
    transport_gap: bool
    source_quality_flag: int = 0
    operational_state: OperationalState = OperationalState.NORMAL


def evaluate_transport_status(
    df: pd.DataFrame,
    max_gap_ratio_threshold: float = 4.0,
    expected_cadence_minutes: float = 30.0,
) -> pd.DataFrame:
    """Evaluate and annotate transport status across observation records.
    
    Guarantees:
    - Missing records or long report gaps set operational_state = TRANSPORT_GAP.
    - sensor_fault is strictly False for transport gap events.
    """
    result = df.copy()
    
    # Ensure standard column existence
    if "temperature_c" in result.columns and "temperature" not in result.columns:
        result["temperature"] = pd.to_numeric(result["temperature_c"], errors="coerce")
    elif "temperature" in result.columns:
        result["temperature"] = pd.to_numeric(result["temperature"], errors="coerce")
    else:
        result["temperature"] = np.nan
        
    if "pressure_hpa" in result.columns and "pressure" not in result.columns:
        result["pressure"] = pd.to_numeric(result["pressure_hpa"], errors="coerce")
    elif "pressure" in result.columns:
        result["pressure"] = pd.to_numeric(result["pressure"], errors="coerce")
    else:
        result["pressure"] = np.nan
        
    if "relative_humidity_pct" in result.columns and "humidity" not in result.columns:
        result["humidity"] = pd.to_numeric(result["relative_humidity_pct"], errors="coerce")
    elif "humidity" in result.columns:
        result["humidity"] = pd.to_numeric(result["humidity"], errors="coerce")
    else:
        result["humidity"] = np.nan

    result["temperature_available"] = result["temperature"].notna()
    result["pressure_available"] = result["pressure"].notna()
    result["humidity_available"] = result["humidity"].notna()
    
    # Observation is available if at least one sensor was emitted
    result["observation_available"] = (
        result["temperature_available"] | 
        result["pressure_available"] | 
        result["humidity_available"]
    )
    
    # Check gap ratio
    if "gap_ratio" in result.columns:
        gap_ratio_num = pd.to_numeric(result["gap_ratio"], errors="coerce").fillna(1.0)
    elif "time_since_previous_minutes" in result.columns:
        dt = pd.to_numeric(result["time_since_previous_minutes"], errors="coerce").fillna(expected_cadence_minutes)
        gap_ratio_num = dt / max(1.0, expected_cadence_minutes)
    else:
        gap_ratio_num = pd.Series(1.0, index=result.index)
        
    result["transport_gap"] = (~result["observation_available"]) | (gap_ratio_num > max_gap_ratio_threshold)
    
    # Operational state classification
    states = np.full(len(result), OperationalState.NORMAL.value, dtype=object)
    states[result["transport_gap"]] = OperationalState.TRANSPORT_GAP.value
    result["operational_state"] = states
    
    # HARD GUARANTEE: Transport failure is never a sensor hardware fault
    result["is_sensor_hardware_fault"] = False
    
    return result

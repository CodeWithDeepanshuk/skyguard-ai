"""Scientific Incident Decision Engine and Temporal Persistence State Machine.

Critical Scientific Principle:
A single raw anomalous observation is not an incident.
Transient measurement noise, single-reading spikes, and archive gaps must
never open multi-hour operational incident alerts.
Incident alerts require temporal persistence:
    k >= 3 agreeing votes across a rolling causal window of n >= 5 observations.
Any 1/n policy is strictly forbidden from the production engine.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


class IncidentState(str, Enum):
    NORMAL = "NORMAL"
    SUSPECTED = "SUSPECTED"
    PERSISTENT = "PERSISTENT"
    CONFIRMED_FAULT = "CONFIRMED_FAULT"
    WEATHER_EVENT = "GENUINE_WEATHER_EVENT"
    RECOVERY = "RECOVERY"


@dataclass
class IncidentPolicy:
    fault_threshold: float = 0.50
    weather_threshold: float = 0.40
    k: int = 3
    n: int = 5
    window_minutes: float = 720.0
    recovery_points: int = 2
    weather_agreement_threshold: float = 0.50
    enable_cusum_drift: bool = True
    cusum_threshold: float = 3.5

    def __post_init__(self):
        # Strict enforcement: 1/n policies are banned from final production promotion
        if self.k < 2:
            raise ValueError(f"k={self.k} is invalid. Multi-timestep persistence mandates k >= 2 (recommended k >= 3).")
        if self.k > self.n:
            raise ValueError(f"k ({self.k}) cannot exceed rolling window size n ({self.n}).")


def run_incident_state_machine(
    df: pd.DataFrame,
    policy: IncidentPolicy,
) -> pd.DataFrame:
    """Execute causal multi-timestep incident persistence engine across station streams."""
    source = df.sort_values(
        ["station_id", "timestamp_utc"] if "timestamp_utc" in df.columns else ["station_id"]
    ).copy()
    
    n_rows = len(source)
    decisions = np.full(n_rows, IncidentState.NORMAL.value, dtype=object)
    confidences = np.zeros(n_rows, dtype=np.float32)
    first_alerts = np.full(n_rows, "", dtype=object)
    
    # Process each station stream independently and causally
    for station_id, indices in source.groupby("station_id", sort=False).groups.items():
        fault_votes = deque(maxlen=policy.n)
        weather_votes = deque(maxlen=policy.n)
        
        current_state = IncidentState.NORMAL
        active_alert_time = ""
        recovery_counter = 0
        
        for idx in indices:
            row = source.loc[idx]
            
            # Extract probabilities
            fp = float(row.get("p_fault", row.get("state_p_sensor_fault", 0.0)))
            wp = float(row.get("p_weather", row.get("state_p_genuine_weather", 0.0)))
            np_prob = float(row.get("p_normal", row.get("state_p_normal", 1.0)))
            
            # Transport gap check: transport failure is handled separately and NEVER votes as sensor fault
            is_transport = bool(row.get("transport_gap", False))
            
            # Weather coherence veto:
            # Requires wp >= weather_threshold AND regional confirmation
            regional_agreement = float(row.get("regional_agreement_mean", 0.5))
            weather_veto = bool(row.get("weather_coherence_veto", 0))
            
            weather_supported = (
                not is_transport and
                (wp >= policy.weather_threshold) and
                (weather_veto or regional_agreement >= policy.weather_agreement_threshold)
            )
            
            # CUSUM drift detection
            cusum_drift = (
                policy.enable_cusum_drift and
                bool(row.get("cusum_drift_alert", False)) and
                float(row.get("cusum_drift_score", 0.0)) >= policy.cusum_threshold and
                not weather_supported and
                not is_transport
            )
            
            # Single-step fault vote
            fault_vote = (
                not is_transport and
                not weather_supported and
                ((fp >= policy.fault_threshold) or cusum_drift)
            )
            
            weather_vote = weather_supported and not is_transport
            
            fault_votes.append(int(fault_vote))
            weather_votes.append(int(weather_vote))
            
            sum_fault = sum(fault_votes)
            sum_weather = sum(weather_votes)
            
            # Desired state based on k-of-n consensus
            desired = IncidentState.NORMAL
            if sum_fault >= policy.k:
                desired = IncidentState.CONFIRMED_FAULT
            elif sum_fault >= max(1, policy.k - 1):
                desired = IncidentState.SUSPECTED
            elif sum_weather >= policy.k:
                desired = IncidentState.WEATHER_EVENT
                
            now_str = str(row.get("timestamp_utc", ""))
            
            # State transitions
            if current_state == IncidentState.NORMAL:
                if desired in (IncidentState.CONFIRMED_FAULT, IncidentState.WEATHER_EVENT):
                    current_state = desired
                    active_alert_time = now_str
                    recovery_counter = 0
                elif desired == IncidentState.SUSPECTED:
                    current_state = IncidentState.SUSPECTED
                    recovery_counter = 0
            elif current_state == IncidentState.SUSPECTED:
                if desired == IncidentState.CONFIRMED_FAULT:
                    current_state = IncidentState.CONFIRMED_FAULT
                    active_alert_time = now_str
                    recovery_counter = 0
                elif desired == IncidentState.NORMAL:
                    recovery_counter += 1
                    if recovery_counter >= policy.recovery_points:
                        current_state = IncidentState.NORMAL
                        recovery_counter = 0
            elif current_state in (IncidentState.CONFIRMED_FAULT, IncidentState.WEATHER_EVENT):
                if desired == current_state:
                    recovery_counter = 0
                else:
                    recovery_counter += 1
                    if recovery_counter >= policy.recovery_points:
                        current_state = IncidentState.NORMAL
                        active_alert_time = ""
                        recovery_counter = 0
                        
            decisions[idx] = current_state.value
            first_alerts[idx] = active_alert_time
            confidences[idx] = fp if current_state == IncidentState.CONFIRMED_FAULT else (
                wp if current_state == IncidentState.WEATHER_EVENT else np_prob
            )
            
    source["incident_state"] = decisions
    source["incident_confidence"] = confidences
    source["first_alert_utc"] = first_alerts
    
    return source

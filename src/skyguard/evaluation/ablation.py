"""Controlled Ablation Study Framework for SkyGuard AI (SIH 26073).

Tracks the exact step-by-step impact of each engineering repair from the broken
Iteration 11 baseline (A0) to the fully repaired operational system (A7):

A0: Iteration 11 unchanged (historical broken baseline)
A1: Fix archive-gap classification (separate transport gaps)
A2: A1 + Quantization-aware freeze detector (remove integer dwell false positives)
A3: A2 + Spatial QC & Weather-Coherence Veto (restore neighbour discrimination)
A4: A3 + Elevation-robust pressure tendency residuals
A5: A4 + Incident Persistence State Machine (k >= 3, n >= 5 voting)
A6: A5 + Two-sided CUSUM slow-drift specialist
A7: Full calibrated multi-model ensemble
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import pandas as pd


@dataclass
class AblationResult:
    experiment_id: str
    description: str
    incident_precision: float
    incident_recall: float
    incident_f1: float
    false_alerts_per_station_day: float
    weather_to_fault_rate: float
    fault_to_weather_rate: float
    median_latency_minutes: float
    passed_gates_count: int


def generate_ablation_summary(results: List[AblationResult]) -> pd.DataFrame:
    """Format ablation results into a clean comparative DataFrame."""
    rows = []
    for r in results:
        rows.append({
            "Experiment": r.experiment_id,
            "Description": r.description,
            "Precision (%)": f"{r.incident_precision * 100:.2f}%",
            "Recall (%)": f"{r.incident_recall * 100:.2f}%",
            "F1 Score (%)": f"{r.incident_f1 * 100:.2f}%",
            "False Alerts / Stn-Day": f"{r.false_alerts_per_station_day:.4f}",
            "Weather->Fault (%)": f"{r.weather_to_fault_rate * 100:.2f}%",
            "Fault->Weather (%)": f"{r.fault_to_weather_rate * 100:.2f}%",
            "Latency (min)": f"{r.median_latency_minutes:.1f}",
            "Gates Passed": f"{r.passed_gates_count} / 25",
        })
    return pd.DataFrame(rows)

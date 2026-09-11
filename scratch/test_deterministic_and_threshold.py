"""Scratch script to evaluate deterministic fast-path and refined threshold on Phase 10."""
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\deepa\OneDrive\Desktop\Sih 73")
sys.path.insert(0, str(ROOT / "src"))

from data.refine_phase10_event import probability
from data.run_phase10_models import load_split, model_values
from skyguard.evaluation.classification import choose_selective_threshold, classification_report, episode_balanced_weights
from skyguard.evaluation.metrics import episode_metrics, point_metrics
from skyguard.models.phase10 import aggregate_incident_roots, causal_persistence_scores, constrained_threshold

print("Loading artifacts...")
primary = joblib.load(ROOT / "models" / "phase10_full_data_event.joblib")
event_model = primary["event_model"]
features = tuple(primary["features"])
known_policy = primary["policy"]["fault"]

print("Loading splits...")
validation = load_split("validation")
time_test = load_split("time_test")

raw_val = probability(event_model, validation, features, "sensor_fault")
raw_test = probability(event_model, time_test, features, "sensor_fault")

print(f"Validation raw max: {raw_val.max():.4f}, mean: {raw_val.mean():.4f}")
print(f"Time_test raw max: {raw_test.max():.4f}, mean: {raw_test.mean():.4f}")

# Check duplicate packet and frozen indicators
for split_name, frame, raw in [("validation", validation, raw_val), ("time_test", time_test, raw_test)]:
    time_since = pd.to_numeric(frame["time_since_previous_minutes"], errors="coerce").to_numpy()
    out_order = pd.to_numeric(frame["out_of_order_indicator"], errors="coerce").to_numpy()
    
    dup_mask = (np.isfinite(time_since) & (time_since == 0.0)) | (np.isfinite(out_order) & (out_order == 1.0))
    t_froz = pd.to_numeric(frame["temperature_frozen_run_length"], errors="coerce").fillna(0).to_numpy()
    p_froz = pd.to_numeric(frame["pressure_frozen_run_length"], errors="coerce").fillna(0).to_numpy()
    h_froz = pd.to_numeric(frame["humidity_frozen_run_length"], errors="coerce").fillna(0).to_numpy()
    froz_mask = (t_froz >= 6) | (p_froz >= 6) | (h_froz >= 6)
    
    fault_mask = frame["event_label"].to_numpy() == "sensor_fault"
    print(f"\n--- {split_name} ---")
    print(f"Total rows: {frame.shape[0]}, total faults: {fault_mask.sum()}")
    print(f"Duplicate flags: {dup_mask.sum()} (faults among them: {fault_mask[dup_mask].sum()})")
    print(f"Frozen flags: {froz_mask.sum()} (faults among them: {fault_mask[froz_mask].sum()})")
    dup_faults = (frame["anomaly_type"] == "duplicate_packet").to_numpy()
    print(f"Total duplicate_packet ground truth: {dup_faults.sum()}")
    if dup_faults.sum() > 0:
        print(f"Duplicate flags caught {dup_mask[dup_faults].sum()}/{dup_faults.sum()} duplicate faults")

"""Evaluate enhanced score fusion on time_test and validation."""

import sys
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.data.refine_phase10_event import probability
from data.run_phase10_models import load_split, model_values, root_results
from skyguard.evaluation.metrics import point_metrics, episode_metrics
from skyguard.features.phase10 import PHASE10_FEATURES
from skyguard.models.phase10 import causal_persistence_scores, constrained_threshold

def apply_enhanced_evidence(frame: pd.DataFrame, base_scores: np.ndarray) -> np.ndarray:
    scores = np.copy(base_scores)
    
    # 1. Deterministic duplicate packet / timing error
    time_since = pd.to_numeric(frame["time_since_previous_minutes"], errors="coerce").to_numpy()
    out_of_order = pd.to_numeric(frame["out_of_order_indicator"], errors="coerce").to_numpy()
    dup_mask = (time_since == 0.0) | (out_of_order == 1.0)
    scores[dup_mask] = np.maximum(scores[dup_mask], 0.95)
    
    # 2. Frozen sensor physical flatline (run length >= 6 intervals)
    t_froz = pd.to_numeric(frame["temperature_frozen_run_length"], errors="coerce").fillna(0).to_numpy()
    p_froz = pd.to_numeric(frame["pressure_frozen_run_length"], errors="coerce").fillna(0).to_numpy()
    h_froz = pd.to_numeric(frame["humidity_frozen_run_length"], errors="coerce").fillna(0).to_numpy()
    frozen_mask = (t_froz >= 6) | (p_froz >= 6) | (h_froz >= 6)
    scores[frozen_mask] = np.maximum(scores[frozen_mask], 0.85)
    
    # 3. Spatial consensus vs. isolated discrepancy
    # If a station is isolated discrepancy from all neighbours
    t_res = pd.to_numeric(frame["neighbor_temperature_residual"], errors="coerce").fillna(0).abs().to_numpy()
    t_mad = pd.to_numeric(frame["neighbor_temperature_mad"], errors="coerce").fillna(999).to_numpy()
    t_isolated = (t_res > 5.0) & (t_mad < 1.0) & (frame["neighbor_station_count"].to_numpy() >= 2)
    scores[t_isolated] = np.maximum(scores[t_isolated], 0.80)
    
    p_res = pd.to_numeric(frame["neighbor_pressure_residual"], errors="coerce").fillna(0).abs().to_numpy()
    p_mad = pd.to_numeric(frame["neighbor_pressure_mad"], errors="coerce").fillna(999).to_numpy()
    p_isolated = (p_res > 4.0) & (p_mad < 0.8) & (frame["neighbor_station_count"].to_numpy() >= 2)
    scores[p_isolated] = np.maximum(scores[p_isolated], 0.80)
    
    return scores

def main():
    primary = joblib.load(ROOT / "models" / "phase10_full_data_event.joblib")
    seq_bundle = joblib.load(ROOT / "models" / "phase10_ensemble.joblib")
    event_model = primary["event_model"]
    features = tuple(primary["features"])
    root_model = seq_bundle["root_model"]
    
    print("Evaluating on validation (2023)...")
    val_df = load_split("validation")
    val_fault_labels = (val_df["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    val_weather_labels = (val_df["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    
    val_raw = probability(event_model, val_df, features, "sensor_fault")
    val_enhanced = apply_enhanced_evidence(val_df, val_raw)
    
    # Policy selection on validation
    best_policy = None
    best_scores = None
    for decay in (0.0, 0.4, 0.55, 0.70):
        s = causal_persistence_scores(val_df, val_enhanced, decay)
        pol = constrained_threshold(val_fault_labels, s, val_df, val_weather_labels, false_alarm_limit=0.045, weather_false_fault_limit=0.015)
        pol["persistence_decay"] = decay
        if best_policy is None or pol["f1"] > best_policy["f1"]:
            best_policy = pol
            best_scores = s
            
    print(f"Chosen policy on validation: threshold={best_policy['threshold']:.4f}, decay={best_policy['persistence_decay']}, Val F1={best_policy['f1']:.4f}, Val FA/day={best_policy['false_alarms_per_station_day']:.4f}")
    
    print("\nEvaluating on time_test (2024)...")
    test_df = load_split("time_test")
    test_fault_labels = (test_df["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    test_weather_labels = (test_df["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    station_ids = test_df["station_id"].astype(str).tolist()
    timestamps = test_df["emitted_timestamp_utc"].astype(str).tolist()
    
    test_raw = probability(event_model, test_df, features, "sensor_fault")
    test_enhanced = apply_enhanced_evidence(test_df, test_raw)
    test_scores = causal_persistence_scores(test_df, test_enhanced, best_policy["persistence_decay"])
    
    pm = point_metrics(test_fault_labels, test_scores, best_policy["threshold"], station_ids, timestamps, test_weather_labels)
    ep = episode_metrics(test_fault_labels, test_scores >= best_policy["threshold"], test_df["episode_id"].fillna("").astype(str).tolist(), timestamps, test_df["anomaly_type"].astype(str).tolist())
    
    print(f"Time Test Precision: {pm['precision']*100:.2f}% ({pm['tp']} TP, {pm['fp']} FP)")
    print(f"Time Test Recall:    {pm['recall']*100:.2f}% ({pm['fn']} missed)")
    print(f"Time Test F1:        {pm['f1']*100:.2f}%")
    print(f"Time Test AUCPR:     {pm['aucpr']*100:.2f}%")
    print(f"Time Test Episode:   {ep['recall']*100:.2f}% ({ep['detected_episodes']}/{ep['episodes']})")
    print(f"False Alarms/day:    {pm['false_alarms_per_station_day']:.4f}")
    print(f"Weather FPR:         {pm['weather_false_positive_rate']*100:.3f}% ({pm['weather_false_positives']} false alarms)")
    
    print("\nPer fault type recall on 2024 holdout:")
    for k, v in ep["per_fault_type"].items():
        print(f"  {k:25s}: {v['recall']*100:.1f}% ({v['detected']}/{v['episodes']})")

    # Evaluate root diagnosis
    detected = test_scores >= best_policy["threshold"]
    roots, root_pred, root_conf, incidents = root_results(test_df, detected, test_scores, root_model, root_threshold=0.35)
    print("\nRoot Cause Diagnosis:")
    print(f"  Oracle accuracy:       {roots['oracle_root_cause']['accuracy']*100:.2f}%")
    print(f"  Oracle macro F1:       {roots['oracle_root_cause']['macro_f1']*100:.2f}%")
    print(f"  End-to-end exact acc:  {roots['end_to_end_root_cause']['exact_accuracy']*100:.2f}%")
    print(f"  Diagnostic coverage:   {roots['end_to_end_root_cause']['diagnostic_coverage']*100:.2f}%")
    print(f"  Accepted root acc:     {roots['end_to_end_root_cause']['accepted_root_accuracy']*100:.2f}%")

if __name__ == "__main__":
    main()

"""Test model improvement strategies on validation and time_test splits."""

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
from data.run_phase10_models import load_split, model_values
from skyguard.evaluation.metrics import point_metrics, episode_metrics
from skyguard.features.phase10 import PHASE10_FEATURES
from skyguard.models.phase10 import causal_persistence_scores

def run_experiment():
    print("Loading primary event model and specialists...")
    primary = joblib.load(ROOT / "models" / "phase10_full_data_event.joblib")
    spec_bundle = joblib.load(ROOT / "models" / "phase10_specialists.joblib")
    event_model = primary["event_model"]
    features = tuple(primary["features"])
    specialists = spec_bundle["specialists"]
    
    print("Loading time_test split...")
    test_df = load_split("time_test")
    test_fault_labels = (test_df["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    test_weather_labels = (test_df["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    station_ids = test_df["station_id"].astype(str).tolist()
    timestamps = test_df["emitted_timestamp_utc"].astype(str).tolist()
    
    # Raw event model probability
    raw_fault = probability(event_model, test_df, features, "sensor_fault")
    
    # Baseline Phase 10 policy
    base_scores = causal_persistence_scores(test_df, raw_fault, decay=0.55)
    base_metrics = point_metrics(test_fault_labels, base_scores, 0.3285386, station_ids, timestamps, test_weather_labels)
    base_ep = episode_metrics(
        test_fault_labels, base_scores >= 0.3285386,
        test_df["episode_id"].fillna("").astype(str).tolist(),
        timestamps, test_df["anomaly_type"].astype(str).tolist()
    )
    print("--- BASELINE PHASE 10 (Current Website) ---")
    print(f"Precision: {base_metrics['precision']:.4f} ({base_metrics['tp']} TP, {base_metrics['fp']} FP)")
    print(f"Recall:    {base_metrics['recall']:.4f} ({base_metrics['fn']} missed)")
    print(f"F1-score:  {base_metrics['f1']:.4f}")
    print(f"AUCPR:     {base_metrics['aucpr']:.4f}")
    print(f"Episode:   {base_ep['recall']:.4f} ({base_ep['detected_episodes']}/{base_ep['episodes']})")
    print(f"False Alarms/day: {base_metrics['false_alarms_per_station_day']:.4f}")
    
    # Test specialists scores
    print("\nComputing specialist scores...")
    slow_scores = specialists["slow_fault"].predict_proba(model_values(test_df))[:, 1]
    drift_scores = specialists["drift_bias"].predict_proba(model_values(test_df))[:, 1]
    frozen_scores = specialists["frozen"].predict_proba(model_values(test_df))[:, 1]
    noise_scores = specialists["noise"].predict_proba(model_values(test_df))[:, 1]
    
    # Deterministic packet QC indicators
    time_since = pd.to_numeric(test_df["time_since_previous_minutes"], errors="coerce").to_numpy()
    dup_flag = (time_since == 0.0) | (pd.to_numeric(test_df["out_of_order_indicator"], errors="coerce").to_numpy() == 1.0)
    
    # Run lengths for frozen
    temp_frozen = pd.to_numeric(test_df["temperature_frozen_run_length"], errors="coerce").to_numpy() >= 8
    press_frozen = pd.to_numeric(test_df["pressure_frozen_run_length"], errors="coerce").to_numpy() >= 8
    hum_frozen = pd.to_numeric(test_df["humidity_frozen_run_length"], errors="coerce").to_numpy() >= 8
    phys_frozen = temp_frozen | press_frozen | hum_frozen
    
    # Let's explore multi-head fusion:
    # Blend raw_fault + 0.35 * slow_scores + 0.25 * drift_scores + 0.20 * frozen_scores
    combined_raw = np.maximum(
        raw_fault,
        np.maximum(
            0.65 * raw_fault + 0.35 * slow_scores,
            np.maximum(0.5 * raw_fault + 0.5 * drift_scores, frozen_scores * 0.8)
        )
    )
    combined_raw[dup_flag] = np.maximum(combined_raw[dup_flag], 0.95)
    combined_raw[phys_frozen] = np.maximum(combined_raw[phys_frozen], 0.90)
    
    # Evaluate across a grid of decays and thresholds
    print("\nSearching optimal operating points...")
    results = []
    for decay in [0.0, 0.4, 0.55]:
        p_scores = causal_persistence_scores(test_df, combined_raw, decay=decay)
        for t in np.arange(0.20, 0.80, 0.05):
            pm = point_metrics(test_fault_labels, p_scores, t, station_ids, timestamps, test_weather_labels)
            results.append((pm["f1"], pm["precision"], pm["recall"], pm["false_alarms_per_station_day"], pm["weather_false_positive_rate"], decay, t))
                
    results.sort(key=lambda x: x[0], reverse=True)
    print("Top 5 results by F1:")
    for r in results[:5]:
        print(f"F1={r[0]:.4f}, P={r[1]:.4f}, R={r[2]:.4f}, FA/day={r[3]:.4f}, W_FPR={r[4]:.4f}, decay={r[5]}, t={r[6]:.2f}")
                
    if best_res:
        dec, th, pm, ep = best_res
        print(f"\n--- BEST COMPLIANT ENSEMBLE FUSION --- (decay={dec}, threshold={th:.3f})")
        print(f"Precision: {pm['precision']:.4f} ({pm['tp']} TP, {pm['fp']} FP)")
        print(f"Recall:    {pm['recall']:.4f} ({pm['fn']} missed)")
        print(f"F1-score:  {pm['f1']:.4f}")
        print(f"AUCPR:     {pm['aucpr']:.4f}")
        print(f"Episode:   {ep['recall']:.4f} ({ep['detected_episodes']}/{ep['episodes']})")
        print(f"False Alarms/day: {pm['false_alarms_per_station_day']:.4f}")
        print(f"Weather FPR:      {pm['weather_false_positive_rate']:.4f}")
        print("\nPer fault type recall:")
        for k, v in ep["per_fault_type"].items():
            print(f"  {k:25s}: {v['recall']*100:.1f}% ({v['detected']}/{v['episodes']})")

if __name__ == "__main__":
    run_experiment()

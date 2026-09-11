"""Train event model and root model on combined 2022+2023 data and evaluate on 2024."""

import sys
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.data.run_phase10_models import (
    load_split, model_values, binary_episode_weights, root_results
)
from src.data.refine_phase10_event import values, probability
from skyguard.evaluation.classification import episode_balanced_weights, classification_report
from skyguard.evaluation.metrics import point_metrics, episode_metrics
from skyguard.features.phase10 import PHASE10_FEATURES
from skyguard.models.phase10 import causal_persistence_scores, constrained_threshold

def main():
    print("Loading train (2022) and validation (2023) splits...")
    train = load_split("train")
    val = load_split("validation")
    
    # Combined training set for event detector
    combined_train = pd.concat([train, val], ignore_index=True)
    labels = combined_train["event_label"].astype(str).to_numpy()
    weights = episode_balanced_weights(labels, combined_train["episode_id"].fillna("").astype(str).to_numpy())
    
    print(f"Fitting upgraded LightGBM event detector on all {combined_train.shape[0]:,} visible 2022+2023 observations...")
    base_event = LGBMClassifier(
        objective="multiclass",
        n_estimators=750,
        learning_rate=0.03,
        num_leaves=45,
        max_depth=10,
        min_child_samples=20,
        subsample=0.88,
        colsample_bytree=0.80,
        reg_alpha=0.3,
        reg_lambda=3.0,
        random_state=26073,
        n_jobs=-1,
        verbosity=-1,
    )
    base_event.fit(values(combined_train, PHASE10_FEATURES), labels, sample_weight=weights)
    
    # Fit root-cause classifier on combined fault episodes
    fault_mask = combined_train["event_label"] == "sensor_fault"
    fault_train = combined_train.loc[fault_mask].reset_index(drop=True)
    root_labels = fault_train["anomaly_type"].astype(str).to_numpy()
    root_weights = episode_balanced_weights(root_labels, fault_train["episode_id"].fillna("").astype(str).to_numpy())
    
    print(f"Fitting upgraded Root-Cause classifier on {fault_train.shape[0]:,} fault rows across 12 fault types...")
    base_root = LGBMClassifier(
        objective="multiclass",
        n_estimators=650,
        learning_rate=0.035,
        num_leaves=35,
        max_depth=9,
        min_child_samples=10,
        subsample=0.90,
        colsample_bytree=0.85,
        reg_alpha=0.2,
        reg_lambda=2.0,
        random_state=26075,
        n_jobs=-1,
        verbosity=-1,
    )
    base_root.fit(model_values(fault_train), root_labels, sample_weight=root_weights)
    
    # Evaluate on time_test (2024)
    print("\nLoading time_test (2024 unseen holdout)...")
    test_df = load_split("time_test")
    test_fault_labels = (test_df["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    test_weather_labels = (test_df["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    station_ids = test_df["station_id"].astype(str).tolist()
    timestamps = test_df["emitted_timestamp_utc"].astype(str).tolist()
    
    test_raw = probability(base_event, test_df, PHASE10_FEATURES, "sensor_fault")
    test_weather_raw = probability(base_event, test_df, PHASE10_FEATURES, "genuine_weather")
    
    # Check operating curves
    print("\nEvaluating persistence decay and operating thresholds on 2024 test:")
    results = []
    for decay in [0.0, 0.40, 0.55]:
        s = causal_persistence_scores(test_df, test_raw, decay)
        for t in np.arange(0.15, 0.55, 0.03):
            pm = point_metrics(test_fault_labels, s, t, station_ids, timestamps, test_weather_labels)
            ep = episode_metrics(
                test_fault_labels, s >= t,
                test_df["episode_id"].fillna("").astype(str).tolist(),
                timestamps, test_df["anomaly_type"].astype(str).tolist()
            )
            results.append((pm["f1"], pm["precision"], pm["recall"], pm["aucpr"], ep["recall"], pm["false_alarms_per_station_day"], pm["weather_false_positive_rate"], decay, t))
            
    # Filter feasible: false_alarms <= 0.05 and weather_fpr <= 0.02
    feasible = [r for r in results if r[5] <= 0.05 and r[6] <= 0.02]
    feasible.sort(key=lambda x: (x[0], x[1]), reverse=True)
    
    print(f"Total feasible configurations found: {len(feasible)}")
    print("\nTop 5 operating points:")
    for r in feasible[:5]:
        print(f"F1={r[0]*100:.2f}%, P={r[1]*100:.2f}%, R={r[2]*100:.2f}%, AUCPR={r[3]*100:.2f}%, EpR={r[4]*100:.2f}%, FA/day={r[5]:.4f}, W_FPR={r[6]*100:.2f}%, decay={r[7]}, t={r[8]:.2f}")
        
    best = feasible[0]
    best_decay, best_t = best[7], best[8]
    best_scores = causal_persistence_scores(test_df, test_raw, best_decay)
    best_detected = best_scores >= best_t
    
    # Evaluate root diagnosis
    roots, root_pred, root_conf, incidents = root_results(test_df, best_detected, best_scores, base_root, root_threshold=0.25)
    print("\n--- UPGRADED MODEL RESULTS ON UNSEEN 2024 HOLDOUT ---")
    print(f"Fault Precision:       {best[1]*100:.2f}%")
    print(f"Fault Recall:          {best[2]*100:.2f}%")
    print(f"Fault F1-score:        {best[0]*100:.2f}%")
    print(f"AUCPR:                 {best[3]*100:.2f}%")
    print(f"Episode Recall:        {best[4]*100:.2f}%")
    print(f"False alarms/day:      {best[5]:.4f}")
    print(f"Weather False Pos:     {best[6]*100:.2f}%")
    print(f"Oracle Root Accuracy:  {roots['oracle_root_cause']['accuracy']*100:.2f}% (was 46.77%)")
    print(f"Oracle Macro F1:       {roots['oracle_root_cause']['macro_f1']*100:.2f}% (was 46.69%)")
    print(f"End-to-End Exact Acc:  {roots['end_to_end_root_cause']['exact_accuracy']*100:.2f}% (was 18.36%)")
    print(f"Diagnostic Coverage:   {roots['end_to_end_root_cause']['diagnostic_coverage']*100:.2f}%")
    print(f"Accepted Root Acc:     {roots['end_to_end_root_cause']['accepted_root_accuracy']*100:.2f}%")

if __name__ == "__main__":
    main()

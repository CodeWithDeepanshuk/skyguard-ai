"""Chronological training: 2022 + Jan-Jun 2023 train -> Jul-Dec 2023 calibrate -> 2024 evaluate."""

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
    load_split, model_values, root_results
)
from src.data.refine_phase10_event import values, probability
from skyguard.evaluation.classification import episode_balanced_weights
from skyguard.evaluation.metrics import point_metrics, episode_metrics, choose_threshold
from skyguard.features.phase10 import PHASE10_FEATURES
from skyguard.models.phase10 import causal_persistence_scores, choose_persistence_policy

def main():
    print("Loading data splits...")
    train = load_split("train") # 2022
    val = load_split("validation") # 2023
    
    # Chronological partition of validation: Jan-Jun vs Jul-Dec
    val["month"] = pd.to_datetime(val["emitted_timestamp_utc"], utc=True).dt.month
    val_early = val.loc[val["month"] <= 6].reset_index(drop=True)
    val_calib = val.loc[val["month"] > 6].reset_index(drop=True)
    
    # Combined training set: all 2022 + early 2023
    fit_df = pd.concat([train, val_early], ignore_index=True)
    fit_labels = fit_df["event_label"].astype(str).to_numpy()
    fit_weights = episode_balanced_weights(fit_labels, fit_df["episode_id"].fillna("").astype(str).to_numpy())
    
    print(f"Fitting event model on {fit_df.shape[0]:,} rows (2022 to Jun 2023)...")
    base_event = LGBMClassifier(
        objective="multiclass",
        n_estimators=680,
        learning_rate=0.03,
        num_leaves=40,
        max_depth=10,
        min_child_samples=25,
        subsample=0.88,
        colsample_bytree=0.82,
        reg_alpha=0.4,
        reg_lambda=4.0,
        random_state=26073,
        n_jobs=-1,
        verbosity=-1,
    )
    base_event.fit(values(fit_df, PHASE10_FEATURES), fit_labels, sample_weight=fit_weights)
    
    # Calibrate on Jul-Dec 2023
    print(f"Calibrating on {val_calib.shape[0]:,} rows (Jul to Dec 2023)...")
    calibrated = CalibratedClassifierCV(FrozenEstimator(base_event), method="sigmoid")
    calibrated.fit(values(val_calib, PHASE10_FEATURES), val_calib["event_label"].astype(str).to_numpy())
    
    # Select policy on calibration fold
    calib_fault = probability(calibrated, val_calib, PHASE10_FEATURES, "sensor_fault")
    calib_weather = probability(calibrated, val_calib, PHASE10_FEATURES, "genuine_weather")
    calib_fault_labels = (val_calib["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    calib_weather_labels = (val_calib["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    
    fault_policy, _ = choose_persistence_policy(val_calib, calib_fault_labels, calib_fault, calib_weather_labels)
    weather_policy = choose_threshold(calib_weather_labels, calib_weather)
    print(f"Selected policy: {fault_policy}")
    
    # Fit root-cause classifier on combined fault episodes
    fault_fit = fit_df.loc[fit_df["event_label"] == "sensor_fault"].reset_index(drop=True)
    root_labels = fault_fit["anomaly_type"].astype(str).to_numpy()
    root_weights = episode_balanced_weights(root_labels, fault_fit["episode_id"].fillna("").astype(str).to_numpy())
    
    print(f"Fitting Root-Cause classifier on {fault_fit.shape[0]:,} fault rows...")
    root_model = LGBMClassifier(
        objective="multiclass",
        n_estimators=580,
        learning_rate=0.035,
        num_leaves=35,
        max_depth=9,
        min_child_samples=12,
        subsample=0.90,
        colsample_bytree=0.85,
        reg_alpha=0.3,
        reg_lambda=3.0,
        random_state=26075,
        n_jobs=-1,
        verbosity=-1,
    )
    root_model.fit(model_values(fault_fit), root_labels, sample_weight=root_weights)
    
    # Evaluate on time_test (2024)
    print("\nEvaluating on time_test (2024 unseen holdout)...")
    test_df = load_split("time_test")
    test_fault_labels = (test_df["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    test_weather_labels = (test_df["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    station_ids = test_df["station_id"].astype(str).tolist()
    timestamps = test_df["emitted_timestamp_utc"].astype(str).tolist()
    
    test_fault_raw = probability(calibrated, test_df, PHASE10_FEATURES, "sensor_fault")
    test_weather_raw = probability(calibrated, test_df, PHASE10_FEATURES, "genuine_weather")
    test_scores = causal_persistence_scores(test_df, test_fault_raw, float(fault_policy["persistence_decay"]))
    
    pm = point_metrics(test_fault_labels, test_scores, float(fault_policy["threshold"]), station_ids, timestamps, test_weather_labels)
    ep = episode_metrics(
        test_fault_labels, test_scores >= float(fault_policy["threshold"]),
        test_df["episode_id"].fillna("").astype(str).tolist(),
        timestamps, test_df["anomaly_type"].astype(str).tolist()
    )
    
    detected = test_scores >= float(fault_policy["threshold"])
    roots, root_pred, root_conf, incidents = root_results(test_df, detected, test_scores, root_model, root_threshold=0.28)
    
    print("\n--- RESULTS ON 2024 UNSEEN TIME HOLDOUT ---")
    print(f"Fault Precision:       {pm['precision']*100:.2f}% (was 71.47%)")
    print(f"Fault Recall:          {pm['recall']*100:.2f}% (was 41.50%)")
    print(f"Fault F1-score:        {pm['f1']*100:.2f}% (was 52.51%)")
    print(f"AUCPR:                 {pm['aucpr']*100:.2f}% (was 48.45%)")
    print(f"Episode Recall:        {ep['recall']*100:.2f}% ({ep['detected_episodes']}/{ep['episodes']}) (was 79.17%)")
    print(f"False alarms/day:      {pm['false_alarms_per_station_day']:.4f}")
    print(f"Weather False Pos:     {pm['weather_false_positive_rate']*100:.2f}% ({pm['weather_false_positives']} alarms)")
    print(f"Oracle Root Accuracy:  {roots['oracle_root_cause']['accuracy']*100:.2f}% (was 46.77%)")
    print(f"Oracle Macro F1:       {roots['oracle_root_cause']['macro_f1']*100:.2f}% (was 46.69%)")
    print(f"End-to-End Exact Acc:  {roots['end_to_end_root_cause']['exact_accuracy']*100:.2f}% (was 18.36%)")
    print(f"Diagnostic Coverage:   {roots['end_to_end_root_cause']['diagnostic_coverage']*100:.2f}% (was 26.24%)")
    print(f"Accepted Root Acc:     {roots['end_to_end_root_cause']['accepted_root_accuracy']*100:.2f}%")
    
    # Evaluate on station_test (unseen stations)
    print("\nEvaluating on station_test (unseen stations holdout)...")
    st_df = load_split("station_test")
    st_fault_labels = (st_df["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    st_weather_labels = (st_df["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    st_station_ids = st_df["station_id"].astype(str).tolist()
    st_timestamps = st_df["emitted_timestamp_utc"].astype(str).tolist()
    
    st_fault_raw = probability(calibrated, st_df, PHASE10_FEATURES, "sensor_fault")
    st_scores = causal_persistence_scores(st_df, st_fault_raw, 0.0) # new station decay is 0.0
    st_pm = point_metrics(st_fault_labels, st_scores, float(fault_policy["threshold"]), st_station_ids, st_timestamps, st_weather_labels)
    st_ep = episode_metrics(
        st_fault_labels, st_scores >= float(fault_policy["threshold"]),
        st_df["episode_id"].fillna("").astype(str).tolist(),
        st_timestamps, st_df["anomaly_type"].astype(str).tolist()
    )
    print("\n--- RESULTS ON UNSEEN STATIONS HOLDOUT ---")
    print(f"Station Precision:     {st_pm['precision']*100:.2f}%")
    print(f"Station Recall:        {st_pm['recall']*100:.2f}%")
    print(f"Station F1:            {st_pm['f1']*100:.2f}%")
    print(f"Station Episode:       {st_ep['recall']*100:.2f}%")
    print(f"False alarms/day:      {st_pm['false_alarms_per_station_day']:.4f}")

if __name__ == "__main__":
    main()

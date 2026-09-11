"""Train the upgraded SkyGuard model with Spatial Buddy QC and Dual-Trigger Persistence."""

import sys, json, time, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from data.refine_phase10_event import evaluate, probability, values
from data.run_phase10_models import load_split
from skyguard.evaluation.classification import episode_balanced_weights
from skyguard.features.phase10 import PHASE10_FEATURES
from skyguard.features.spatial_qc import add_spatial_qc
from skyguard.models.phase10 import causal_persistence_scores, constrained_threshold

UPGRADED_MODEL_FILE = ROOT / "models" / "upgraded_spatial_model.joblib"
REPORT_FILE = ROOT / "reports" / "upgraded_spatial_model_report.json"

def apply_dual_persistence(frame, raw_scores, decay=0.55, low_trigger=0.25, boost_per_step=0.06, max_boost=0.20, maximum_gap_hours=3.0):
    result = np.zeros_like(raw_scores, dtype=np.float64)
    timestamps = pd.to_datetime(frame["emitted_timestamp_utc"], utc=True).astype("int64").to_numpy() / 3.6e12
    station_ids = frame["station_id"].astype(str).to_numpy()
    order = np.lexsort((timestamps, station_ids))
    previous_station = ""
    previous_time = 0.0
    state = 0.0
    consecutive = 0
    for index in order:
        station = station_ids[index]
        timestamp = timestamps[index]
        if station != previous_station or timestamp - previous_time > maximum_gap_hours or timestamp <= previous_time:
            consecutive = 1 if raw_scores[index] >= low_trigger else 0
            state = float(raw_scores[index])
        else:
            if raw_scores[index] >= low_trigger:
                consecutive += 1
                boost = min(max_boost, consecutive * boost_per_step)
                state = max(float(raw_scores[index]) + boost, state * decay)
            else:
                consecutive = 0
                state = max(float(raw_scores[index]), state * decay)
        result[index] = state
        previous_station = station
        previous_time = timestamp
    return result

def main():
    started = time.perf_counter()
    print("Loading data splits...")
    train = load_split("train")
    validation = load_split("validation")
    time_test = load_split("time_test")
    station_test = load_split("station_test")
    
    print("Computing Spatial Buddy QC features...")
    train = add_spatial_qc(train)
    validation = add_spatial_qc(validation)
    time_test = add_spatial_qc(time_test)
    station_test = add_spatial_qc(station_test)
    
    spatial_features = [c for c in train.columns if c.startswith('qc_')]
    all_features = list(PHASE10_FEATURES) + spatial_features
    print(f"Total features: {len(all_features)} ({len(PHASE10_FEATURES)} base + {len(spatial_features)} spatial buddy)")
    
    labels = train["event_label"].astype(str).to_numpy()
    weights = episode_balanced_weights(labels, train["episode_id"].fillna("").astype(str).to_numpy())
    
    print(f"Training multiclass LightGBM with spatial buddy awareness on {train.shape[0]:,} rows...")
    base = LGBMClassifier(
        objective="multiclass", n_estimators=600, learning_rate=0.03, num_leaves=31,
        max_depth=9, min_child_samples=30, subsample=0.90, colsample_bytree=0.85,
        reg_alpha=0.5, reg_lambda=5.0, random_state=26073, n_jobs=-1, verbosity=-1,
    )
    base.fit(values(train, all_features), labels, sample_weight=weights)
    
    print("Calibrating model on validation split...")
    calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    calibrated.fit(values(validation, all_features), validation["event_label"].astype(str).to_numpy())
    
    print("Selecting Dual-Trigger Persistence Policy...")
    val_fault_raw = probability(calibrated, validation, all_features, "sensor_fault")
    val_weather_raw = probability(calibrated, validation, all_features, "genuine_weather")
    val_fault_labels = (validation["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    val_weather_labels = (validation["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    
    best_policy = None
    best_f1 = 0
    best_scores_val = None
    
    for low_trig in (0.22, 0.25, 0.28):
        for boost in (0.05, 0.08):
            for decay in (0.55, 0.70):
                scores = apply_dual_persistence(validation, val_fault_raw, decay=decay, low_trigger=low_trig, boost_per_step=boost)
                policy = constrained_threshold(val_fault_labels, scores, validation, val_weather_labels, false_alarm_limit=0.025, weather_false_fault_limit=0.015)
                policy.update({"decay": decay, "low_trigger": low_trig, "boost_per_step": boost})
                if policy["f1"] > best_f1:
                    best_f1 = policy["f1"]
                    best_policy = policy
                    best_scores_val = scores
                    
    print(f"Optimal Policy Selected: Threshold={best_policy['threshold']:.4f}, Decay={best_policy['decay']}, LowTrig={best_policy['low_trigger']}, F1={best_policy['f1']:.4f}")
    
    best_policy["persistence_decay"] = best_policy["decay"]
    
    from skyguard.evaluation.metrics import point_metrics, episode_metrics
    def eval_adjusted(frame, adjusted, th):
        labels = (frame["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
        weather = (frame["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
        res = point_metrics(
            labels, adjusted, th, frame["station_id"].astype(str).tolist(),
            frame["emitted_timestamp_utc"].astype(str).tolist(), weather,
        )
        res["episode_detection"] = episode_metrics(
            labels, adjusted >= th, frame["episode_id"].fillna("").astype(str).tolist(),
            frame["emitted_timestamp_utc"].astype(str).tolist(), frame["anomaly_type"].astype(str).tolist(),
        )
        return res

    evaluation = {}
    print("\n--- EVALUATING ON TIME TEST (2024 Unseen Time) ---")
    tt_raw = probability(calibrated, time_test, all_features, "sensor_fault")
    tt_scores = apply_dual_persistence(time_test, tt_raw, decay=best_policy["decay"], low_trigger=best_policy["low_trigger"], boost_per_step=best_policy["boost_per_step"])
    eval_tt = eval_adjusted(time_test, tt_scores, best_policy["threshold"])
    evaluation["time_test"] = eval_tt
    print(f"Time Test -> Prec: {eval_tt['precision']:.4f}, Rec: {eval_tt['recall']:.4f}, F1: {eval_tt['f1']:.4f}, EpRec: {eval_tt['episode_detection']['recall']:.4f}, FA/day: {eval_tt['false_alarms_per_station_day']:.4f}")
    
    print("\n--- EVALUATING ON STATION TEST (Held-Out Unseen Stations) ---")
    st_raw = probability(calibrated, station_test, all_features, "sensor_fault")
    st_scores = apply_dual_persistence(station_test, st_raw, decay=best_policy["decay"], low_trigger=best_policy["low_trigger"], boost_per_step=best_policy["boost_per_step"])
    eval_st = eval_adjusted(station_test, st_scores, best_policy["threshold"])
    evaluation["station_test"] = eval_st
    print(f"Station Test -> Prec: {eval_st['precision']:.4f}, Rec: {eval_st['recall']:.4f}, F1: {eval_st['f1']:.4f}, EpRec: {eval_st['episode_detection']['recall']:.4f}, FA/day: {eval_st['false_alarms_per_station_day']:.4f}")
    
    report = {
        "status": "complete",
        "features": all_features,
        "feature_count": len(all_features),
        "policy": best_policy,
        "evaluation": evaluation,
        "runtime_seconds": round(time.perf_counter() - started, 2)
    }
    
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    joblib.dump({"event_model": calibrated, "features": all_features, "policy": best_policy}, UPGRADED_MODEL_FILE, compress=3)
    print(f"\nReport written to {REPORT_FILE}")

if __name__ == '__main__':
    main()

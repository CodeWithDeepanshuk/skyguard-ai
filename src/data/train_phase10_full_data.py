"""Train the compliant multiclass event detector on every 2022 row."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.refine_phase10_event import evaluate, probability, values  # noqa: E402
from data.run_phase10_models import load_split  # noqa: E402
from skyguard.evaluation.classification import episode_balanced_weights  # noqa: E402
from skyguard.evaluation.metrics import choose_threshold  # noqa: E402
from skyguard.features.phase10 import PHASE10_FEATURES  # noqa: E402
from skyguard.models.phase10 import choose_persistence_policy  # noqa: E402


MODEL_FILE = ROOT / "models" / "phase10_full_data_event.joblib"
REPORT_FILE = ROOT / "reports" / "phase10_full_data_event.json"


def main() -> None:
    started = time.perf_counter()
    train = load_split("train")
    validation = load_split("validation")
    
    # Chronological partition of 2023 validation: Jan-Jun into fit, Jul-Dec into calibration
    val_month = pd.to_datetime(validation["emitted_timestamp_utc"], utc=True).dt.month
    val_train = validation.loc[val_month <= 6].reset_index(drop=True)
    val_calib = validation.loc[val_month > 6].reset_index(drop=True)
    
    fit_df = pd.concat([train, val_train], ignore_index=True)
    labels = fit_df["event_label"].astype(str).to_numpy()
    weights = episode_balanced_weights(labels, fit_df["episode_id"].fillna("").astype(str).to_numpy())
    
    print(f"Training on all {fit_df.shape[0]:,} visible 2022 to Jun-2023 rows...")
    base = LGBMClassifier(
        objective="multiclass", n_estimators=680, learning_rate=0.03, num_leaves=40,
        max_depth=10, min_child_samples=25, subsample=0.88, colsample_bytree=0.82,
        reg_alpha=0.4, reg_lambda=4.0, random_state=26073, n_jobs=-1, verbosity=-1,
    )
    base.fit(values(fit_df, PHASE10_FEATURES), labels, sample_weight=weights)
    
    print(f"Calibrating on {val_calib.shape[0]:,} out-of-sample Jul-Dec 2023 rows...")
    calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    calibrated.fit(values(val_calib, PHASE10_FEATURES), val_calib["event_label"].astype(str).to_numpy())
    
    validation_fault = probability(calibrated, val_calib, PHASE10_FEATURES, "sensor_fault")
    validation_weather = probability(calibrated, val_calib, PHASE10_FEATURES, "genuine_weather")
    fault_labels = (val_calib["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather_labels = (val_calib["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    fault_policy, _ = choose_persistence_policy(val_calib, fault_labels, validation_fault, weather_labels)
    weather_policy = choose_threshold(weather_labels, validation_weather)
    policy = {"fault": fault_policy, "weather": weather_policy, "dew_point_used": False, "selection": "chronological 2023 H2 calibration"}
    evaluation = {"validation": evaluate(val_calib, validation_fault, fault_policy)}
    for split in ("time_test", "station_test"):
        frame = load_split(split)
        scores = probability(calibrated, frame, PHASE10_FEATURES, "sensor_fault")
        evaluation[split] = evaluate(frame, scores, fault_policy)
    joblib.dump({"event_model": calibrated, "features": list(PHASE10_FEATURES), "policy": policy}, MODEL_FILE, compress=3)
    report = {"phase": "10-full-data", "status": "complete", "training_rows": int(train.shape[0]), "policy": policy, "evaluation": evaluation, "runtime_seconds": round(time.perf_counter() - started, 3)}
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

"""Select a validation-only threshold robust across individual stations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.refine_phase10_event import probability  # noqa: E402
from data.run_phase10_models import load_split  # noqa: E402
from skyguard.evaluation.metrics import episode_metrics, point_metrics  # noqa: E402
from skyguard.models.phase10 import causal_persistence_scores, station_days  # noqa: E402


REPORT = ROOT / "reports" / "phase10_new_station_policy.json"


def select(frame: pd.DataFrame, raw: np.ndarray) -> dict[str, float]:
    labels = (frame["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (frame["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    stations = frame["station_id"].astype(str).to_numpy()
    best = None
    days = station_days(frame)
    for decay in (0.0, 0.55, 0.70, 0.82):
        scores = causal_persistence_scores(frame, raw, decay)
        thresholds = np.unique(np.quantile(scores, np.linspace(0.90, 0.9999, 500)))
        for threshold in thresholds:
            predicted = scores >= threshold
            fp = int(np.sum(predicted & (labels == 0)))
            weather_rate = float(np.mean(predicted[weather == 1])) if np.any(weather == 1) else 0.0
            if fp / max(days, 1) > 0.05 or weather_rate > 0.02:
                continue
            station_f1 = []
            for station in np.unique(stations):
                mask = stations == station
                tp = int(np.sum(predicted[mask] & (labels[mask] == 1)))
                local_fp = int(np.sum(predicted[mask] & (labels[mask] == 0)))
                fn = int(np.sum(~predicted[mask] & (labels[mask] == 1)))
                precision = tp / max(tp + local_fp, 1)
                recall = tp / max(tp + fn, 1)
                station_f1.append(2 * precision * recall / max(precision + recall, 1e-12))
            macro_f1 = float(np.mean(station_f1))
            recall = float(np.sum(predicted & (labels == 1)) / max(np.sum(labels), 1))
            item = {"threshold": float(threshold), "persistence_decay": decay, "station_macro_f1": macro_f1, "recall": recall, "false_alarms_per_station_day": fp / max(days, 1), "weather_false_fault_rate": weather_rate}
            if best is None or (macro_f1, recall) > (best["station_macro_f1"], best["recall"]):
                best = item
    if best is None:
        raise RuntimeError("No feasible new-station policy")
    return best


def metrics(frame: pd.DataFrame, raw: np.ndarray, policy: dict[str, float]) -> dict[str, object]:
    labels = (frame["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (frame["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    scores = causal_persistence_scores(frame, raw, policy["persistence_decay"])
    result = point_metrics(labels, scores, policy["threshold"], frame["station_id"].astype(str).tolist(), frame["emitted_timestamp_utc"].astype(str).tolist(), weather)
    result["episode_detection"] = episode_metrics(labels, scores >= policy["threshold"], frame["episode_id"].fillna("").astype(str).tolist(), frame["emitted_timestamp_utc"].astype(str).tolist(), frame["anomaly_type"].astype(str).tolist())
    return result


def main() -> None:
    artifact = joblib.load(ROOT / "models" / "phase10_full_data_event.joblib")
    features = tuple(artifact["features"])
    validation = load_split("validation")
    raw = probability(artifact["event_model"], validation, features, "sensor_fault")
    policy = select(validation, raw)
    evaluation = {"validation": metrics(validation, raw, policy)}
    for split in ("time_test", "station_test"):
        frame = load_split(split)
        scores = probability(artifact["event_model"], frame, features, "sensor_fault")
        evaluation[split] = metrics(frame, scores, policy)
    report = {"status": "complete", "selection": "2023 station-macro F1 under operational constraints", "policy": policy, "evaluation": evaluation}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

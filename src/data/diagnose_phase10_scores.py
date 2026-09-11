"""Compare frozen Phase 10 score combinations without retraining or test tuning."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.run_phase10_models import (  # noqa: E402
    TCN_FEATURES, CausalTCN, fusion_values, histories, load_split, model_values, predict_tcn, tcn_matrix,
)
from skyguard.evaluation.metrics import point_metrics  # noqa: E402
from skyguard.models.phase10 import causal_persistence_scores, choose_persistence_policy  # noqa: E402


REPORT = ROOT / "reports" / "phase10_score_diagnostics.json"


def candidates(lightgbm: np.ndarray, tcn: np.ndarray, fusion: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "lightgbm": lightgbm,
        "tcn": tcn,
        "mean": 0.5 * lightgbm + 0.5 * tcn,
        "tcn_70": 0.3 * lightgbm + 0.7 * tcn,
        "lightgbm_70": 0.7 * lightgbm + 0.3 * tcn,
        "maximum": np.maximum(lightgbm, tcn),
        "logistic_fusion": fusion,
    }


def score(frame: pd.DataFrame, values: np.ndarray, threshold: float) -> dict[str, float]:
    labels = (frame["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (frame["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    return point_metrics(
        labels, values, threshold, frame["station_id"].astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), weather,
    )


def main() -> None:
    bundle = joblib.load(ROOT / "models" / "phase10_ensemble.joblib")
    checkpoint = torch.load(ROOT / "models" / "phase10_tcn.pt", map_location="cpu", weights_only=False)
    tcn = CausalTCN(checkpoint["input_channels"], checkpoint["hidden_channels"])
    tcn.load_state_dict(checkpoint["state_dict"])
    validation = load_split("validation")
    matrix = tcn_matrix(validation, bundle["tcn_center"], bundle["tcn_scale"])
    history = histories(validation)
    tcn_scores = predict_tcn(tcn, matrix, history, np.arange(validation.shape[0]))
    values = model_values(validation)
    lightgbm = bundle["fault_model"].predict_proba(values)[:, 1]
    weather_scores = bundle["weather_model"].predict_proba(values)[:, 1]
    fusion = bundle["fusion_model"].predict_proba(fusion_values(validation, lightgbm, tcn_scores, weather_scores))[:, 1]
    validation_candidates = candidates(lightgbm, tcn_scores, fusion)
    labels = (validation["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (validation["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    policies: dict[str, object] = {}
    for name, raw in validation_candidates.items():
        policy, _ = choose_persistence_policy(validation, labels, raw, weather)
        policies[name] = policy

    evaluations: dict[str, object] = {"validation": {}}
    for name, raw in validation_candidates.items():
        policy = policies[name]
        adjusted = causal_persistence_scores(validation, raw, float(policy["persistence_decay"]))
        evaluations["validation"][name] = score(validation, adjusted, float(policy["threshold"]))

    for split in ("time_test", "station_test"):
        frame = load_split(split)
        predictions = pd.read_csv(ROOT / "data" / "predictions_phase10" / f"{split}_phase10_predictions.csv.gz")
        split_candidates = candidates(
            predictions["lightgbm_fault_probability"].to_numpy(),
            predictions["tcn_fault_probability"].to_numpy(),
            predictions["fault_probability"].to_numpy(),
        )
        evaluations[split] = {}
        for name, raw in split_candidates.items():
            policy = policies[name]
            adjusted = causal_persistence_scores(frame, raw, float(policy["persistence_decay"]))
            evaluations[split][name] = score(frame, adjusted, float(policy["threshold"]))

    selected = max(policies, key=lambda name: (evaluations["validation"][name]["f1"], evaluations["validation"][name]["recall"]))
    report = {"selection_rule": "maximum full-2023 F1 under false-alarm/weather constraints", "selected": selected, "policies": policies, "evaluation": evaluations}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "selected": selected,
        "validation": evaluations["validation"][selected],
        "time_test": evaluations["time_test"][selected],
        "station_test": evaluations["station_test"][selected],
    }, indent=2))


if __name__ == "__main__":
    main()

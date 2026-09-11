"""Select a safe TCN contribution against the strongest compliant LightGBM."""

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

from data.refine_phase10_event import probability  # noqa: E402
from data.run_phase10_models import CausalTCN, histories, load_split, predict_tcn, tcn_matrix  # noqa: E402
from skyguard.evaluation.metrics import episode_metrics, point_metrics  # noqa: E402
from skyguard.models.phase10 import causal_persistence_scores, choose_persistence_policy  # noqa: E402


REPORT = ROOT / "reports" / "phase10_final_fusion.json"


def combinations(lightgbm: np.ndarray, tcn: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "lightgbm_only": lightgbm,
        "mean_tcn20": 0.80 * lightgbm + 0.20 * tcn,
        "mean_tcn30": 0.70 * lightgbm + 0.30 * tcn,
        "max_tcn30": np.maximum(lightgbm, 0.30 * tcn),
        "max_tcn40": np.maximum(lightgbm, 0.40 * tcn),
        "max_tcn50": np.maximum(lightgbm, 0.50 * tcn),
        "agreement_product": np.sqrt(np.maximum(lightgbm * tcn, 0.0)),
    }


def metrics(frame: pd.DataFrame, raw: np.ndarray, policy: dict[str, float]) -> dict[str, object]:
    labels = (frame["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (frame["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    scores = causal_persistence_scores(frame, raw, policy["persistence_decay"])
    result = point_metrics(
        labels, scores, policy["threshold"], frame["station_id"].astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), weather,
    )
    result["episode_detection"] = episode_metrics(
        labels, scores >= policy["threshold"], frame["episode_id"].fillna("").astype(str).tolist(),
        frame["emitted_timestamp_utc"].astype(str).tolist(), frame["anomaly_type"].astype(str).tolist(),
    )
    return result


def main() -> None:
    primary = joblib.load(ROOT / "models" / "phase10_full_data_event.joblib")
    phase10 = joblib.load(ROOT / "models" / "phase10_ensemble.joblib")
    checkpoint = torch.load(ROOT / "models" / "phase10_tcn.pt", map_location="cpu", weights_only=False)
    tcn = CausalTCN(checkpoint["input_channels"], checkpoint["hidden_channels"])
    tcn.load_state_dict(checkpoint["state_dict"])
    validation = load_split("validation")
    lgbm = probability(primary["event_model"], validation, tuple(primary["features"]), "sensor_fault")
    tcn_scores = predict_tcn(
        tcn, tcn_matrix(validation, phase10["tcn_center"], phase10["tcn_scale"]),
        histories(validation), np.arange(validation.shape[0]),
    )
    validation_candidates = combinations(lgbm, tcn_scores)
    labels = (validation["event_label"].to_numpy() == "sensor_fault").astype(np.int8)
    weather = (validation["event_label"].to_numpy() == "genuine_weather").astype(np.int8)
    policies = {}
    evaluation = {"validation": {}}
    for name, scores in validation_candidates.items():
        policy, _ = choose_persistence_policy(validation, labels, scores, weather)
        policies[name] = policy
        evaluation["validation"][name] = metrics(validation, scores, policy)
    selected = max(policies, key=lambda name: (evaluation["validation"][name]["f1"], evaluation["validation"][name]["recall"]))
    for split in ("time_test", "station_test"):
        frame = load_split(split)
        lgbm = probability(primary["event_model"], frame, tuple(primary["features"]), "sensor_fault")
        stored = pd.read_csv(ROOT / "data" / "predictions_phase10" / f"{split}_phase10_predictions.csv.gz", usecols=["tcn_fault_probability"])
        split_candidates = combinations(lgbm, stored["tcn_fault_probability"].to_numpy())
        evaluation[split] = {name: metrics(frame, scores, policies[name]) for name, scores in split_candidates.items()}
    report = {"phase": "10-final-fusion", "status": "complete", "selected": selected, "policies": policies, "evaluation": evaluation}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "selected": selected,
        "validation": evaluation["validation"][selected],
        "time_test": evaluation["time_test"][selected],
        "station_test": evaluation["station_test"][selected],
    }, indent=2))


if __name__ == "__main__":
    main()

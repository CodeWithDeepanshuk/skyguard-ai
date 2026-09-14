"""Run an evidence-backed neural benchmark for SkyGuard AI.

This experiment is intentionally isolated from every previously published result.
It never overwrites Iteration 10/11 evidence or the active production model.

Protocol
--------
* 2022, 20 stations: neural-network fitting.
* Jan-Feb 2023: epoch selection only.
* Mar-Apr 2023: probability calibration.
* May-Aug 2023: model/blend and incident-policy selection.
* Sep-Dec 2023: development confirmation (not used for selection).
* 2024, same 20 stations: sealed time holdout.
* 2024, four different stations: sealed geographic holdout.

The source observations are real NOAA/NCEI ISD observations from India. Fault and
weather-event labels are injected/simulated labels supplied by the Phase 10 data
contract; therefore the resulting metrics are reproducible research metrics, not
field-verified IMD maintenance accuracy.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from torch import nn
from torch.utils.data import DataLoader


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.skyguard.models.tcn import (  # noqa: E402
    CausalTCN,
    SequenceDataset,
    TCN_FEATURES,
    WeightedFocalLoss,
    sequence_index,
)


SEED = 26073
SEQ_LEN = 24
TRAIN_NORMAL_ENDPOINTS = 30_000
MONITOR_NORMAL_ENDPOINTS = 12_000
MAX_EPOCHS = 8
PATIENCE = 3
BATCH_SIZE = 256
INFERENCE_BATCH_SIZE = 1024
MAX_GAP_MINUTES = 180.0

FEATURE_DIR = ROOT / "data" / "features_phase10"
RAW_DATA = ROOT / "data" / "processed" / "aws_observations_2022_2024.csv"
OUTPUT_DIR = ROOT / "reports" / "iteration12_neural_honest"
MODEL_DIR = OUTPUT_DIR / "models"

META_COLUMNS = (
    "row_id",
    "station_id",
    "timestamp_utc",
    "emitted_timestamp_utc",
    "available_to_detector",
    "is_anomaly",
    "is_weather_event",
    "episode_id",
    "anomaly_type",
    "anomaly_sensor",
    "anomaly_severity",
)


def set_deterministic(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.set_num_threads(max(1, min(10, os.cpu_count() or 1)))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_split(name: str, feature_names: tuple[str, ...]) -> pd.DataFrame:
    path = FEATURE_DIR / f"{name}_features.csv.gz"
    header = pd.read_csv(path, nrows=0).columns
    missing = sorted(set(feature_names) - set(header))
    if missing:
        raise ValueError(f"{name} is missing required causal features: {missing}")
    available_meta = [column for column in META_COLUMNS if column in header]
    frame = pd.read_csv(
        path,
        usecols=list(feature_names) + available_meta,
        low_memory=False,
    )
    frame = frame.loc[frame["available_to_detector"].eq(1)].reset_index(drop=True)
    frame["station_id"] = frame["station_id"].astype(str)
    frame["emitted_timestamp_utc"] = pd.to_datetime(
        frame["emitted_timestamp_utc"], utc=True, errors="raise"
    )
    frame["is_fault"] = frame["is_anomaly"].fillna(0).astype(int).eq(1)
    frame["is_weather"] = frame["is_weather_event"].fillna(0).astype(int).eq(1)
    frame["episode_id"] = frame.get("episode_id", "").fillna("").astype(str)
    return frame


def fit_normalizer(frame: pd.DataFrame, feature_names: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
    raw = frame.loc[:, feature_names].apply(pd.to_numeric, errors="coerce").to_numpy(np.float32)
    center = np.nanmedian(raw, axis=0).astype(np.float32)
    q25 = np.nanpercentile(raw, 25, axis=0).astype(np.float32)
    q75 = np.nanpercentile(raw, 75, axis=0).astype(np.float32)
    scale = (q75 - q25).astype(np.float32)
    center[~np.isfinite(center)] = 0.0
    scale[~np.isfinite(scale) | (scale < 1e-4)] = 1.0
    return center, scale


def transform_matrix(
    frame: pd.DataFrame,
    feature_names: tuple[str, ...],
    center: np.ndarray,
    scale: np.ndarray,
) -> np.ndarray:
    raw = frame.loc[:, feature_names].apply(pd.to_numeric, errors="coerce").to_numpy(np.float32)
    normalized = (raw - center) / scale
    return np.nan_to_num(normalized, nan=0.0, posinf=10.0, neginf=-10.0).clip(-10.0, 10.0)


def build_history(frame: pd.DataFrame) -> np.ndarray:
    stations = frame["station_id"].to_numpy(str)
    timestamps = frame["emitted_timestamp_utc"].astype("int64").to_numpy()
    return sequence_index(stations, timestamps, SEQ_LEN)


def sampled_endpoints(
    frame: pd.DataFrame,
    mask: np.ndarray,
    normal_limit: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    candidates = np.flatnonzero(mask)
    positive = candidates[frame.loc[candidates, "is_fault"].to_numpy(bool)]
    weather = candidates[frame.loc[candidates, "is_weather"].to_numpy(bool)]
    ordinary = candidates[
        ~(frame.loc[candidates, "is_fault"].to_numpy(bool) |
          frame.loc[candidates, "is_weather"].to_numpy(bool))
    ]
    selected_normal = rng.choice(ordinary, size=min(normal_limit, ordinary.size), replace=False)
    return np.unique(np.concatenate([positive, weather, selected_normal])).astype(np.int64)


class CausalGRU(nn.Module):
    def __init__(self, input_channels: int, hidden_size: int = 40) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_channels,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
            bidirectional=False,
        )
        self.output = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Linear(hidden_size, 24),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(24, 1),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        sequence = values.transpose(1, 2)
        hidden, _ = self.gru(sequence)
        return self.output(hidden[:, -1, :]).squeeze(1)


def predict_raw(
    model: nn.Module,
    matrix: np.ndarray,
    history: np.ndarray,
    targets: np.ndarray,
    device: torch.device,
) -> np.ndarray:
    dataset = SequenceDataset(matrix, history, targets)
    loader = DataLoader(dataset, batch_size=INFERENCE_BATCH_SIZE, shuffle=False, num_workers=0)
    chunks: list[np.ndarray] = []
    model.eval()
    with torch.inference_mode():
        for (values,) in loader:
            logits = model(values.to(device))
            chunks.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(chunks).astype(np.float64)


def train_model(
    name: str,
    model: nn.Module,
    train_matrix: np.ndarray,
    train_history: np.ndarray,
    train_frame: pd.DataFrame,
    train_targets: np.ndarray,
    validation_matrix: np.ndarray,
    validation_history: np.ndarray,
    validation_frame: pd.DataFrame,
    monitor_targets: np.ndarray,
    device: torch.device,
) -> tuple[nn.Module, list[dict[str, object]], int, float]:
    labels = train_frame["is_fault"].to_numpy(np.float32)
    sample_labels = labels[train_targets]
    negatives = int((sample_labels == 0).sum())
    positives = int((sample_labels == 1).sum())
    positive_weight = float(min(15.0, negatives / max(positives, 1)))
    weights = np.ones(len(train_frame), dtype=np.float32)
    weights[labels == 1] = positive_weight
    weights[train_frame["is_weather"].to_numpy(bool)] = 1.5

    dataset = SequenceDataset(train_matrix, train_history, train_targets, labels, weights)
    generator = torch.Generator().manual_seed(SEED)
    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=generator,
        num_workers=0,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=1.2e-3, weight_decay=2e-4)
    loss_function = WeightedFocalLoss(gamma=2.0)
    model.to(device)

    history_rows: list[dict[str, object]] = []
    best_ap = -math.inf
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    monitor_labels = validation_frame.loc[monitor_targets, "is_fault"].to_numpy(bool)

    for epoch in range(1, MAX_EPOCHS + 1):
        started = time.perf_counter()
        model.train()
        total_loss = 0.0
        batches = 0
        for values, targets, sample_weights in loader:
            values = values.to(device)
            targets = targets.to(device)
            sample_weights = sample_weights.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(values)
            loss = loss_function(logits, targets, sample_weights)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            total_loss += float(loss.detach().cpu())
            batches += 1

        monitor_scores = predict_raw(
            model,
            validation_matrix,
            validation_history,
            monitor_targets,
            device,
        )
        monitor_ap = float(average_precision_score(monitor_labels, monitor_scores))
        row = {
            "model": name,
            "epoch": epoch,
            "train_loss": total_loss / max(batches, 1),
            "monitor_auprc": monitor_ap,
            "elapsed_seconds": time.perf_counter() - started,
            "positive_sample_weight": positive_weight,
            "training_endpoints": int(train_targets.size),
            "monitor_endpoints": int(monitor_targets.size),
        }
        history_rows.append(row)
        print(
            f"{name:>4} epoch {epoch}/{MAX_EPOCHS} | "
            f"loss={row['train_loss']:.5f} | Jan-Feb-2023 AUPRC={monitor_ap:.5f} | "
            f"{row['elapsed_seconds']:.1f}s",
            flush=True,
        )
        if monitor_ap > best_ap + 1e-5:
            best_ap = monitor_ap
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= PATIENCE:
                print(f"{name}: early stop; restoring epoch {best_epoch}", flush=True)
                break

    if best_state is None:
        raise RuntimeError(f"{name} did not produce a valid checkpoint")
    model.load_state_dict(best_state)
    return model, history_rows, best_epoch, float(best_ap)


def logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values.astype(np.float64), 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped))


def fit_calibrator(raw_scores: np.ndarray, labels: np.ndarray) -> LogisticRegression:
    calibrator = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=SEED)
    calibrator.fit(logit(raw_scores).reshape(-1, 1), labels.astype(int))
    return calibrator


def calibrate(calibrator: LogisticRegression, raw_scores: np.ndarray) -> np.ndarray:
    return calibrator.predict_proba(logit(raw_scores).reshape(-1, 1))[:, 1]


def station_sessions(frame: pd.DataFrame) -> list[np.ndarray]:
    sessions: list[np.ndarray] = []
    for _, group in frame.groupby("station_id", sort=False):
        ordered = group.sort_values("emitted_timestamp_utc", kind="stable").index.to_numpy(np.int64)
        stamps = frame.loc[ordered, "emitted_timestamp_utc"].astype("int64").to_numpy()
        gaps = np.diff(stamps) / 60_000_000_000.0
        boundaries = np.flatnonzero(np.r_[True, gaps > MAX_GAP_MINUTES, True])
        for left, right in zip(boundaries[:-1], boundaries[1:]):
            sessions.append(ordered[left:right])
    return sessions


def apply_persistence(
    frame: pd.DataFrame,
    scores: np.ndarray,
    threshold: float,
    k: int,
    n: int,
    sessions: list[np.ndarray] | None = None,
) -> np.ndarray:
    raw = scores >= threshold
    output = np.zeros(raw.size, dtype=bool)
    active_sessions = station_sessions(frame) if sessions is None else sessions
    for indices in active_sessions:
        votes = pd.Series(raw[indices].astype(np.int8)).rolling(n, min_periods=1).sum().to_numpy()
        output[indices] = votes >= k
    return output


def binary_counts(labels: np.ndarray, predictions: np.ndarray) -> dict[str, float | int]:
    labels = labels.astype(bool)
    predictions = predictions.astype(bool)
    tp = int(np.sum(labels & predictions))
    fp = int(np.sum(~labels & predictions))
    fn = int(np.sum(labels & ~predictions))
    tn = int(np.sum(~labels & ~predictions))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def predicted_runs(
    frame: pd.DataFrame,
    predictions: np.ndarray,
    sessions: list[np.ndarray] | None = None,
) -> list[np.ndarray]:
    runs: list[np.ndarray] = []
    active_sessions = station_sessions(frame) if sessions is None else sessions
    for session in active_sessions:
        active = predictions[session].astype(bool)
        boundaries = np.diff(np.r_[False, active, False].astype(np.int8))
        starts = np.flatnonzero(boundaries == 1)
        ends = np.flatnonzero(boundaries == -1)
        runs.extend(session[left:right] for left, right in zip(starts, ends))
    return runs


def episode_metrics(
    frame: pd.DataFrame,
    predictions: np.ndarray,
    sessions: list[np.ndarray] | None = None,
    station_days: int | None = None,
) -> dict[str, float | int | None]:
    labels = frame["is_fault"].to_numpy(bool)
    runs = predicted_runs(frame, predictions, sessions)
    true_predicted_runs = sum(bool(labels[run].any()) for run in runs)
    false_predicted_runs = len(runs) - true_predicted_runs

    fault_rows = frame.loc[labels].copy()
    valid_episode = fault_rows["episode_id"].ne("") & fault_rows["episode_id"].ne("nan")
    fault_rows = fault_rows.loc[valid_episode]
    detected_episodes = 0
    latencies: list[float] = []
    for _, episode in fault_rows.groupby("episode_id", sort=False):
        indices = episode.index.to_numpy(np.int64)
        detected = indices[predictions[indices]]
        if detected.size:
            detected_episodes += 1
            start = episode["emitted_timestamp_utc"].min()
            first_detection = frame.loc[detected, "emitted_timestamp_utc"].min()
            latencies.append(max(0.0, (first_detection - start).total_seconds() / 60.0))

    true_episodes = int(fault_rows["episode_id"].nunique())
    incident_precision = true_predicted_runs / max(len(runs), 1)
    incident_recall = detected_episodes / max(true_episodes, 1)
    incident_f1 = 2.0 * incident_precision * incident_recall / max(
        incident_precision + incident_recall, 1e-12
    )
    if station_days is None:
        station_days = int(
            frame.assign(observed_date=frame["emitted_timestamp_utc"].dt.date)
            .drop_duplicates(["station_id", "observed_date"])
            .shape[0]
        )
    return {
        "predicted_incidents": len(runs),
        "true_positive_predicted_incidents": true_predicted_runs,
        "false_positive_predicted_incidents": false_predicted_runs,
        "true_fault_episodes": true_episodes,
        "detected_fault_episodes": detected_episodes,
        "incident_precision": incident_precision,
        "episode_recall": incident_recall,
        "incident_f1": incident_f1,
        "false_alert_incidents_per_station_day": false_predicted_runs / max(station_days, 1),
        "observed_station_days": station_days,
        "median_detection_latency_minutes": float(np.median(latencies)) if latencies else None,
        "p90_detection_latency_minutes": float(np.quantile(latencies, 0.90)) if latencies else None,
    }


def expected_calibration_error(labels: np.ndarray, scores: np.ndarray, bins: int = 10) -> float:
    labels = labels.astype(bool)
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = labels.size
    ece = 0.0
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (scores >= left) & (scores < right if right < 1.0 else scores <= right)
        if mask.any():
            ece += mask.mean() * abs(float(scores[mask].mean()) - float(labels[mask].mean()))
    return float(ece)


def evaluate(
    frame: pd.DataFrame,
    scores: np.ndarray,
    threshold: float,
    k: int,
    n: int,
    sessions: list[np.ndarray] | None = None,
    station_days: int | None = None,
) -> tuple[dict[str, object], np.ndarray]:
    predictions = apply_persistence(frame, scores, threshold, k, n, sessions)
    labels = frame["is_fault"].to_numpy(bool)
    weather = frame["is_weather"].to_numpy(bool)
    row = binary_counts(labels, predictions)
    row.update(episode_metrics(frame, predictions, sessions, station_days))
    row.update(
        {
            "rows": int(len(frame)),
            "stations": int(frame["station_id"].nunique()),
            "fault_rows": int(labels.sum()),
            "weather_rows": int(weather.sum()),
            "fault_auprc": float(average_precision_score(labels, scores)),
            "brier_score": float(brier_score_loss(labels.astype(int), scores)),
            "ece_10_bin": expected_calibration_error(labels, scores),
            "weather_rows_flagged_as_fault": int(np.sum(weather & predictions)),
            "weather_false_fault_rate": float(np.mean(predictions[weather])) if weather.any() else None,
            "threshold": float(threshold),
            "persistence_k": int(k),
            "persistence_n": int(n),
        }
    )
    return row, predictions


@dataclass(frozen=True)
class Policy:
    candidate: str
    threshold: float
    k: int
    n: int
    eligible: bool
    tune_incident_f1: float
    tune_incident_precision: float
    tune_episode_recall: float
    tune_false_alert_rate: float


def tune_candidates(
    frame: pd.DataFrame,
    score_candidates: dict[str, np.ndarray],
) -> tuple[Policy, Policy, pd.DataFrame]:
    records: list[dict[str, object]] = []
    thresholds = np.linspace(0.02, 0.98, 49)
    persistence_options = ((1, 1), (2, 3), (3, 5))
    sessions = station_sessions(frame)
    station_days = int(
        frame.assign(observed_date=frame["emitted_timestamp_utc"].dt.date)
        .drop_duplicates(["station_id", "observed_date"])
        .shape[0]
    )
    for candidate, scores in score_candidates.items():
        for threshold in thresholds:
            for k, n in persistence_options:
                metrics, _ = evaluate(
                    frame,
                    scores,
                    float(threshold),
                    k,
                    n,
                    sessions=sessions,
                    station_days=station_days,
                )
                eligible = bool(
                    metrics["incident_precision"] >= 0.80
                    and metrics["false_alert_incidents_per_station_day"] <= 0.020
                    and metrics["predicted_incidents"] > 0
                )
                records.append(
                    {
                        "candidate": candidate,
                        "threshold": float(threshold),
                        "k": k,
                        "n": n,
                        "eligible": eligible,
                        **metrics,
                    }
                )
    table = pd.DataFrame(records)
    best_f1_row = table.sort_values(
        ["incident_f1", "false_alert_incidents_per_station_day", "precision"],
        ascending=[False, True, False],
        kind="stable",
    ).iloc[0]
    eligible = table.loc[table["eligible"]]
    guarded_row = (
        eligible.sort_values(
            ["incident_f1", "episode_recall", "false_alert_incidents_per_station_day"],
            ascending=[False, False, True],
            kind="stable",
        ).iloc[0]
        if len(eligible)
        else best_f1_row
    )

    def convert(row: pd.Series, is_eligible: bool) -> Policy:
        return Policy(
            candidate=str(row["candidate"]),
            threshold=float(row["threshold"]),
            k=int(row["k"]),
            n=int(row["n"]),
            eligible=is_eligible,
            tune_incident_f1=float(row["incident_f1"]),
            tune_incident_precision=float(row["incident_precision"]),
            tune_episode_recall=float(row["episode_recall"]),
            tune_false_alert_rate=float(row["false_alert_incidents_per_station_day"]),
        )

    return convert(best_f1_row, bool(best_f1_row["eligible"])), convert(
        guarded_row, bool(len(eligible))
    ), table


def frame_subset(frame: pd.DataFrame, mask: np.ndarray) -> pd.DataFrame:
    return frame.loc[mask].reset_index(drop=True)


def subset_scores(scores: dict[str, np.ndarray], mask: np.ndarray) -> dict[str, np.ndarray]:
    return {name: values[mask] for name, values in scores.items()}


def save_predictions(
    name: str,
    frame: pd.DataFrame,
    scores: dict[str, np.ndarray],
    selected_scores: np.ndarray,
    predictions: np.ndarray,
) -> Path:
    columns = [
        "row_id",
        "station_id",
        "emitted_timestamp_utc",
        "is_fault",
        "is_weather",
        "episode_id",
        "anomaly_type",
        "anomaly_sensor",
    ]
    output = frame.loc[:, [column for column in columns if column in frame.columns]].copy()
    for model_name, values in scores.items():
        output[f"{model_name}_probability"] = values
    output["selected_probability"] = selected_scores
    output["selected_fault_prediction"] = predictions.astype(np.int8)
    path = OUTPUT_DIR / f"{name}_predictions.csv.gz"
    output.to_csv(path, index=False, compression="gzip")
    return path


def raw_data_receipt() -> dict[str, object]:
    frame = pd.read_csv(
        RAW_DATA,
        usecols=["station_id", "timestamp_utc", "source", "pressure_source"],
        low_memory=False,
    )
    timestamps = pd.to_datetime(frame["timestamp_utc"], utc=True)
    return {
        "path": str(RAW_DATA.relative_to(ROOT)),
        "sha256": sha256(RAW_DATA),
        "rows": int(len(frame)),
        "stations": int(frame["station_id"].nunique()),
        "start_utc": timestamps.min().isoformat(),
        "end_utc": timestamps.max().isoformat(),
        "source_counts": {str(k): int(v) for k, v in frame["source"].value_counts(dropna=False).items()},
        "pressure_source_counts": {
            str(k): int(v) for k, v in frame["pressure_source"].value_counts(dropna=False).items()
        },
        "is_authenticated_imd_aws": False,
        "label_provenance": "real observations with injected/simulated fault and weather-event labels",
    }


def main() -> None:
    started = time.perf_counter()
    set_deterministic(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    feature_names = tuple(feature for feature in TCN_FEATURES)
    print(f"Device: {device}; causal sequence features: {len(feature_names)}", flush=True)

    frames = {
        name: load_split(name, feature_names)
        for name in ("train", "validation", "time_test", "station_test")
    }
    train_frame = frames["train"]
    validation_frame = frames["validation"]
    center, scale = fit_normalizer(train_frame, feature_names)

    matrices = {
        name: transform_matrix(frame, feature_names, center, scale)
        for name, frame in frames.items()
    }
    histories = {name: build_history(frame) for name, frame in frames.items()}

    all_train = np.ones(len(train_frame), dtype=bool)
    train_targets = sampled_endpoints(train_frame, all_train, TRAIN_NORMAL_ENDPOINTS, SEED)
    validation_month = validation_frame["emitted_timestamp_utc"].dt.month.to_numpy()
    monitor_mask = validation_month <= 2
    calibration_mask = (validation_month >= 3) & (validation_month <= 4)
    tune_mask = (validation_month >= 5) & (validation_month <= 8)
    confirmation_mask = validation_month >= 9
    monitor_targets = sampled_endpoints(
        validation_frame, monitor_mask, MONITOR_NORMAL_ENDPOINTS, SEED + 1
    )

    input_channels = len(feature_names) + 1
    model_definitions: dict[str, nn.Module] = {
        "tcn": CausalTCN(input_channels=input_channels, hidden_channels=32, dropout=0.15),
        "gru": CausalGRU(input_channels=input_channels, hidden_size=40),
    }
    trained: dict[str, nn.Module] = {}
    history_rows: list[dict[str, object]] = []
    checkpoint_summary: dict[str, dict[str, float | int]] = {}
    for name, model in model_definitions.items():
        model, rows, best_epoch, best_ap = train_model(
            name,
            model,
            matrices["train"],
            histories["train"],
            train_frame,
            train_targets,
            matrices["validation"],
            histories["validation"],
            validation_frame,
            monitor_targets,
            device,
        )
        trained[name] = model
        history_rows.extend(rows)
        checkpoint_summary[name] = {"best_epoch": best_epoch, "monitor_auprc": best_ap}

    raw_scores: dict[str, dict[str, np.ndarray]] = {name: {} for name in frames}
    for split_name in frames:
        targets = np.arange(len(frames[split_name]), dtype=np.int64)
        for model_name, model in trained.items():
            print(f"Scoring {model_name} on {split_name} ({len(targets):,} rows)...", flush=True)
            raw_scores[split_name][model_name] = predict_raw(
                model,
                matrices[split_name],
                histories[split_name],
                targets,
                device,
            )

    calibration_labels = validation_frame.loc[calibration_mask, "is_fault"].to_numpy(bool)
    calibrators: dict[str, LogisticRegression] = {}
    calibrated: dict[str, dict[str, np.ndarray]] = {name: {} for name in frames}
    for model_name in trained:
        calibrators[model_name] = fit_calibrator(
            raw_scores["validation"][model_name][calibration_mask], calibration_labels
        )
        for split_name in frames:
            calibrated[split_name][model_name] = calibrate(
                calibrators[model_name], raw_scores[split_name][model_name]
            )

    # Blend weights are selected only on May-Aug 2023.
    for split_name in frames:
        tcn = calibrated[split_name]["tcn"]
        gru = calibrated[split_name]["gru"]
        calibrated[split_name]["blend_25tcn"] = 0.25 * tcn + 0.75 * gru
        calibrated[split_name]["blend_50tcn"] = 0.50 * tcn + 0.50 * gru
        calibrated[split_name]["blend_75tcn"] = 0.75 * tcn + 0.25 * gru

    tune_frame = frame_subset(validation_frame, tune_mask)
    tune_scores = subset_scores(calibrated["validation"], tune_mask)
    best_f1_policy, guarded_policy, frontier = tune_candidates(tune_frame, tune_scores)
    selected_policy = guarded_policy if guarded_policy.eligible else best_f1_policy
    print("Selected frozen policy:", json.dumps(asdict(selected_policy), indent=2), flush=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(history_rows).to_csv(OUTPUT_DIR / "training_history.csv", index=False)
    frontier.to_csv(OUTPUT_DIR / "policy_frontier.csv", index=False)

    split_evaluations: dict[str, dict[str, object]] = {}
    prediction_paths: list[Path] = []
    evaluation_sets = {
        "development_confirmation_sep_dec_2023": (
            frame_subset(validation_frame, confirmation_mask),
            subset_scores(calibrated["validation"], confirmation_mask),
        ),
        "time_holdout_2024": (frames["time_test"], calibrated["time_test"]),
        "unseen_station_holdout_2024": (frames["station_test"], calibrated["station_test"]),
    }
    metric_rows: list[dict[str, object]] = []
    for split_label, (frame, score_map) in evaluation_sets.items():
        chosen_scores = score_map[selected_policy.candidate]
        metrics, predictions = evaluate(
            frame,
            chosen_scores,
            selected_policy.threshold,
            selected_policy.k,
            selected_policy.n,
        )
        metrics.update({"split": split_label, "candidate": selected_policy.candidate})
        split_evaluations[split_label] = metrics
        metric_rows.append(metrics)
        prediction_paths.append(
            save_predictions(split_label, frame, score_map, chosen_scores, predictions)
        )
        print(
            f"{split_label}: incident P={metrics['incident_precision']:.4f}, "
            f"episode R={metrics['episode_recall']:.4f}, incident F1={metrics['incident_f1']:.4f}, "
            f"point F1={metrics['f1']:.4f}, FA={metrics['false_alert_incidents_per_station_day']:.5f}",
            flush=True,
        )
    pd.DataFrame(metric_rows).to_csv(OUTPUT_DIR / "holdout_metrics.csv", index=False)

    # Store complete inference contracts. These files are challengers only and are not
    # loaded by the current live API.
    model_paths: list[Path] = []
    for model_name, model in trained.items():
        model_path = MODEL_DIR / f"{model_name}.pt"
        torch.save(
            {
                "state_dict": model.state_dict(),
                "architecture": model.__class__.__name__,
                "feature_names": list(feature_names),
                "sequence_length": SEQ_LEN,
                "normalization_center": center,
                "normalization_scale": scale,
                "seed": SEED,
                "checkpoint_selection": checkpoint_summary[model_name],
            },
            model_path,
        )
        model_paths.append(model_path)
    calibrator_path = MODEL_DIR / "calibrators_and_policy.joblib"
    joblib.dump(
        {
            "calibrators": calibrators,
            "selected_policy": asdict(selected_policy),
            "best_f1_policy": asdict(best_f1_policy),
            "guarded_policy": asdict(guarded_policy),
            "feature_names": list(feature_names),
            "sequence_length": SEQ_LEN,
            "normalization_center": center,
            "normalization_scale": scale,
        },
        calibrator_path,
        compress=3,
    )
    model_paths.append(calibrator_path)

    data_receipt = raw_data_receipt()
    split_receipts = {}
    for name, frame in frames.items():
        source_path = FEATURE_DIR / f"{name}_features.csv.gz"
        split_receipts[name] = {
            "path": str(source_path.relative_to(ROOT)),
            "sha256": sha256(source_path),
            "rows_available_to_detector": int(len(frame)),
            "stations": int(frame["station_id"].nunique()),
            "fault_rows": int(frame["is_fault"].sum()),
            "weather_rows": int(frame["is_weather"].sum()),
            "start_utc": frame["emitted_timestamp_utc"].min().isoformat(),
            "end_utc": frame["emitted_timestamp_utc"].max().isoformat(),
        }
    receipt = {
        "raw_data": data_receipt,
        "feature_splits": split_receipts,
        "leakage_controls": {
            "normalization_fit_on": "2022 training only",
            "epoch_selection": "Jan-Feb 2023 only",
            "calibration": "Mar-Apr 2023 only",
            "policy_and_blend_selection": "May-Aug 2023 only",
            "development_confirmation": "Sep-Dec 2023; never used for selection",
            "sealed_time_holdout": "2024; never used for fitting/calibration/selection",
            "sealed_station_holdout": "four stations in 2024; never used for fitting/calibration/selection",
        },
    }
    (OUTPUT_DIR / "data_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    artifacts = model_paths + prediction_paths + [
        OUTPUT_DIR / "training_history.csv",
        OUTPUT_DIR / "policy_frontier.csv",
        OUTPUT_DIR / "holdout_metrics.csv",
        OUTPUT_DIR / "data_receipt.json",
    ]
    result = {
        "experiment": "iteration12_neural_honest",
        "status": "research_challenger_evaluated",
        "promoted": False,
        "promotion_reason": (
            "Not eligible for production promotion: labels are injected research labels, "
            "only 24 NOAA/NCEI proxy stations are available, and this is a single-seed benchmark."
        ),
        "metrics_are_empirical": True,
        "metrics_are_hardcoded": False,
        "seed": SEED,
        "device": str(device),
        "models": {
            "tcn": "causal dilated Conv1D network",
            "gru": "unidirectional GRU sequence classifier",
            "selection_candidates": list(calibrated["validation"].keys()),
            "selected_candidate": selected_policy.candidate,
            "checkpoint_summary": checkpoint_summary,
        },
        "selected_policy": asdict(selected_policy),
        "best_unconstrained_policy": asdict(best_f1_policy),
        "guarded_policy": asdict(guarded_policy),
        "evaluations": split_evaluations,
        "data_summary": data_receipt,
        "limitations": [
            "Historical source is NOAA/NCEI ISD from 24 Indian stations, not authenticated IMD AWS telemetry.",
            "Fault and weather-event labels are injected/simulated, not independently verified maintenance labels.",
            "The unseen-station holdout contains four stations and no labelled genuine-weather scenarios.",
            "Only one deterministic training seed was run for each architecture.",
            "These neural challengers are not connected to the live API or production manifest.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }
    result_path = OUTPUT_DIR / "result_block.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    artifacts.append(result_path)
    checksums = {str(path.relative_to(ROOT)): sha256(path) for path in artifacts}
    (OUTPUT_DIR / "artifact_checksums.json").write_text(
        json.dumps(checksums, indent=2), encoding="utf-8"
    )

    print(f"\nCompleted in {result['runtime_seconds']:.1f}s", flush=True)
    print(f"Evidence: {result_path}", flush=True)


if __name__ == "__main__":
    main()

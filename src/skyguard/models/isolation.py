"""Isolation Forest training and persistence for SkyGuard."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


ISOLATION_FEATURES = (
    "primary_missing_count", "time_since_previous_minutes", "gap_ratio", "out_of_order_indicator",
    "temperature_rate_per_hour", "temperature_robust_z_24h", "temperature_ewma_residual",
    "temperature_rolling_mad_24h", "temperature_frozen_run_length",
    "pressure_rate_per_hour", "pressure_robust_z_24h", "pressure_ewma_residual",
    "pressure_rolling_mad_24h", "pressure_frozen_run_length",
    "humidity_rate_per_hour", "humidity_robust_z_24h", "humidity_ewma_residual",
    "humidity_rolling_mad_24h", "humidity_frozen_run_length",
    "neighbor_temperature_residual", "neighbor_temperature_mad", "neighbor_temperature_agreement_fraction",
    "neighbor_pressure_residual", "neighbor_pressure_mad", "neighbor_pressure_agreement_fraction",
    "neighbor_humidity_residual", "neighbor_humidity_mad", "neighbor_humidity_agreement_fraction",
    "temperature_dewpoint_spread_c", "temperature_humidity_interaction", "pressure_temperature_ratio",
)


def build_model(random_state: int = 26073) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", RobustScaler(quantile_range=(10.0, 90.0))),
        ("model", IsolationForest(
            n_estimators=160,
            max_samples=4096,
            contamination="auto",
            random_state=random_state,
            n_jobs=-1,
        )),
    ])


def anomaly_scores(model: Pipeline, values: np.ndarray) -> np.ndarray:
    """Return scores where larger means more anomalous."""
    return -model.decision_function(values).astype(np.float64)


def save_model(path: Path, model: Pipeline, metadata: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": model, "feature_columns": ISOLATION_FEATURES, "metadata": metadata}, path)

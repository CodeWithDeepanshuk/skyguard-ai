"""Lightweight supervised classifiers used by SkyGuard Phase 5."""

from __future__ import annotations

import numpy as np
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from skyguard.features.contracts import MODEL_FEATURE_COLUMNS


# Absolute calendar position can correlate with synthetic injection schedules. The
# detector keeps causal weather context but excludes these leakage-prone shortcuts.
CLASSIFIER_FEATURES = tuple(
    column for column in MODEL_FEATURE_COLUMNS
    if column not in {"hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos"}
)


def build_classifier(random_state: int = 26073, estimators: int = 320) -> LGBMClassifier:
    return LGBMClassifier(
        objective="multiclass",
        n_estimators=estimators,
        learning_rate=0.04,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=20,
        subsample=0.85,
        colsample_bytree=0.80,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=random_state,
        n_jobs=-1,
        verbosity=-1,
    )


def build_binary_classifier(random_state: int = 26073, estimators: int = 280) -> LGBMClassifier:
    return LGBMClassifier(
        objective="binary", n_estimators=estimators, learning_rate=0.04,
        num_leaves=31, min_child_samples=20, subsample=0.85, colsample_bytree=0.80,
        reg_alpha=0.1, reg_lambda=1.0, random_state=random_state, n_jobs=-1, verbosity=-1,
    )


def calibrate_prefit(model: LGBMClassifier, values: np.ndarray, labels: np.ndarray) -> CalibratedClassifierCV:
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
    calibrated.fit(values, labels)
    return calibrated

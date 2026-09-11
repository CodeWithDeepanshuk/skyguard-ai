"""Classification, calibration, and selective-prediction metrics."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_curve, precision_recall_fscore_support


def classification_report(y_true: np.ndarray, y_pred: np.ndarray, classes: list[str]) -> dict[str, object]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=classes, zero_division=0,
    )
    matrix = confusion_matrix(y_true, y_pred, labels=classes)
    return {
        "classes": classes,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=classes, average="macro", zero_division=0)),
        "per_class": {
            label: {
                "precision": float(precision[index]), "recall": float(recall[index]),
                "f1": float(f1[index]), "support": int(support[index]),
            }
            for index, label in enumerate(classes)
        },
        "confusion_matrix": matrix.astype(int).tolist(),
    }


def expected_calibration_error(
    probabilities: np.ndarray, y_true: np.ndarray, classes: np.ndarray, bins: int = 10,
) -> float:
    predicted_indices = np.argmax(probabilities, axis=1)
    confidence = np.max(probabilities, axis=1)
    predictions = classes[predicted_indices]
    correct = predictions == y_true
    error = 0.0
    boundaries = np.linspace(0.0, 1.0, bins + 1)
    for lower, upper in zip(boundaries[:-1], boundaries[1:]):
        mask = (confidence > lower) & (confidence <= upper)
        if np.any(mask):
            error += float(np.mean(mask)) * abs(float(np.mean(correct[mask])) - float(np.mean(confidence[mask])))
    return error


def multiclass_brier_score(probabilities: np.ndarray, y_true: np.ndarray, classes: np.ndarray) -> float:
    lookup = {label: index for index, label in enumerate(classes)}
    targets = np.zeros_like(probabilities)
    for row, label in enumerate(y_true):
        targets[row, lookup[label]] = 1.0
    return float(np.mean(np.sum((probabilities - targets) ** 2, axis=1)))


def episode_balanced_weights(labels: np.ndarray, episode_ids: np.ndarray) -> np.ndarray:
    """Give every class equal total mass and every episode equal mass inside its class."""
    weights = np.zeros(labels.size, dtype=np.float64)
    for label in np.unique(labels):
        class_mask = labels == label
        class_indices = np.flatnonzero(class_mask)
        groups: dict[str, list[int]] = {}
        for index in class_indices:
            episode = str(episode_ids[index]) or f"row-{index}"
            groups.setdefault(episode, []).append(int(index))
        group_mass = 1.0 / len(groups)
        for indices in groups.values():
            row_mass = group_mass / len(indices)
            weights[indices] = row_mass
    weights *= labels.size / np.sum(weights)
    return weights


def choose_selective_threshold(
    y_true: np.ndarray,
    predictions: np.ndarray,
    confidence: np.ndarray,
    target_accuracy: float,
    minimum_coverage: float = 0.25,
) -> dict[str, float]:
    """Maximize coverage while meeting accepted-prediction accuracy."""
    candidates = np.unique(np.concatenate(([0.0], np.quantile(confidence, np.linspace(0, 1, 101)))))
    options: list[tuple[float, float, float]] = []
    for threshold in candidates:
        accepted = confidence >= threshold
        coverage = float(np.mean(accepted))
        if coverage < minimum_coverage or not np.any(accepted):
            continue
        accuracy = float(np.mean(predictions[accepted] == y_true[accepted]))
        options.append((threshold, coverage, accuracy))
    feasible = [item for item in options if item[2] >= target_accuracy]
    if feasible:
        threshold, coverage, accuracy = max(feasible, key=lambda item: (item[1], item[2], -item[0]))
    else:
        threshold, coverage, accuracy = max(options, key=lambda item: (item[2] * item[1] ** 0.5, item[1]))
    return {"threshold": float(threshold), "coverage": coverage, "accepted_accuracy": accuracy}


def choose_threshold_for_precision(
    labels: np.ndarray, scores: np.ndarray, target_precision: float,
) -> dict[str, float]:
    """Choose maximum validation recall among thresholds meeting a precision target."""
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    options = [
        (float(thresholds[index]), float(precision[index]), float(recall[index]))
        for index in range(thresholds.size)
        if precision[index] >= target_precision
    ]
    if options:
        threshold, selected_precision, selected_recall = max(options, key=lambda item: (item[2], item[1], item[0]))
    else:
        f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
        index = int(np.argmax(f1))
        threshold, selected_precision, selected_recall = float(thresholds[index]), float(precision[index]), float(recall[index])
    return {
        "threshold": threshold, "precision": selected_precision, "recall": selected_recall,
        "target_precision": target_precision,
    }

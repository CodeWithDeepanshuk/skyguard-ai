"""Small causal temporal convolutional network for Phase 10."""

from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset


TCN_FEATURES = (
    "temperature_robust_z_24h", "pressure_robust_z_24h", "humidity_robust_z_24h",
    "temperature_ewma_residual", "pressure_ewma_residual", "humidity_ewma_residual",
    "neighbor_temperature_residual", "neighbor_pressure_residual", "neighbor_humidity_residual",
    "temperature_slope_6h", "pressure_slope_6h", "humidity_slope_6h",
    "temperature_slope_24h", "pressure_slope_24h", "humidity_slope_24h",
    "temperature_neighbor_residual_slope_6h", "pressure_neighbor_residual_slope_6h",
    "humidity_neighbor_residual_slope_6h",
    "temperature_cusum_positive", "temperature_cusum_negative",
    "pressure_cusum_positive", "pressure_cusum_negative",
    "humidity_cusum_positive", "humidity_cusum_negative",
    "temperature_frozen_run_length", "pressure_frozen_run_length", "humidity_frozen_run_length",
    "gap_ratio", "regional_agreement_mean", "regional_standardized_disagreement_max",
)


class CausalBlock(nn.Module):
    def __init__(self, channels: int, dilation: int, dropout: float) -> None:
        super().__init__()
        padding = 2 * dilation
        self.padding = padding
        self.network = nn.Sequential(
            nn.Conv1d(channels, channels, kernel_size=3, dilation=dilation, padding=padding),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(channels, channels, kernel_size=3, dilation=dilation, padding=padding),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.normalization = nn.BatchNorm1d(channels)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        transformed = self.network(values)
        if self.padding:
            transformed = transformed[:, :, : -2 * self.padding]
        return self.normalization(values + transformed)


class CausalTCN(nn.Module):
    def __init__(self, input_channels: int, hidden_channels: int = 32, dropout: float = 0.15) -> None:
        super().__init__()
        self.input_projection = nn.Conv1d(input_channels, hidden_channels, kernel_size=1)
        self.blocks = nn.Sequential(
            CausalBlock(hidden_channels, 1, dropout),
            CausalBlock(hidden_channels, 2, dropout),
            CausalBlock(hidden_channels, 4, dropout),
        )
        self.output = nn.Sequential(nn.Linear(hidden_channels, 24), nn.ReLU(), nn.Dropout(dropout), nn.Linear(24, 1))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        hidden = self.blocks(self.input_projection(values))
        return self.output(hidden[:, :, -1]).squeeze(1)


def sequence_index(station_ids: np.ndarray, timestamps: np.ndarray, length: int) -> np.ndarray:
    """Map every target row to its causal same-station history."""

    result = np.full((station_ids.size, length), -1, dtype=np.int32)
    order = np.lexsort((timestamps, station_ids))
    ordered_stations = station_ids[order]
    boundaries = np.flatnonzero(np.r_[True, ordered_stations[1:] != ordered_stations[:-1], True])
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        indices = order[left:right]
        for lag in range(length):
            if lag >= indices.size:
                break
            result[indices[lag:], length - 1 - lag] = indices[: indices.size - lag]
    return result


class SequenceDataset(Dataset):
    def __init__(
        self, matrix: np.ndarray, history: np.ndarray, targets: np.ndarray,
        labels: np.ndarray | None = None, weights: np.ndarray | None = None,
    ) -> None:
        self.matrix = matrix
        self.history = history
        self.targets = targets.astype(np.int64)
        self.labels = labels
        self.weights = weights

    def __len__(self) -> int:
        return self.targets.size

    def __getitem__(self, item: int) -> tuple[torch.Tensor, ...]:
        target = self.targets[item]
        indices = self.history[target]
        valid = indices >= 0
        sequence = np.zeros((indices.size, self.matrix.shape[1] + 1), dtype=np.float32)
        sequence[valid, :-1] = self.matrix[indices[valid]]
        sequence[valid, -1] = 1.0
        values = torch.from_numpy(sequence.T.copy())
        if self.labels is None:
            return (values,)
        label = torch.tensor(float(self.labels[target]), dtype=torch.float32)
        weight = torch.tensor(1.0 if self.weights is None else float(self.weights[target]), dtype=torch.float32)
        return values, label, weight


class WeightedFocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0) -> None:
        super().__init__()
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
        probabilities = torch.sigmoid(logits)
        pt = torch.where(targets > 0.5, probabilities, 1.0 - probabilities)
        loss = -(1.0 - pt).pow(self.gamma) * torch.log(pt.clamp_min(1e-7))
        return (loss * weights).sum() / weights.sum().clamp_min(1e-7)


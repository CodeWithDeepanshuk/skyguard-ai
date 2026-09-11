from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.models.tcn import CausalTCN, SequenceDataset, sequence_index  # noqa: E402


class Phase10TCNTests(unittest.TestCase):
    def test_history_never_crosses_station(self) -> None:
        stations = np.array(["A", "B", "A", "B"])
        times = np.array([1, 1, 2, 2])
        history = sequence_index(stations, times, 3)
        for row in range(stations.size):
            used = history[row][history[row] >= 0]
            self.assertTrue(np.all(stations[used] == stations[row]))
            self.assertTrue(np.all(times[used] <= times[row]))

    def test_model_output_shape(self) -> None:
        model = CausalTCN(input_channels=5, hidden_channels=8)
        output = model(torch.zeros(4, 5, 12))
        self.assertEqual(tuple(output.shape), (4,))

    def test_dataset_adds_padding_mask(self) -> None:
        matrix = np.ones((2, 3), dtype=np.float32)
        history = np.array([[-1, 0], [0, 1]], dtype=np.int32)
        dataset = SequenceDataset(matrix, history, np.array([0, 1]))
        values = dataset[0][0].numpy()
        self.assertEqual(values.shape, (4, 2))
        self.assertEqual(values[-1].tolist(), [0.0, 1.0])


if __name__ == "__main__":
    unittest.main()

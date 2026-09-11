"""Execute the Iteration 8 unsupervised notebook cells on a small CPU fixture."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

from skyguard.features.phase10 import PHASE10_FEATURES


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_08_MultiClimate_Data_Curriculum_Colab.ipynb"


def fixture(rows_per_station: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(81)
    rows: list[pd.DataFrame] = []
    for domain in ("india", "dwd"):
        for station_number in range(2):
            count = rows_per_station
            frame = pd.DataFrame(
                rng.normal(size=(count, len(PHASE10_FEATURES))).astype(np.float32),
                columns=PHASE10_FEATURES,
            )
            frame["station_id"] = f"{domain}-{station_number}"
            frame["i8_domain"] = domain
            frame["i8_scope"] = "tune"
            frame["emitted_timestamp_utc"] = pd.date_range(
                "2023-01-01", periods=count, freq="1h", tz="UTC"
            )
            frame["is_anomaly"] = 0
            frame.loc[np.arange(30 + station_number, count, 53), "is_anomaly"] = 1
            frame["i8_fault_score"] = np.clip(rng.beta(1.5, 8.0, count), 0, 1)
            rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def notebook_cells() -> list[str]:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    sources = ["".join(cell.get("source", [])) for cell in notebook["cells"] if cell["cell_type"] == "code"]
    markers = (
        "from sklearn.ensemble import IsolationForest",
        "I8_SEQUENCE_WINDOW=24",
        "def i8_lstm_scores(frame):",
    )
    selected = []
    for marker in markers:
        matches = [source for source in sources if marker in source]
        assert len(matches) == 1, f"Expected one notebook cell for {marker!r}, found {len(matches)}"
        selected.append(matches[0])
    return selected


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="skyguard_i8_unsup_") as temporary:
        train = fixture(144)
        tune = fixture(96)
        validation = tune.copy()
        namespace = {
            "np": np,
            "pd": pd,
            "torch": torch,
            "joblib": joblib,
            "FEATURES": list(PHASE10_FEATURES),
            "i8_fit": train,
            "i8_tune": tune,
            "i8_validation": validation,
            "ITER8_ROOT": Path(temporary),
            "REUSE_SAVED_MODELS": False,
            "DEVICE": "cpu",
            "display": lambda *_args, **_kwargs: None,
        }
        for source in notebook_cells():
            exec(compile(source, "iteration8_unsupervised_cell.py", "exec"), namespace)

        scored = namespace["i8_validation"]
        for column in (
            "i8_if_score", "i8_lstm_ae_score", "i8_tree_if_score",
            "i8_tree_lstm_score", "i8_three_model_score",
        ):
            values = pd.to_numeric(scored[column], errors="raise").to_numpy(float)
            assert np.isfinite(values).all()
            assert ((0.0 <= values) & (values <= 1.0)).all()
        assert len(namespace["I8_SCORE_VARIANTS"]) == 4
        assert (Path(temporary) / "iteration8_isolation_forest.joblib").exists()
        assert (Path(temporary) / "iteration8_causal_lstm_autoencoder.pt").exists()
        print(json.dumps({
            "status": "PASS",
            "rows_scored": len(scored),
            "unsupervised_features": len(namespace["I8_UNSUP_FEATURES"]),
            "variants": list(namespace["I8_SCORE_VARIANTS"]),
            "lstm_epochs": len(namespace["i8_lstm_history"]),
        }, indent=2))


if __name__ == "__main__":
    main()

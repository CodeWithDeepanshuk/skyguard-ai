"""Static and causal-contract checks for the Iteration 9 Colab notebook."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_09_Domain_Invariant_Calibration_Colab.ipynb"
PHASE10_REPORT = ROOT / "reports" / "phase10_features.json"


def python_source(source: str) -> str:
    return "\n".join(
        line for line in source.splitlines()
        if not line.lstrip().startswith(("!", "%"))
    )


def function_nodes(source: str, names: set[str]) -> list[ast.FunctionDef]:
    tree = ast.parse(python_source(source))
    return [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]


def main() -> None:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    assert len(cells) >= 110, f"Unexpectedly short notebook: {len(cells)}"
    assert "GPU Iteration 9" in "".join(cells[0].get("source", []))

    code_sources: list[str] = []
    syntax_errors: list[str] = []
    stale_outputs = 0
    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        code_sources.append(source)
        stale_outputs += int(bool(cell.get("outputs")) or cell.get("execution_count") is not None)
        try:
            ast.parse(python_source(source), filename=f"cell_{index}.py")
        except SyntaxError as error:
            syntax_errors.append(f"cell {index}: {error}")

    joined = "\n".join(code_sources)
    assert not syntax_errors, "\n".join(syntax_errors)
    assert stale_outputs == 0, f"Notebook contains {stale_outputs} stale executed cells"

    # Split and lock safety.
    assert "UNLOCK_FINAL_TESTS=True" not in joined
    assert "load_dwd(2024)" not in joined
    assert "load_dwd(2025)" not in joined
    assert "DWD-2024" not in joined
    assert "I9_NEW_STRESS_SEEDS=[9029,9049]" in joined
    assert "set(i9_stress_summary.seed.astype(int))==set(I9_ALL_STRESS_SEEDS)" in joined
    assert "discovery_or_confirmation_used_for_selection':False" in joined

    # Domain-invariant model contract and method checks.
    required_fragments = [
        "I9_EXCLUDED_SHORTCUT_FEATURES",
        "'nearest_neighbor_km'",
        "I9_RESIDUAL_FEATURES",
        "I9_LGB_SEEDS=[17,41,67]",
        "reg_alpha=2.0,reg_lambda=20.0",
        "LogisticRegression(",
        "penalty='l2'",
        "i9_causal_station_z",
        "past=logits.shift(1)",
        "I9_FAULT_META_FEATURES",
        "I9_WEATHER_META_FEATURES",
        "iteration9_calibrator_coefficients.csv",
        "iteration9_residual_feature_importance.csv",
        "iteration9_root_cause_metrics.csv",
        "macro_f1",
        "iteration9_problem_coverage.json",
        "communication gap and duplicate detection",
    ]
    for fragment in required_fragments:
        assert fragment in joined, f"Missing Iteration 9 contract fragment: {fragment}"
    assert "iteration9_sih_score_impact.json" not in joined
    assert "i9_enforce_numeric_features" not in joined
    assert "i9_early_features=i8_enforce_numeric_features(" in joined
    assert "fit_predict(i8_validation" not in joined
    meta_source = next(source for source in code_sources if "I9_FAULT_META_FEATURES=[" in source)
    meta_tree = ast.parse(python_source(meta_source))
    declared_meta: dict[str, list[str]] = {}
    for node in meta_tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in {"I9_FAULT_META_FEATURES", "I9_WEATHER_META_FEATURES"}:
            declared_meta[target.id] = ast.literal_eval(node.value)
    assert set(declared_meta) == {"I9_FAULT_META_FEATURES", "I9_WEATHER_META_FEATURES"}
    identifier_fields = {"i8_domain", "station_id", "cluster", "latitude", "longitude", "nearest_neighbor_km"}
    assert not identifier_fields.intersection(
        declared_meta["I9_FAULT_META_FEATURES"] + declared_meta["I9_WEATHER_META_FEATURES"]
    ), "Identifier leaked into calibration feature declaration"

    # Validate the declared feature count against the production feature report.
    report = json.loads(PHASE10_REPORT.read_text(encoding="utf-8"))
    features = report["model_features"]
    excluded = {
        "temperature_value", "pressure_value", "humidity_value",
        "temperature_humidity_interaction", "pressure_temperature_ratio",
        "nearest_neighbor_km",
    }
    for sensor in ["temperature", "pressure", "humidity"]:
        excluded.update({
            f"{sensor}_lag1", f"{sensor}_rolling_median_24h", f"{sensor}_ewma_prior",
            f"neighbor_{sensor}_weighted_mean", f"neighbor_{sensor}_median",
        })
    residual = [feature for feature in features if feature not in excluded]
    assert len(features) == 108
    assert len(residual) == 87
    assert not excluded.intersection(residual)
    assert "temperature_slope_6h" in residual and "pressure_cusum_positive" in residual

    # Execute the notebook's actual causal normalization helpers. Appending a
    # future observation must not change any already-computed score.
    helper_source = next(source for source in code_sources if "def i9_causal_station_z" in source)
    nodes = function_nodes(helper_source, {"i9_logit_probability", "i9_causal_station_z"})
    namespace = {"np": np, "pd": pd}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "iteration9_causal_helpers.py", "exec"), namespace)
    base = pd.DataFrame({
        "station_id": ["S1"] * 12,
        "emitted_timestamp_utc": pd.date_range("2023-01-01", periods=12, freq="h", tz="UTC"),
        "score": np.linspace(0.05, 0.25, 12),
    })
    reference = {"median": float(np.log(.1 / .9)), "scale": 1.0}
    before = namespace["i9_causal_station_z"](
        base.copy(), "score", reference, window=6, min_periods=3,
    )
    extended = pd.concat([
        base,
        pd.DataFrame({
            "station_id": ["S1"],
            "emitted_timestamp_utc": [pd.Timestamp("2023-01-01T12:00:00Z")],
            "score": [.999],
        }),
    ], ignore_index=True)
    after = namespace["i9_causal_station_z"](
        extended, "score", reference, window=6, min_periods=3,
    )
    np.testing.assert_allclose(before.to_numpy(), after.iloc[: len(base)].to_numpy(), equal_nan=True)
    assert np.isfinite(after.iloc[-1])

    print(json.dumps({
        "status": "PASS",
        "notebook": str(NOTEBOOK),
        "cells": len(cells),
        "code_cells": len(code_sources),
        "syntax_errors": 0,
        "stale_outputs": stale_outputs,
        "full_feature_count": len(features),
        "residual_feature_count": len(residual),
        "excluded_shortcuts": len(excluded),
        "calibration": "chronological L2, no station/domain identifiers",
        "stress_seeds": [8023, 9029, 9049],
        "locked_years_loaded": False,
        "causal_future_append_test": "PASS",
    }, indent=2))


if __name__ == "__main__":
    main()

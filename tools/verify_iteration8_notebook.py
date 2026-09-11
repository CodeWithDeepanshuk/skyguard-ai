"""Static integrity checks for the Iteration 8 Colab notebook."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_08_MultiClimate_Data_Curriculum_Colab.ipynb"
DEV_BUNDLE = ROOT / "deliverables" / "SkyGuard_Iteration8_Development_Data_Bundle.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def python_source(source: str) -> str:
    """Remove Colab shell/magic lines before Python syntax parsing."""
    return "\n".join(
        line for line in source.splitlines()
        if not line.lstrip().startswith(("!", "%"))
    )


def main() -> None:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    assert len(cells) >= 75, f"Unexpectedly short notebook: {len(cells)} cells"
    assert "GPU Iteration 8" in "".join(cells[0].get("source", []))

    syntax_errors: list[str] = []
    code_text: list[str] = []
    stale_outputs = 0
    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        code_text.append(source)
        stale_outputs += int(bool(cell.get("outputs")) or cell.get("execution_count") is not None)
        try:
            ast.parse(python_source(source), filename=f"cell_{index}.py")
        except SyntaxError as error:
            syntax_errors.append(f"cell {index}: {error}")

    joined_code = "\n".join(code_text)
    assert not syntax_errors, "\n".join(syntax_errors)
    assert stale_outputs == 0, f"Notebook contains {stale_outputs} stale executed cells"
    assert "iteration_06_" not in joined_code and "iteration_07_" not in joined_code
    assert "SkyGuard_Iteration8_Locked_2024_Confirmation.zip" not in joined_code
    assert "SkyGuard_Iteration8_Development_Data_Bundle.zip" in joined_code
    assert sha256(DEV_BUNDLE) in joined_code
    assert "assert not any('2024' in name or '2025' in name" in joined_code
    assert "I8_DWD_HOLDOUTS" in joined_code and "dwd_holdout" in joined_code
    assert "str(row.station_id):{key:str(value)" not in joined_code
    assert "str(row['station_id']):{key:str(value)" in joined_code
    assert "Recovered cached DWD feature tables after an interrupted/out-of-order run." in joined_code
    assert "Cell 34 did not complete, so dwd_train/dwd_val do not exist" in joined_code
    assert "def i8_enforce_numeric_features(frame,label):" in joined_code
    assert "numeric.replace([np.inf,-np.inf],np.nan).astype(np.float32)" in joined_code
    assert "i8_fit=i8_enforce_numeric_features(i8_fit,'Combined training table')" in joined_code
    assert "frame=i8_enforce_numeric_features(frame,'Candidate scoring table')" in joined_code
    assert "i8_old_eval.iteration5_reference" not in joined_code
    assert "i8_reference_columns={'iteration3_reference','iteration5_rescue'}" in joined_code
    assert "i8_old_eval['iteration3_reference'].astype(bool)" in joined_code
    assert "i8_old_eval['iteration5_rescue'].astype(bool)" in joined_code
    assert "dev['iteration3_reference']=False" in joined_code
    assert "dev['iteration5_rescue']=materialize_weak_rescue" in joined_code
    assert "IsolationForest" in joined_code and "i8_clean_fit=i8_fit.loc[i8_fit.is_anomaly.eq(0)]" in joined_code
    assert "I8CausalLSTMAutoencoder" in joined_code and "bidirectional=False" in joined_code
    assert "I8_SCORE_VARIANTS" in joined_code and "tree_if_lstm_consensus" in joined_code
    assert "iteration8_unsupervised_training_history.csv" in joined_code
    assert "fit_predict(i8_validation" not in joined_code
    assert "iteration8_result_block.json" in joined_code

    # Execute the notebook's actual dtype-contract helper against the failure mode
    # seen in Colab: numeric values and missing values represented as strings.
    contract_cell = next(source for source in code_text if "def i8_enforce_numeric_features" in source)
    contract_tree = ast.parse(python_source(contract_cell))
    contract_function = next(
        node for node in contract_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "i8_enforce_numeric_features"
    )
    contract_namespace = {"np": np, "pd": pd, "FEATURES": ["feature_a", "feature_b"]}
    exec(compile(ast.Module(body=[contract_function], type_ignores=[]), "numeric_contract.py", "exec"),
         contract_namespace)
    contract_frame = pd.DataFrame({
        "feature_a": ["1.25", ""],
        "feature_b": ["inf", "-2.5"],
    })
    contract_namespace["i8_enforce_numeric_features"](contract_frame, "smoke")
    assert all(pd.api.types.is_float_dtype(contract_frame[column]) for column in contract_frame)
    assert np.isnan(contract_frame.loc[1, "feature_a"])
    assert np.isnan(contract_frame.loc[0, "feature_b"])

    print(json.dumps({
        "status": "PASS",
        "notebook": str(NOTEBOOK),
        "cells": len(cells),
        "code_cells": len(code_text),
        "syntax_errors": 0,
        "stale_outputs": stale_outputs,
        "development_bundle_sha256": sha256(DEV_BUNDLE),
        "iterations_6_or_7_rerun": False,
        "locked_2024_bundle_referenced_by_code": False,
        "clean_only_isolation_forest": True,
        "causal_lstm_autoencoder": True,
        "fault_score_variants": 4,
    }, indent=2))


if __name__ == "__main__":
    main()

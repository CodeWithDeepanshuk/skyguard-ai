"""Static, bundle-integrity, lock-safety and source-regression checks for Iteration 10."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

from collections import deque
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb"
STARTER = ROOT / "deliverables" / "SkyGuard_Iteration10_Final_Starter_Bundle.zip"
DWD = ROOT / "deliverables" / "SkyGuard_Iteration8_Development_Data_Bundle.zip"
EXPECTED_STARTER = "47b5db0ccea2b46f4adbc24ac41a8ccf4a08c4f140234544009a4ba95bf850f7"
EXPECTED_DWD = "7f47466805309faf528d6abc8f04a588c4accbaf454989e36a2b4ff5b31681d4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    assert NOTEBOOK.is_file()
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) == 36
    assert "GPU Iteration 10" in "".join(notebook["cells"][0]["source"])

    sources: list[str] = []
    errors: list[str] = []
    stale = 0
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        sources.append(source)
        stale += int(bool(cell.get("outputs")) or cell.get("execution_count") is not None)
        try:
            ast.parse(python_source(source), filename=f"iteration10_cell_{index}.py")
        except SyntaxError as error:
            errors.append(f"cell {index}: {error}")
    assert not errors, "\n".join(errors)
    assert stale == 0
    joined = "\n".join(sources)

    required = (
        "UNLOCK_FINAL_TESTS=False",
        "LOCKED_YEARS=(2024,2025)",
        "MAIN_SEED=10023",
        "STRESS_SEEDS=(10061,10103)",
        "MultiClimateCurriculum",
        "FaultInjector",
        "set(OPERATIONAL_FAULT_FAMILIES)<=set(main_events.anomaly_type)",
        "set(WEATHER_FAMILIES)<=set(main_events.anomaly_type)",
        "I10_EXCLUDED.update({feature for feature in PHASE10_FEATURES if feature.startswith('neighbor_pressure_')})",
        "causal_arrival_timestamp_utc",
        "stream_order",
        "bridge_detection_labels",
        "verified_heartbeat",
        "independent_weather_gate",
        "drift_evidence_score",
        "STATE_SEEDS=(2017,2041,2067)",
        "LogisticRegression(C=.5,penalty='l2'",
        "def apply_policy",
        "policy_selection_state=main_state.loc[~policy_holdout].copy()",
        "decision_run_id",
        "confirmation_used_for_selection':False",
        "iteration10_fault_episode_recall.csv",
        "iteration10_root_cause_metrics.csv",
        "iteration10_calibration_metrics.json",
        "iteration10_correction_metrics.csv",
        "iteration10_integrity_receipt.json",
        "locked_2024_2025_unopened",
    )
    for fragment in required:
        assert fragment in joined, f"Missing required contract: {fragment}"

    forbidden = (
        "UNLOCK_FINAL_TESTS=True",
        "iteration5_reference",
        "i9_enforce_numeric_features",
        "fit_predict(i8_validation",
        "random_split",
        "train_test_split(",
    )
    for fragment in forbidden:
        assert fragment not in joined, f"Forbidden/stale fragment: {fragment}"

    # Locked years may appear in safety constants and reports, but never in an
    # observation reader or filename constructor.
    reader_patterns = (
        r"read_csv\([^\n]*(?:2024|2025)",
        r"load_dwd\((?:2024|2025)\)",
        r"aws_.*(?:2024|2025).*\.csv",
        r"dwd_.*(?:2024|2025).*\.csv",
    )
    for pattern in reader_patterns:
        assert not re.search(pattern, joined, flags=re.IGNORECASE), f"Locked reader pattern: {pattern}"

    assert sha256(STARTER) == EXPECTED_STARTER
    assert sha256(DWD) == EXPECTED_DWD
    with zipfile.ZipFile(STARTER) as archive:
        names = archive.namelist()
        assert not any("2024" in name.lower() or "2025" in name.lower() for name in names)
        manifest_name = "SkyGuard_Iteration10_Final_Starter_Bundle/bundle_manifest.json"
        manifest = json.loads(archive.read(manifest_name))
        assert manifest["development_years"] == [2022, 2023]
        assert manifest["locked_observation_years_included"] == []
        assert "src/skyguard/faults/injector.py" in {item["path"] for item in manifest["files"]}
        assert "src/skyguard/incidents/state.py" in {item["path"] for item in manifest["files"]}

    sys.path.insert(0, str(ROOT / "src"))
    from skyguard.features.phase10 import PHASE10_FEATURES  # noqa: PLC0415

    excluded = {
        "temperature_value", "pressure_value", "humidity_value", "temperature_humidity_interaction",
        "pressure_temperature_ratio", "nearest_neighbor_km", "pressure_climatology_residual",
        "regional_agreement_mean", "regional_agreement_min", "regional_agreeing_sensor_count",
        "regional_standardized_disagreement_max", "regional_trend_disagreement_mean",
    }
    for sensor in ("temperature", "pressure", "humidity"):
        excluded.update({
            f"{sensor}_lag1", f"{sensor}_rolling_median_24h", f"{sensor}_ewma_prior",
            f"neighbor_{sensor}_weighted_mean", f"neighbor_{sensor}_median",
        })
    excluded.update(feature for feature in PHASE10_FEATURES if feature.startswith("neighbor_pressure_"))
    strict = [feature for feature in PHASE10_FEATURES if feature not in excluded]
    assert len(PHASE10_FEATURES) == 108
    assert len(strict) >= 75
    assert not any(feature.startswith("neighbor_pressure_") for feature in strict)
    assert "pressure_slope_12h" in strict and "pressure_cusum_positive" in strict

    # Execute the actual state-policy helpers against a non-contiguous input
    # index and an all-normal block.  These cases previously caused notebook
    # crashes or accidentally merged separate incidents.
    policy_source = next(source for source in sources if "def apply_policy(frame,policy):" in source)
    nodes = function_nodes(policy_source, {"apply_policy", "predicted_incidents", "truth_incidents"})
    namespace = {"np": np, "pd": pd, "deque": deque}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "iteration10_policy_helpers.py", "exec"), namespace)
    synthetic = pd.DataFrame({
        "eval_station_id": ["india|meteorological|A"] * 4,
        "causal_arrival_timestamp_utc": pd.date_range("2023-09-01", periods=4, freq="h", tz="UTC").astype(str),
        "stream_order": [0, 1, 2, 3],
        "state_p_sensor_fault": [.01, .01, .01, .01],
        "state_p_genuine_weather": [.01, .01, .01, .01],
        "state_p_normal": [.98, .98, .98, .98],
        "independent_weather_gate": [0, 0, 0, 0],
        "drift_evidence_score": [0.0, 0.0, 0.0, 0.0],
        "hard_fault": [0, 0, 0, 0],
        "root_cause_row": ["normal"] * 4,
        "i10_scope": ["confirmation"] * 4,
        "i10_domain": ["india"] * 4,
        "i10_lane": ["meteorological"] * 4,
    }, index=[10, 20, 30, 40])
    decided = namespace["apply_policy"](
        synthetic,
        {"fault_threshold": .5, "weather_threshold": .5, "k": 2, "n": 3, "recovery_points": 2},
    )
    assert decided.index.tolist() == [0, 1, 2, 3]
    assert decided["decision_state"].eq("normal").all()
    empty_predictions = namespace["predicted_incidents"](decided)
    assert empty_predictions.empty and "decision_state" in empty_predictions.columns
    empty_truth = namespace["truth_incidents"](
        pd.DataFrame(columns=["scope", "label_category"]), "confirmation", "sensor_fault"
    )
    assert empty_truth.empty and "station_id" in empty_truth.columns

    print(json.dumps({
        "status": "PASS",
        "notebook": str(NOTEBOOK),
        "cells": len(notebook["cells"]),
        "code_cells": len(sources),
        "syntax_errors": 0,
        "stale_outputs": stale,
        "phase10_features": len(PHASE10_FEATURES),
        "strict_features": len(strict),
        "starter_sha256": EXPECTED_STARTER,
        "dwd_sha256": EXPECTED_DWD,
        "locked_observation_readers": 0,
        "policy_empty_and_noncontiguous_smoke": "PASS",
    }, indent=2))


if __name__ == "__main__":
    main()

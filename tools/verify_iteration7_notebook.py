"""Static integrity checks for the generated Iteration 7 Colab notebook."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_07_Climate_Calibration_Causal_TCN_Colab.ipynb"

nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
code_cells = [cell for cell in nb["cells"] if cell.get("cell_type") == "code"]
assert code_cells
assert all(cell.get("execution_count") is None for cell in code_cells)
assert all(not cell.get("outputs") for cell in code_cells)

compile_errors = []
for index, cell in enumerate(nb["cells"], start=1):
    if cell.get("cell_type") != "code":
        continue
    source = "".join(cell.get("source", []))
    if any(line.lstrip().startswith(("!", "%")) for line in source.splitlines()):
        continue
    try:
        compile(source, f"iteration7_cell_{index}", "exec")
    except SyntaxError as error:
        compile_errors.append({"cell": index, "error": str(error)})
assert not compile_errors, compile_errors

all_code = "\n".join("".join(cell.get("source", [])) for cell in code_cells)
assert "UNLOCK_FINAL_TESTS=False" in all_code
assert "assert UNLOCK_FINAL_TESTS is False" in all_code
assert "load_table('time_test')" not in all_code
assert 'load_table("time_test")' not in all_code
assert "load_table('station_test')" not in all_code
assert 'load_table("station_test")' not in all_code
assert "weak7_confirmation_pass" in all_code
assert "weather7_confirmation_pass" in all_code
assert "pseudo_unseen_all_2023" in all_code
assert "temperature_dewpoint_spread_c" in all_code  # present only in explicit forbidden-feature assertions

required_outputs = {
    "iteration7_result_block.json",
    "iteration7_integrity_receipt.json",
    "iteration7_communication_contract.json",
    "iteration7_weather_policy_frontier.csv",
    "iteration7_weather_confirmation.csv",
    "iteration7_weather_station_metrics.csv",
    "iteration7_tcn_training_history.csv",
    "iteration7_weak_policy_frontier.csv",
    "iteration7_weak_confirmation.csv",
    "iteration7_multiblock_ablation.csv",
    "iteration7_fault_episode_recall.csv",
    "iteration7_feature_contract.json",
}
missing_outputs = sorted(name for name in required_outputs if name not in all_code)
assert not missing_outputs, missing_outputs

print(json.dumps({
    "status": "pass",
    "notebook": str(NOTEBOOK),
    "cells": len(nb["cells"]),
    "code_cells": len(code_cells),
    "compile_errors": 0,
    "unexecuted_clean_template": True,
    "final_test_load_calls": 0,
    "required_return_files": len(required_outputs),
}, indent=2))

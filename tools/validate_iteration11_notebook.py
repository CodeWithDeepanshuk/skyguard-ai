"""Validate the Iteration 11 Colab notebook syntax, AST, and logic integrity."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_11_Colab.ipynb"


def main() -> None:
    assert NOTEBOOK.exists(), f"Notebook not found: {NOTEBOOK}"
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = nb["cells"]
    assert len(cells) == 36, f"Expected 36 cells, got {len(cells)}"

    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    syntax_errors = []

    for i, cell in enumerate(code_cells):
        src = "".join(cell.get("source", []))
        # Filter IPython magics and bash commands for AST validation
        clean_lines = []
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("!") or stripped.startswith("%") or stripped.startswith("display("):
                clean_lines.append(f"# {line}")
            else:
                clean_lines.append(line)
        clean_src = "\n".join(clean_lines)

        try:
            ast.parse(clean_src)
        except SyntaxError as e:
            syntax_errors.append(f"Cell {i}: {e}")

    full_text = "".join("".join(c.get("source", [])) for c in cells)

    checks = {
        "all_code_cells_parse": len(syntax_errors) == 0,
        "bundle_reference_updated": "SkyGuard_Iteration11_All_India_545_Stations_Bundle.zip" in full_text,
        "single_sensor_freeze_present": "SINGLE_SENSOR_FREEZE" in full_text,
        "pareto_policy_selection_present": "BALANCED_PARETO_POLICY_FROZEN" in full_text,
        "no_0_95_fallback_trap": "worst_domain_false_alerts_per_station_day" not in full_text or "Pareto fallback" in full_text,
        "no_direct_locked_observation_read": "data/processed/aws_observations_2024" not in full_text and "data/blind_2025" not in full_text,
    }

    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "notebook": str(NOTEBOOK),
        "total_cells": len(cells),
        "code_cells": len(code_cells),
        "checks": checks,
        "syntax_errors": syntax_errors,
    }

    out_path = ROOT / "reports" / "iteration11_notebook_validation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    assert report["status"] == "PASS", f"Validation failed: {checks}"


if __name__ == "__main__":
    main()

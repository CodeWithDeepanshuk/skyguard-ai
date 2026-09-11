"""Static and synthetic regression checks for the Iteration 10R Colab."""

from __future__ import annotations

import ast
import json
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_10R_Calibration_Integrity_Repair_Colab.ipynb"
REPORT = ROOT / "reports" / "iteration10r_notebook_validation.json"


def cell_source(cell: dict[str, object]) -> str:
    return "".join(cell.get("source", []))


def extract_function(code: str, function_name: str, namespace: dict[str, object]):
    tree = ast.parse(code)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function_name]
    if len(nodes) != 1:
        raise AssertionError(f"Expected one {function_name}, found {len(nodes)}")
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, NOTEBOOK.as_posix(), "exec"), namespace)
    return namespace[function_name]


notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
sources = [cell_source(cell) for cell in notebook["cells"]]
combined = "\n".join(sources)
checks: dict[str, bool] = {}

syntax_errors: list[dict[str, object]] = []
for index, cell in enumerate(notebook["cells"]):
    text = cell_source(cell)
    if cell.get("cell_type") != "code" or "!pip" in text:
        continue
    try:
        ast.parse(text)
    except SyntaxError as error:
        syntax_errors.append({"cell": index, "line": error.lineno, "message": error.msg})
checks["all_code_cells_parse"] = not syntax_errors
checks["balanced_calibrator_removed"] = "class_weight='balanced'" not in sources[22]
checks["typed_cache_reload_present"] = "dtype={'station_id':str,'eval_station_id':str,'row_id':str}" in sources[14]
checks["new_cache_schema_present"] = "iteration10r-v2-string-station-id-natural-prior" in combined
checks["holdout_nonempty_assertions_present"] = "HOLDOUT_INTEGRITY['india_main_rows']>0" in sources[14]
checks["policy_fails_closed"] = "FROZEN_POLICY=EVALUATION_POLICY if POLICY_PROMOTABLE else None" in sources[26]
checks["separate_fault_weather_runs"] = all(
    token in sources[20] for token in ("fault_candidate_run_length", "weather_candidate_run_length")
)
checks["multi_evidence_drift_present"] = all(
    token in sources[20] for token in ("ordered[:,-2]", "drift_support_count", "isolated_drift_gate")
)
checks["weather_veto_present"] = "not weather_supported" in sources[26]
checks["downstream_uses_diagnostic_policy_explicitly"] = (
    "EVALUATION_POLICY" in sources[28] and "EVALUATION_POLICY" in sources[30]
)
checks["conformal_correction_intervals_present"] = all(
    token in sources[32] for token in ("development_conformal_90", "target_marginal_coverage", "coverage_gap_to_90")
)
checks["sensor_health_fails_closed"] = all(
    token in sources[32] for token in ("if POLICY_PROMOTABLE", "shadow_unvalidated", "no automatic maintenance action")
)
checks["no_direct_locked_observation_read"] = not any(
    token in combined for token in ("dwd_aws_10min_2024", "dwd_aws_10min_2025", "india_aws_2024", "india_aws_2025")
)

# Cache identifier regression.
normalise = extract_function(sources[14], "normalise_feature_identifiers", {"pd": pd})
identifier_frame = pd.DataFrame(
    {"station_id": [42182, "DWD-00001.0"], "eval_station_id": ["india|x|42182", "dwd|x|DWD-00001"],
     "row_id": ["1.0", "abc"]}
)
normalised = normalise(identifier_frame, "synthetic")
checks["identifier_regression_pass"] = (
    normalised.station_id.tolist() == ["42182", "DWD-00001"]
    and normalised.row_id.tolist() == ["1", "abc"]
)

# Prior scaling regression: force three deliberately wrong mean probabilities to
# converge to a rare-fault target prior.
cal_namespace = {"np": np}
apply_prior_scaling = extract_function(sources[22], "apply_prior_scaling", cal_namespace)
rng = np.random.default_rng(26073)
base = rng.dirichlet([2.0, 2.0, 2.0], size=5000)
target = np.array([0.975, 0.018, 0.007], dtype=float)
scales = np.ones(3, dtype=float)
for _ in range(300):
    current = apply_prior_scaling(base, scales).mean(axis=0)
    scales *= target / np.clip(current, 1e-9, None)
    scales /= scales[0]
scaled = apply_prior_scaling(base, scales)
checks["prior_scaling_regression_pass"] = bool(np.max(np.abs(scaled.mean(axis=0) - target)) < 2e-4)

# Stateful policy regression: coherent weather must not become a fault; isolated
# drift must become a fault; hard faults and high-confidence slow-cadence faults
# must alert immediately.
policy_namespace = {"np": np, "pd": pd, "deque": deque}
apply_policy = extract_function(sources[26], "apply_policy", policy_namespace)
times = pd.date_range("2023-03-10", periods=13, freq="h", tz="UTC")
rows = []
for index, timestamp in enumerate(times):
    row = {
        "eval_station_id": "india|meteorological|42182", "causal_arrival_timestamp_utc": timestamp,
        "stream_order": index, "state_p_normal": 0.98, "state_p_sensor_fault": 0.01,
        "state_p_genuine_weather": 0.01, "hard_fault": 0, "independent_weather_gate": 0,
        "safe_weather_agreement": 0.0, "isolated_drift_gate": 0, "drift_support_count": 0,
        "drift_evidence_score": 0.0, "expected_interval_minutes": 60.0,
    }
    if 5 <= index <= 7:
        row.update(state_p_normal=0.10, state_p_sensor_fault=0.20, state_p_genuine_weather=0.70,
                   independent_weather_gate=1, safe_weather_agreement=0.90)
    if 9 <= index <= 11:
        row.update(state_p_normal=0.10, state_p_sensor_fault=0.85, state_p_genuine_weather=0.05,
                   isolated_drift_gate=1, drift_support_count=5, drift_evidence_score=8.0)
    if index == 12:
        row.update(state_p_normal=0.0, state_p_sensor_fault=1.0, hard_fault=1)
    rows.append(row)
policy = {
    "fault_threshold": 0.50, "weather_threshold": 0.50, "k": 2, "n": 3,
    "window_minutes": 720, "enable_drift_rescue": True, "drift_rescue_threshold": 6.0,
    "drift_min_fault_probability": 0.20, "weather_agreement_threshold": 0.55,
    "weather_probability_floor": 0.10, "recovery_points": 2,
}
decisions = apply_policy(pd.DataFrame(rows), policy)
checks["weather_not_misclassified_as_fault_regression"] = not decisions.iloc[5:8].decision_state.eq("sensor_fault").any()
checks["weather_detected_regression"] = decisions.iloc[5:9].decision_state.eq("genuine_weather").any()
checks["isolated_drift_detected_regression"] = decisions.iloc[9:12].decision_state.eq("sensor_fault").any()
checks["hard_fault_immediate_regression"] = decisions.iloc[12].decision_state == "sensor_fault"

slow = pd.DataFrame([{
    "eval_station_id": "india|operational|slow", "causal_arrival_timestamp_utc": pd.Timestamp("2023-03-10", tz="UTC"),
    "stream_order": 0, "state_p_normal": 0.02, "state_p_sensor_fault": 0.96,
    "state_p_genuine_weather": 0.02, "hard_fault": 0, "independent_weather_gate": 0,
    "safe_weather_agreement": 0.0, "isolated_drift_gate": 1, "drift_support_count": 5,
    "drift_evidence_score": 8.0, "expected_interval_minutes": 180.0,
}])
checks["slow_cadence_high_confidence_immediate_regression"] = (
    apply_policy(slow, policy).iloc[0].decision_state == "sensor_fault"
)

checks = {name: bool(value) for name, value in checks.items()}
status = "PASS" if all(checks.values()) else "FAIL"
payload = {
    "status": status,
    "notebook": str(NOTEBOOK),
    "cell_count": len(notebook["cells"]),
    "code_cell_count": sum(cell.get("cell_type") == "code" for cell in notebook["cells"]),
    "checks": checks,
    "syntax_errors": syntax_errors,
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
raise SystemExit(0 if status == "PASS" else 1)

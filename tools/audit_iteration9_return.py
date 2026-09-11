"""Reconcile the user-returned Iteration 9 Colab artifacts and write an audit receipt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "reports" / "gpu_iterations" / "iteration9_returned_2026-08-30"
LOCAL_NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_09_Domain_Invariant_Calibration_Colab.ipynb"
ITER8_RESULT = (
    ROOT / "reports" / "gpu_iterations" / "iteration8_returned_2026-08-29"
    / "iteration8_result_block.json"
)
AUDIT_PATH = ARCHIVE / "iteration9_audit_report.json"
MANIFEST_PATH = ARCHIVE / "archive_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(name: str) -> dict[str, Any]:
    return json.loads((ARCHIVE / name).read_text(encoding="utf-8"))


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(ARCHIVE / name)


def comparable(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return str(value)


def reconcile_records(
    csv_frame: pd.DataFrame,
    json_records: list[dict[str, Any]],
    keys: list[str],
) -> dict[str, Any]:
    json_frame = pd.DataFrame(json_records)
    common = [column for column in json_frame.columns if column in csv_frame.columns]
    left = csv_frame[common].sort_values(keys).reset_index(drop=True)
    right = json_frame[common].sort_values(keys).reset_index(drop=True)
    mismatches: list[dict[str, Any]] = []
    if left.shape != right.shape:
        return {
            "status": "FAIL",
            "csv_shape": list(left.shape),
            "json_shape": list(right.shape),
            "mismatches": [{"reason": "shape mismatch"}],
        }
    for row in range(len(left)):
        for column in common:
            a, b = left.at[row, column], right.at[row, column]
            if pd.isna(a) and pd.isna(b):
                continue
            if isinstance(a, (int, float, np.number)) and isinstance(b, (int, float, np.number)):
                if np.isclose(float(a), float(b), rtol=1e-10, atol=1e-12, equal_nan=True):
                    continue
            elif str(a) == str(b):
                continue
            mismatches.append({
                "row": row,
                "column": column,
                "csv": comparable(a),
                "json": comparable(b),
            })
            if len(mismatches) >= 25:
                break
        if len(mismatches) >= 25:
            break
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "rows": len(left),
        "columns_compared": common,
        "mismatches": mismatches,
    }


def recall_from_precision_f1(precision: float, f1: float) -> float:
    denominator = 2 * precision - f1
    return float(f1 * precision / denominator) if denominator > 0 else 0.0


def inspect_notebook(path: Path) -> dict[str, Any]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    code_indices = [index for index, cell in enumerate(cells) if cell.get("cell_type") == "code"]
    error_outputs: list[dict[str, Any]] = []
    unexecuted: list[dict[str, Any]] = []
    for index in code_indices:
        cell = cells[index]
        source = "".join(cell.get("source", []))
        first_line = next((line.strip() for line in source.splitlines() if line.strip()), "")[:160]
        if cell.get("execution_count") is None:
            unexecuted.append({"cell_index": index, "first_line": first_line})
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                error_outputs.append({
                    "cell_index": index,
                    "ename": output.get("ename"),
                    "evalue": output.get("evalue"),
                })
    joined_code = "\n".join(
        "".join(cells[index].get("source", [])) for index in code_indices
    )
    return {
        "cells": len(cells),
        "code_cells": len(code_indices),
        "executed_code_cells": len(code_indices) - len(unexecuted),
        "unexecuted_code_cells": unexecuted,
        "error_outputs": error_outputs,
        "dangerous_unlock_assignment_present": "UNLOCK_FINAL_TESTS=True" in joined_code,
        "dwd_2024_load_present": "load_dwd(2024)" in joined_code,
        "result_export_code_present": "iteration9_result_block.json" in joined_code,
    }


def main() -> None:
    result = read_json("iteration9_result_block.json")
    integrity = read_json("iteration9_integrity_receipt.json")
    feature_contract = read_json("iteration9_feature_contract.json")

    main_metrics = read_csv("iteration9_multidomain_confirmation.csv")
    stress = read_csv("iteration9_multiseed_stress.csv")
    root_metrics = read_csv("iteration9_root_cause_metrics.csv")
    confidence = read_csv("iteration9_seed_confidence_intervals.csv")
    fault_frontier = read_csv("iteration9_fault_policy_frontier.csv")
    weather_frontier = read_csv("iteration9_weather_policy_frontier.csv")
    feature_ablation = read_csv("iteration9_feature_ablation_contract.csv")
    feature_ablation_duplicate = read_csv("iteration9_feature_ablation_contract (1).csv")
    training_history = read_csv("iteration9_model_training_history.csv")
    family_recall = read_csv("iteration9_fault_episode_recall.csv")
    stress_family = read_csv("iteration9_multiseed_fault_recall.csv")
    root_classes = read_csv("iteration9_root_cause_per_class.csv")
    weather_clusters = read_csv("iteration9_weather_by_cluster.csv")
    stress_weather_clusters = read_csv("iteration9_multiseed_weather_by_cluster.csv")

    reconciliations = {
        "multidomain_confirmation": reconcile_records(
            main_metrics, result["multidomain_confirmation"], ["scope", "domain"]
        ),
        "stress_confirmation": reconcile_records(
            stress.loc[stress.scope.eq("confirmation")],
            result["stress_confirmation"],
            ["seed", "scope", "domain"],
        ),
        "root_cause_metrics": reconcile_records(
            root_metrics, result["root_cause_metrics"], ["domain", "slice"]
        ),
    }

    ci_checks: list[dict[str, Any]] = []
    for _, row in confidence.iterrows():
        metric = str(row.metric)
        subset = stress.loc[
            stress.scope.eq(row.scope) & stress.domain.eq(row.domain), metric
        ]
        actual_mean = float(subset.mean())
        ci_checks.append({
            "scope": row.scope,
            "domain": row.domain,
            "metric": metric,
            "reported_mean": float(row["mean"]),
            "recomputed_mean": actual_mean,
            "mean_matches": bool(np.isclose(actual_mean, float(row["mean"]), atol=1e-12)),
            "ci_order_valid": bool(float(row.ci_lower) <= float(row["mean"]) <= float(row.ci_upper)),
            "reported_seeds": int(row.seeds),
            "actual_seeds": int(subset.notna().sum()),
        })

    selected_fault = result["selected_policy"]
    fault_match = fault_frontier.loc[
        fault_frontier.variant.eq(selected_fault["fault_variant"])
        & fault_frontier.score_col.eq(selected_fault["fault_score_col"])
        & np.isclose(fault_frontier.threshold, selected_fault["fault_threshold"], atol=1e-12)
    ]
    weather_match = weather_frontier.loc[
        weather_frontier.variant.eq(selected_fault["weather_variant"])
        & weather_frontier.score_col.eq(selected_fault["weather_score_col"])
        & np.isclose(weather_frontier.threshold, selected_fault["weather_threshold"], atol=1e-12)
    ]

    confirmation = main_metrics.loc[main_metrics.scope.eq("confirmation")].copy()
    confirmation["derived_iteration9_recall"] = [
        recall_from_precision_f1(float(p), float(f))
        for p, f in zip(confirmation.iteration9_precision, confirmation.iteration9_point_f1)
    ]

    failed_gates = [key for key, value in result["promotion_gates"].items() if not value]
    passed_gates = [key for key, value in result["promotion_gates"].items() if value]
    gate_count_matches = (
        len(passed_gates) == int(result["passed_gates"])
        and len(result["promotion_gates"]) == int(result["total_gates"])
    )

    notebook = inspect_notebook(
        ARCHIVE / "SkyGuard_AI_GPU_Iteration_09_Domain_Invariant_Calibration_Colab.ipynb"
    )
    local_notebook = inspect_notebook(LOCAL_NOTEBOOK)
    executed_nb = json.loads(
        (ARCHIVE / "SkyGuard_AI_GPU_Iteration_09_Domain_Invariant_Calibration_Colab.ipynb")
        .read_text(encoding="utf-8")
    )
    clean_nb = json.loads(LOCAL_NOTEBOOK.read_text(encoding="utf-8"))
    source_match = (
        len(executed_nb.get("cells", [])) == len(clean_nb.get("cells", []))
        and all(
            executed.get("cell_type") == clean.get("cell_type")
            and "".join(executed.get("source", [])) == "".join(clean.get("source", []))
            for executed, clean in zip(executed_nb.get("cells", []), clean_nb.get("cells", []))
        )
    )

    i8_hash = sha256(ITER8_RESULT)
    integrity_checks = {
        "iteration8_hash_matches": i8_hash == integrity["iteration8_result_sha256"],
        "development_years_only": integrity["development_years"] == [2022, 2023],
        "locked_2024_sealed": not any(
            [integrity["dwd_2024_opened"], integrity["noaa_2024_opened"]]
        ),
        "all_2025_sealed": not integrity["any_2025_opened"],
        "no_discovery_confirmation_selection": not integrity[
            "discovery_or_confirmation_used_for_selection"
        ],
        "no_domain_station_identifier": not integrity[
            "domain_or_station_identifier_used_by_model"
        ],
        "three_declared_stress_seeds": integrity["stress_seeds"] == [8023, 9029, 9049],
    }

    table_checks = {
        "feature_ablation_duplicate_identical": feature_ablation.equals(feature_ablation_duplicate),
        "feature_rows": len(feature_ablation),
        "residual_allowed_rows": int(feature_ablation.residual_model_allowed.astype(bool).sum()),
        "excluded_shortcut_rows": int((~feature_ablation.residual_model_allowed.astype(bool)).sum()),
        "feature_contract_counts_match": (
            len(feature_contract["residual_features"]) == feature_contract["residual_feature_count"] == 87
            and len(feature_contract["excluded_shortcuts"]) == 21
        ),
        "training_history_rows": len(training_history),
        "training_target_seed_pairs_complete": set(
            zip(training_history.target, training_history.seed.astype(int))
        ) == {(target, seed) for target in ["fault", "weather"] for seed in [17, 41, 67]},
        "main_family_rows": len(family_recall),
        "stress_family_rows": len(stress_family),
        "root_class_rows": len(root_classes),
        "weather_cluster_rows": len(weather_clusters),
        "stress_weather_cluster_rows": len(stress_weather_clusters),
        "stress_seed_set": sorted(stress.seed.astype(int).unique().tolist()),
    }

    stress_confirmation = stress.loc[stress.scope.eq("confirmation")]
    diagnostic_summary = {
        "confirmation": confirmation[
            [
                "domain", "iteration9_precision", "derived_iteration9_recall",
                "iteration9_point_f1", "iteration9_event_f1", "iteration9_weak_recall",
                "iteration9_false_alarm", "iteration9_weather_f1",
                "iteration9_fault_to_weather",
            ]
        ].to_dict("records"),
        "stress_dwd_all_mean": stress_confirmation.loc[
            stress_confirmation.domain.eq("dwd_all"),
            [
                "iteration9_precision", "iteration9_point_f1", "iteration9_event_f1",
                "iteration9_weak_recall", "iteration9_false_alarm", "iteration9_weather_f1",
                "iteration9_fault_to_weather", "iteration9_drift_episode_recall",
            ],
        ].mean().to_dict(),
        "stress_dwd_holdout_mean": stress_confirmation.loc[
            stress_confirmation.domain.eq("dwd_holdout"),
            [
                "iteration9_precision", "iteration9_point_f1", "iteration9_event_f1",
                "iteration9_weak_recall", "iteration9_false_alarm", "iteration9_weather_f1",
                "iteration9_fault_to_weather", "iteration9_drift_episode_recall",
            ],
        ].mean().to_dict(),
        "detected_root_cause": root_metrics.loc[
            root_metrics.slice.eq("detected_fault_rows")
        ].to_dict("records"),
        "india_confirmation_weather_clusters_with_events": weather_clusters.loc[
            weather_clusters.scope.eq("confirmation")
            & weather_clusters.domain.eq("india")
            & weather_clusters.weather_event_rows.gt(0),
            ["cluster", "weather_event_rows", "precision", "recall", "f1", "fault_to_weather_rate"],
        ].to_dict("records"),
    }

    all_reconciled = all(item["status"] == "PASS" for item in reconciliations.values())
    all_ci_valid = all(
        item["mean_matches"] and item["ci_order_valid"] and item["reported_seeds"] == item["actual_seeds"]
        for item in ci_checks
    )
    notebook_clean = not notebook["error_outputs"] and not notebook["dangerous_unlock_assignment_present"] and not notebook["dwd_2024_load_present"]
    audit_status = "PASS_NON_PROMOTABLE_RESULT" if all_reconciled and all_ci_valid and notebook_clean else "AUDIT_FAILURE"

    audit = {
        "audit_status": audit_status,
        "iteration": result["iteration"],
        "experiment_status": result["status"],
        "promoted": result["promoted"],
        "gate_summary": {
            "passed": len(passed_gates),
            "total": len(result["promotion_gates"]),
            "count_matches_result": gate_count_matches,
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
        },
        "reconciliations": reconciliations,
        "confidence_interval_checks": {
            "status": "PASS" if all_ci_valid else "FAIL",
            "rows": ci_checks,
        },
        "selected_policy_checks": {
            "fault_frontier_row_count": len(fault_match),
            "fault_frontier_row": fault_match.to_dict("records"),
            "weather_frontier_row_count": len(weather_match),
            "weather_frontier_row": weather_match.to_dict("records"),
        },
        "integrity_checks": integrity_checks,
        "table_checks": table_checks,
        "notebook_checks": {
            "executed_notebook": notebook,
            "clean_local_notebook": local_notebook,
            "source_matches_clean_notebook": source_match,
        },
        "diagnostic_summary": diagnostic_summary,
        "decision": result["next_decision"],
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, default=comparable), encoding="utf-8")

    manifest_files = []
    for path in sorted(ARCHIVE.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path == MANIFEST_PATH:
            continue
        manifest_files.append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "iteration": 9,
        "archive_date": "2026-08-30",
        "immutable_checkpoint": True,
        "file_count": len(manifest_files),
        "files": manifest_files,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({
        "audit_status": audit_status,
        "experiment_status": result["status"],
        "promoted": result["promoted"],
        "passed_gates": len(passed_gates),
        "total_gates": len(result["promotion_gates"]),
        "failed_gates": failed_gates,
        "json_csv_reconciliation": "PASS" if all_reconciled else "FAIL",
        "confidence_intervals": "PASS" if all_ci_valid else "FAIL",
        "notebook_error_outputs": len(notebook["error_outputs"]),
        "notebook_unexecuted_code_cells": len(notebook["unexecuted_code_cells"]),
        "notebook_source_matches_clean": source_match,
        "audit_report": str(AUDIT_PATH),
        "manifest": str(MANIFEST_PATH),
    }, indent=2))


if __name__ == "__main__":
    main()

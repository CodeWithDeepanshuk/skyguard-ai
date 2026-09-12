import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import ast
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skyguard.benchmark import InjectionConfig, inject_partition, split_genuine_observations, verify_no_source_overlap
from skyguard.detection.hybrid import add_causal_features, analyze_frame, analyze_row
from skyguard.health import sensor_health


def genuine(stations=5, periods=500):
    rows=[]
    for j in range(stations):
        for i, ts in enumerate(pd.date_range("2025-01-01", periods=periods, freq="h", tz="UTC")):
            rows.append({"station_id":f"S{j}", "timestamp_utc":ts, "source_snapshot_hash":f"hash-{i}",
                         "source_is_genuine":True, "temperature_c":25+3*np.sin(i/24),
                         "pressure_hpa":1000+2*np.cos(i/30), "relative_humidity_pct":60-5*np.sin(i/24),
                         "latitude":20+j*.2, "longitude":75+j*.2})
    return pd.DataFrame(rows)


def test_split_before_injection_has_no_source_overlap():
    parts, contract = split_genuine_observations(genuine())
    assert contract["split_before_injection"]
    assert verify_no_source_overlap(parts)
    assert not set(parts["train"].station_id) & set(parts["unseen_station_test"].station_id)


def test_overlap_guard_fails():
    part = pd.DataFrame({"source_row_id":["same"]})
    with pytest.raises(ValueError, match="leakage"):
        verify_no_source_overlap({"a":part, "b":part.copy()})


def test_injection_is_deterministic_and_raw_input_immutable():
    parts, _ = split_genuine_observations(genuine())
    raw = parts["train"].copy(deep=True)
    cfg = InjectionConfig(events_per_type=1, seed=13)
    a, ae, _ = inject_partition(parts["train"], "train", cfg)
    b, be, _ = inject_partition(parts["train"], "train", cfg)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(ae, be)
    pd.testing.assert_frame_equal(parts["train"], raw)
    assert set(ae.fault_type) == set(a.loc[a.injection_applied,"fault_type"])
    assert a.loc[a.injection_applied,"source_snapshot_hash"].notna().all()


def test_partitions_use_independent_seeds():
    parts, _ = split_genuine_observations(genuine())
    _, train_events, _ = inject_partition(parts["train"], "train", InjectionConfig(1, 11))
    _, test_events, _ = inject_partition(parts["future_test"], "future_test", InjectionConfig(1, 29))
    assert set(train_events.injection_seed) == {11}
    assert set(test_events.injection_seed) == {29}
    assert not set(train_events.episode_id) & set(test_events.episode_id)


def test_causal_features_are_prefix_invariant():
    frame = genuine(stations=1, periods=100)
    full = add_causal_features(frame)
    prefix = add_causal_features(frame.iloc[:70])
    pd.testing.assert_frame_equal(full.iloc[:70], prefix, check_dtype=False)


def test_spike_and_physical_corruption_detected():
    row={"temperature_c":9999, "pressure_hpa":1000, "relative_humidity_pct":50,
         "temperature_robust_z":20, "spatial_context_available":False}
    result=analyze_row(row)
    assert result["is_anomaly"] and result["severity"] in {"HIGH","CRITICAL"}
    assert "temperature" in result["affected_parameters"]


def test_frozen_requires_history_variability_not_repeat_alone():
    base={"temperature_c":25,"pressure_hpa":1000,"relative_humidity_pct":50,
          "temperature_frozen_run":20,"spatial_context_available":False}
    calm=analyze_row({**base,"temperature_past_variability":0.01})
    variable=analyze_row({**base,"temperature_past_variability":2})
    assert "TEMPERATURE_FROZEN_WITH_EXPECTED_VARIABILITY" not in calm["reason_codes"]
    assert "TEMPERATURE_FROZEN_WITH_EXPECTED_VARIABILITY" in variable["reason_codes"]


def test_event_consistency_gate_reduces_fault_probability():
    row={"temperature_c":30,"pressure_hpa":1000,"relative_humidity_pct":70,
         "temperature_robust_z":6,"spatial_context_available":True,"spatial_coherence_score":.9}
    coherent=analyze_row(row)
    isolated=analyze_row({**row,"spatial_coherence_score":.1,"spatial_disagreement_score":.9})
    assert coherent["possible_genuine_meteorological_event"]
    assert coherent["anomaly_probability"] < isolated["anomaly_probability"]


def test_health_score_transparent_and_no_rul_claim():
    assert sensor_health(history_rows=2)["state"] == "INSUFFICIENT_HISTORY"
    result=sensor_health(history_rows=100, drift_score=.8, missingness_rate=.2)
    assert 0 <= result["health_score"] <= 100
    assert result["remaining_useful_life"] is None


def test_iteration13_notebook_clean_and_delivery_matches():
    name="SkyGuard_AI_Iteration_13_SIH26073_Benchmark.ipynb"
    notebook_path=ROOT/"notebooks"/name
    assert notebook_path.read_bytes() == (ROOT/"deliverables"/name).read_bytes()
    notebook=json.loads(notebook_path.read_text(encoding="utf-8"))
    assert len(notebook["cells"]) >= 25
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))
            assert cell["execution_count"] is None and cell["outputs"] == []


def test_iteration13_runner_blocks_insufficient_history(tmp_path):
    sys.path.insert(0, str(ROOT/"tools"))
    from run_iteration13_benchmark import run
    data=genuine(stations=5,periods=48)
    data["source"]="IMD_AUTHORIZED_AWS_API"
    data["generated_or_simulated"]=False
    data["eligible_for_unlabelled_baseline"]=True
    data["primary_complete"]=True
    data["source_timezone_contract"]="UTC"
    path=tmp_path/"genuine.parquet"; data.to_parquet(path,index=False)
    out=tmp_path/"reports"
    assert run(path,out,timezone_confirmed=False) == 2
    assert (out/"BLOCKED.txt").read_text() == "NOT ENOUGH GENUINE TEMPORAL DATA FOR THIS EXPERIMENT"

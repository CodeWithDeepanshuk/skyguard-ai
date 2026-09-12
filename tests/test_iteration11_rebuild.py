"""Regression tests for the new-data Iteration 11, not the old catalogue-only notebook."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from iteration11_data import choose_pressure, neighbor_graph, normalize, parse_group, write_json
from iteration11_training import FEATURES, inject, spatial, split_roles, temporal


def frame(n=200, start="2021-01-01", sid="11111199999"):
    t = np.arange(n)
    return pd.DataFrame({"timestamp_utc": pd.date_range(start, periods=n, freq="h", tz="UTC"),
                         "temperature_c": 24+np.sin(t/4), "pressure_hpa": 990+np.sin(t/20),
                         "relative_humidity_pct": 60+np.cos(t/5), "station_id": sid,
                         "qc_screened_proxy": True, "geographic_block": "12:40"})


def test_parse_ma1_station_pressure_and_missing():
    s = pd.Series(["99999,9,09133,1", "10100,1,09900,1", "", None])
    alt, _ = parse_group(s)
    station, qc = parse_group(s, 2)
    assert np.isnan(alt.iloc[0])
    assert station.iloc[0] == 913.3 and qc.iloc[0] == "1"


def test_no_rowwise_pressure_datum_switch_and_no_future_selection():
    f = frame(10)
    for p in ["station_pressure", "sea_level_pressure", "altimeter_pressure"]:
        f[p] = np.nan
        f[p+"_qc"] = "1"
    f.loc[:7, "station_pressure"] = 910
    f.loc[8:, "sea_level_pressure"] = 1050
    f["source_qc_temperature_ok"] = True
    f["source_qc_humidity_ok"] = True
    selected, _ = choose_pressure(f)
    assert selected.pressure_datum.nunique() == 1
    assert selected.pressure_hpa.iloc[8:].isna().all()
    future = f.copy()
    future.timestamp_utc = future.timestamp_utc + pd.DateOffset(years=2)
    future.sea_level_pressure = 1010
    joined, _ = choose_pressure(pd.concat([f, future]))
    assert joined.pressure_datum.eq("station_pressure").all()


def test_temporal_prefix_invariance():
    f = frame()
    original = temporal(f)
    f.loc[150:, "temperature_c"] = 9999
    updated = temporal(f)
    pd.testing.assert_frame_equal(original.iloc[:150], updated.iloc[:150])
    pd.testing.assert_frame_equal(original.iloc[:80], temporal(frame(80)))


def test_future_and_stale_neighbors_not_available():
    own = frame(40)
    future = frame(40, start="2022-01-01")
    old = frame(40, start="2020-01-01")
    out = spatial(own, temporal(own), [(future, temporal(future), True), (old, temporal(old), True)])
    assert out.temperature_buddy_count.eq(0).all()
    assert out.temperature_buddy_residual.isna().all()


def test_buddies_need_two_and_pressure_compatibility():
    own = frame(80)
    b = frame(80, sid="22222299999")
    one = spatial(own, temporal(own), [(b, temporal(b), True)])
    assert one.temperature_buddy_residual.isna().all()
    two = spatial(own, temporal(own), [(b, temporal(b), False), (b, temporal(b), False)])
    assert two.pressure_buddy_count.eq(0).all()
    assert two.temperature_buddy_residual.iloc[10:].notna().all()


def test_graph_distance_elevation_and_alias_filter():
    rows = pd.DataFrame({"station_id": ["a", "b", "c", "d", "e"], "latitude": [25,25.1,28,25.2,25],
                         "longitude": [80]*5, "elevation_m": [100,120,100,2000,100],
                         "pressure_datum": ["station_pressure"]*5, "station_role": ["development"]*5})
    g = neighbor_graph(rows)
    assert set(g.loc[g.station_id.eq("a"), "neighbor_id"]) == {"b"}


def test_split_disjoint_and_spatial_holdout_not_training():
    t = pd.Series(pd.to_datetime(["2021-01-01", "2022-03-01", "2022-07-01", "2022-11-01", "2023-06-01"], utc=True))
    assert split_roles(t, "development").tolist() == ["train", "early_stop", "calibration", "policy", "temporal_confirmation"]
    assert split_roles(t, "spatial_holdout").tolist() == ["unused"]*4 + ["spatial_confirmation"]


def test_inject_reproducible_no_label_feature_leak():
    f = frame(1500)
    a, b = inject(f), inject(f)
    pd.testing.assert_frame_equal(a, b)
    assert a.y.eq(1).any()
    assert not set(FEATURES) & {"y", "episode_id", "fault_type", "qc_screened_proxy", "dew_point_c", "station_id", "ground_truth_fault"}
    f.qc_screened_proxy = False
    assert inject(f).y.eq(-1).all()


def test_normalizer_preserves_source_quality_and_unclipped_rh():
    r = pd.DataFrame({"STATION":["12345699999"], "DATE":["2021-01-01T00:00:00"],
                      "TMP":["+0200,1"], "DEW":["+0220,1"], "SLP":["99999,9"], "MA1":["99999,9,09100,1"]})
    meta = dict(station_id="12345699999", latitude=20, longitude=75, elevation_m=800,
                station_role="development", geographic_block="10:37", legacy_24_station=False)
    out = normalize(r, meta)
    assert out.relative_humidity_pct.iloc[0] > 100
    assert out.station_pressure.iloc[0] == 910


def test_missing_metadata_is_json_null_not_zero(tmp_path):
    import json
    path = tmp_path/'metadata.json'
    write_json(path, {'elevation_m':np.nan,'count':np.int64(2)})
    assert json.loads(path.read_text()) == {'elevation_m':None,'count':2}


def test_standalone_notebook_embeds_current_source():
    import ast
    import hashlib
    import json
    root = Path(__file__).resolve().parents[1]
    name = 'SkyGuard_AI_Iteration_11_Data_Rebuild_Colab.ipynb'
    notebook = json.loads((root/'notebooks'/name).read_text(encoding='utf-8'))
    assert (root/'notebooks'/name).read_bytes() == (root/'deliverables'/name).read_bytes()
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            ast.parse(''.join(cell['source']))
            assert cell['execution_count'] is None and not cell['outputs']
    embedded = next(''.join(c['source']) for c in notebook['cells'] if ''.join(c['source']).startswith('MODULE_SOURCES ='))
    tree = ast.parse(embedded)
    modules = ast.literal_eval(tree.body[0].value)
    hashes = ast.literal_eval(tree.body[1].value)
    for name, source in modules.items():
        assert source == (root/'tools'/f'{name}.py').read_text(encoding='utf-8')
        assert hashlib.sha256(source.encode()).hexdigest() == hashes[name]

import ast
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from iteration12_imd_aws import MODEL_INPUTS, archive_snapshot, normalize_aws, readiness


SAMPLE = [{"ID":"B48970CA", "CALL_SIGN":"NDL", "DISTRICT":"NEW_DELHI", "STATE":"DELHI",
           "STATION":"LODI ROAD", "DATE":"2026-09-12", "TIME":"07:00:00",
           "CURR_TEMP":"40.8", "RH":"20", "MSLP":"1003.0", "Latitude":"28.5885", "Longitude":"77.2224"}]


def test_official_schema_normalizes_only_three_model_inputs():
    out = normalize_aws(SAMPLE)
    assert out.loc[0, MODEL_INPUTS].tolist() == [40.8, 1003.0, 20.0]
    assert out.source.eq("IMD_AUTHORIZED_AWS_API").all()
    assert not out.generated_or_simulated.any()
    assert out.ground_truth_fault.eq(-1).all()


def test_missing_required_field_fails_closed():
    broken = [dict(SAMPLE[0])]
    broken[0].pop("RH")
    with pytest.raises(ValueError, match="missing required"):
        normalize_aws(broken)


def test_snapshot_is_immutable_and_secrets_not_recorded(tmp_path):
    receipt = {"retrieved_at_utc":"2026-09-12T07:01:00+00:00", "url":"official", "payload_sha256":"x"}
    frame, record = archive_snapshot(tmp_path, SAMPLE, receipt)
    assert len(frame) == 1 and record["credentials_recorded"] is False
    assert not any("token" in key.lower() or "key" in key.lower() for key in record)
    saved = json.loads(next(tmp_path.glob("raw/**/*.receipt.json")).read_text())
    assert saved["generated_rows"] == 0


def test_readiness_does_not_claim_one_snapshot_is_training_ready():
    out = normalize_aws(SAMPLE)
    stations, report = readiness(out)
    assert len(stations) == 1
    assert not report["ready_for_pilot_training"]
    assert not report["ready_for_seasonal_claims"]
    assert report["verified_real_fault_labels"] is False


def test_iteration12_notebook_is_clean_and_embeds_module():
    name = "SkyGuard_AI_Iteration_12_Genuine_IMD_AWS_Data_Colab.ipynb"
    nb_path = ROOT / "notebooks" / name
    delivery = ROOT / "deliverables" / name
    assert nb_path.read_bytes() == delivery.read_bytes()
    notebook = json.loads(nb_path.read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))
            assert cell["execution_count"] is None and cell["outputs"] == []
    embedded = next("".join(c["source"]) for c in notebook["cells"] if "MODULE_SOURCE =" in "".join(c["source"]))
    tree = ast.parse(embedded)
    embedded_source = ast.literal_eval(tree.body[0].value)
    assert embedded_source == (ROOT / "tools" / "iteration12_imd_aws.py").read_text(encoding="utf-8")

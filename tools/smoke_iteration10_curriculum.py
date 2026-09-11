"""Execute Iteration 10's real-data load and both curriculum lanes without training models."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import zipfile

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb"
STARTER_ZIP = ROOT / "deliverables" / "SkyGuard_Iteration10_Final_Starter_Bundle.zip"
DWD_ZIP = ROOT / "deliverables" / "SkyGuard_Iteration8_Development_Data_Bundle.zip"


def cell_source(notebook: dict[str, object], marker: str) -> str:
    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))
        if cell.get("cell_type") == "code" and marker in source:
            return source
    raise KeyError(marker)


def main() -> None:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="skyguard_i10_smoke_") as temporary:
        target = Path(temporary)
        with zipfile.ZipFile(STARTER_ZIP) as archive:
            archive.extractall(target)
        with zipfile.ZipFile(DWD_ZIP) as archive:
            archive.extractall(target)
        starter = target / "SkyGuard_Iteration10_Final_Starter_Bundle"
        dwd = target / "SkyGuard_Iteration8_Development_Data_Bundle"
        sys.path.insert(0, str(starter / "src"))
        namespace = {
            "__name__": "iteration10_smoke",
            "STARTER": starter,
            "DWD_BUNDLE": dwd,
            "json": json,
            "np": np,
            "pd": pd,
            "GLOBAL_SEED": 26073,
            "MAIN_SEED": 10023,
            "ITER10_ROOT": target,
            "display": lambda *_args, **_kwargs: None,
        }
        for marker in (
            "from skyguard.faults.curriculum import",
            "SCOPE_RANGES={",
        ):
            source = cell_source(notebook, marker)
            exec(compile(source, f"iteration10_{marker[:12]}.py", "exec"), namespace)

        train_events = namespace["train_events"]
        main_events = namespace["main_events"]
        operational = set(namespace["OPERATIONAL_FAULT_FAMILIES"])
        weather = set(namespace["WEATHER_FAMILIES"])
        observed = set(main_events["anomaly_type"])
        assert operational <= observed
        assert weather <= observed
        assert main_events["episode_id"].is_unique
        assert set(main_events["scope"]) == {"calibration", "policy", "discovery", "confirmation"}
        print(json.dumps({
            "status": "PASS",
            "india_rows": len(namespace["india"]),
            "dwd_hourly_rows": len(namespace["dwd"]),
            "training_events": len(train_events),
            "validation_events": len(main_events),
            "operational_fault_families": len(operational),
            "weather_families": len(weather),
        }, indent=2))


if __name__ == "__main__":
    main()

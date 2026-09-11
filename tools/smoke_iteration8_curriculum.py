"""Run the Iteration 8 curriculum against the downloaded DWD development years."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from skyguard.faults.curriculum import MultiClimateCurriculum


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "iteration8" / "processed"


def load_hourly(year: int) -> pd.DataFrame:
    frame = pd.read_csv(PROCESSED / f"dwd_aws_10min_{year}.csv.gz", low_memory=False)
    timestamp = pd.to_datetime(frame["timestamp_utc"], utc=True)
    frame = frame.loc[timestamp.dt.minute.eq(0)].copy().reset_index(drop=True)
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True).dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    frame["dew_point_c"] = ""
    return frame


def main() -> None:
    train = MultiClimateCurriculum(load_hourly(2022), "dwd_train", seed=8017)
    train.build_training(
        "2022-01-08", "2022-12-22", weather_repetitions=4, fault_repetitions=8
    )
    validation = MultiClimateCurriculum(load_hourly(2023), "dwd_validation", seed=8023)
    validation.build_validation({
        "tune": ("2023-01-08", "2023-04-24"),
        "discovery": ("2023-05-05", "2023-08-25"),
        "confirmation": ("2023-09-05", "2023-12-22"),
    })

    train_audit = train.validate()
    validation_audit = validation.validate()
    coverage = validation.event_frame().groupby(
        ["scope", "cluster", "label_category", "anomaly_type"]
    ).size()
    assert train_audit["status"] == "PASS"
    assert validation_audit["status"] == "PASS"
    assert train_audit["weather_events"] == 96 and train_audit["fault_events"] == 160
    assert validation_audit["weather_events"] == 72 and validation_audit["fault_events"] == 60
    assert int(coverage.min()) >= 1
    print(json.dumps({
        "status": "PASS",
        "train": train_audit,
        "validation": validation_audit,
        "minimum_events_per_required_validation_cell": int(coverage.min()),
        "required_validation_cells": int(len(coverage)),
    }, indent=2))


if __name__ == "__main__":
    main()

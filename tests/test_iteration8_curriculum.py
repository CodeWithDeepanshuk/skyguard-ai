from __future__ import annotations

import numpy as np
import pandas as pd

from skyguard.faults.curriculum import FAULT_FAMILIES, WEATHER_FAMILIES, MultiClimateCurriculum


def sample_frame() -> pd.DataFrame:
    timestamps = pd.date_range("2023-01-01", "2023-04-30 23:00", freq="1h", tz="UTC")
    rows = []
    for station_offset, station in enumerate(("A", "B", "C", "D")):
        for step, timestamp in enumerate(timestamps):
            rows.append({
                "station_id": station,
                "timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
                "cluster": "test_cluster",
                "evaluation_role": "development_validation",
                "temperature_c": 15.0 + 5.0 * np.sin(step / 24.0) + station_offset * 0.1,
                "pressure_hpa": 1010.0 + np.sin(step / 72.0),
                "relative_humidity_pct": 60.0 - 10.0 * np.sin(step / 24.0),
                "dew_point_c": "",
            })
    return pd.DataFrame(rows)


def test_balanced_validation_curriculum_is_reproducible_and_non_overlapping() -> None:
    scopes = {
        "tune": ("2023-01-01", "2023-02-09"),
        "discovery": ("2023-02-10", "2023-03-20"),
        "confirmation": ("2023-03-21", "2023-04-30"),
    }
    first = MultiClimateCurriculum(sample_frame(), "validation", seed=81)
    first.build_validation(scopes)
    second = MultiClimateCurriculum(sample_frame(), "validation", seed=81)
    second.build_validation(scopes)

    assert first.validate()["status"] == "PASS"
    assert first.event_frame().equals(second.event_frame())
    weather_events = first.event_frame().query("label_category == 'genuine_weather_scenario'")
    fault_events = first.event_frame().query("label_category == 'sensor_fault'")
    assert set(weather_events["anomaly_type"]) == set(WEATHER_FAMILIES)
    assert set(fault_events["anomaly_type"]) == set(FAULT_FAMILIES)
    assert first.event_frame().query("label_category == 'genuine_weather_scenario'")["stations"].str.count(",").ge(2).all()
    assert first.frame.loc[first.frame["is_weather_event"].eq(1), "is_anomaly"].eq(0).all()
    assert first.frame.loc[first.frame["is_anomaly"].eq(1), "is_weather_event"].eq(0).all()


def test_mixed_three_hour_cadence_can_generate_regional_weather() -> None:
    sparse = sample_frame().loc[
        pd.to_datetime(sample_frame()["timestamp_utc"], utc=True).dt.hour.mod(3).eq(0)
    ].reset_index(drop=True)
    curriculum = MultiClimateCurriculum(sparse, "sparse_validation", seed=26073)
    curriculum.build_validation({"confirmation": ("2023-01-05", "2023-04-25")})
    report = curriculum.validate()
    assert report["status"] == "PASS"
    assert report["weather_events"] == len(WEATHER_FAMILIES)
    assert curriculum.event_frame().query(
        "label_category == 'genuine_weather_scenario'"
    )["stations"].str.count(",").ge(2).all()

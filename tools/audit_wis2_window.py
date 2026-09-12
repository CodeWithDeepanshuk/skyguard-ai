"""Audit a collected WIS2 window without claiming anomaly-model performance."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ROOT / "data" / "observations" / "imd_wis2" / "latest_national.csv.gz"
    frame = pd.read_csv(source, dtype={"station_id": str})
    frame["timestamp_utc"] = pd.to_datetime(frame.timestamp_utc, utc=True, errors="coerce")
    for column in ("temperature_c", "pressure_hpa", "relative_humidity_pct"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    keys = ["station_id", "timestamp_utc"]
    counts = frame.groupby("station_id").size()
    gaps = (frame.sort_values(keys).groupby("station_id").timestamp_utc.diff().dt.total_seconds()/60).dropna()
    valid = {
        "temperature": frame.temperature_c.between(-90, 65) | frame.temperature_c.isna(),
        "pressure": frame.pressure_hpa.between(300, 1100) | frame.pressure_hpa.isna(),
        "humidity": frame.relative_humidity_pct.between(0, 100) | frame.relative_humidity_pct.isna(),
    }
    report = {
        "source_type": "OBSERVED", "provider": "IMD_WIS2", "rows": int(len(frame)),
        "reporting_stations": int(frame.station_id.nunique()), "verified_metadata_stations": 432,
        "reporting_vs_metadata_pct": round(100*frame.station_id.nunique()/432, 2),
        "reporting_vs_stated_1008_target_pct": round(100*frame.station_id.nunique()/1008, 2),
        "first_timestamp_utc": frame.timestamp_utc.min().isoformat(),
        "last_timestamp_utc": frame.timestamp_utc.max().isoformat(),
        "duplicate_station_timestamp_rows": int(frame.duplicated(keys).sum()),
        "non_null": {c: int(frame[c].notna().sum()) for c in ("temperature_c", "pressure_hpa", "relative_humidity_pct")},
        "complete_three_parameter_rows": int(frame[["temperature_c","pressure_hpa","relative_humidity_pct"]].notna().all(axis=1).sum()),
        "rh_source": frame.rh_source.fillna("MISSING").value_counts().to_dict(),
        "reports_per_station": {"min": int(counts.min()), "median": float(counts.median()), "max": int(counts.max())},
        "gap_minutes": {"median": round(float(gaps.median()),2), "p90": round(float(gaps.quantile(.9)),2), "max": round(float(gaps.max()),2)} if len(gaps) else None,
        "physical_range_failures": {name: int((~mask).sum()) for name, mask in valid.items()},
        "reference_rows": int(frame.source_type.ne("OBSERVED").sum()),
        "model_accuracy_measured": False,
    }
    json_path = ROOT / "reports" / "WIS2_NATIONAL_WINDOW_AUDIT.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = f"""# IMD WIS2 National 24-Hour Window Audit

- Direct reports: **{report['rows']:,}**
- Reporting stations: **{report['reporting_stations']}/432 metadata stations ({report['reporting_vs_metadata_pct']}%)**
- Coverage against stated 1008 target: **{report['reporting_vs_stated_1008_target_pct']}%**
- Complete T/P/RH reports: **{report['complete_three_parameter_rows']:,}**
- Non-null T/P/RH: **{report['non_null']['temperature_c']:,} / {report['non_null']['pressure_hpa']:,} / {report['non_null']['relative_humidity_pct']:,}**
- Duplicate station-timestamps: **{report['duplicate_station_timestamp_rows']}**
- Reports/station min/median/max: **{report['reports_per_station']['min']} / {report['reports_per_station']['median']} / {report['reports_per_station']['max']}**
- Median/P90 cadence gap: **{report['gap_minutes']['median']} / {report['gap_minutes']['p90']} minutes**
- Reference/model rows mixed into output: **{report['reference_rows']}**

This is an ingestion/coverage audit, not an anomaly-accuracy benchmark. Sparse and irregular station cadence must be respected by temporal and graph models.
"""
    (ROOT / "reports" / "WIS2_NATIONAL_WINDOW_AUDIT.md").write_text(md, encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

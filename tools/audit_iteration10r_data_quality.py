"""Compare the exact India and DWD development corpora used by Iteration 10.

The audit is descriptive only.  It never changes source observations and it
does not open the locked 2024/2025 evaluation years.  DWD is sampled at exact
hour boundaries because that is the table consumed by the final notebook.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT_CSV = ROOT / "reports" / "iteration10r_india_dwd_station_quality.csv"
REPORT_JSON = ROOT / "reports" / "iteration10r_india_dwd_data_quality.json"
REPORT_MD = ROOT / "reports" / "ITERATION_10R_INDIA_DWD_DATA_FEASIBILITY.md"
PRIMARY = ["temperature_c", "pressure_hpa", "relative_humidity_pct"]


def load_india() -> tuple[pd.DataFrame, int]:
    path = ROOT / "data" / "iteration10" / "processed" / "india_aws_2022_2023.csv.gz"
    frame = pd.read_csv(path, dtype={"station_id": str}, low_memory=False)
    return frame, len(frame)


def load_dwd() -> tuple[pd.DataFrame, int]:
    parts: list[pd.DataFrame] = []
    raw_rows = 0
    for year in (2022, 2023):
        path = ROOT / "data" / "iteration8" / "processed" / f"dwd_aws_10min_{year}.csv.gz"
        frame = pd.read_csv(path, dtype={"station_id": str}, low_memory=False)
        raw_rows += len(frame)
        timestamp = pd.to_datetime(frame["timestamp_utc"], utc=True)
        parts.append(frame.loc[timestamp.dt.minute.eq(0)].copy())
    return pd.concat(parts, ignore_index=True), raw_rows


def prepare(frame: pd.DataFrame, domain: str) -> pd.DataFrame:
    result = frame.copy()
    result["station_id"] = result["station_id"].astype(str)
    result["timestamp"] = pd.to_datetime(result["timestamp_utc"], utc=True)
    result["year"] = result["timestamp"].dt.year.astype(int)
    result["domain"] = domain
    result = result.loc[result["year"].isin([2022, 2023])].copy()
    result = result.sort_values(["station_id", "timestamp"], kind="stable").reset_index(drop=True)
    return result


def station_year_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    exact_counts = frame.groupby(["cluster", "timestamp"], sort=False)["station_id"].transform("nunique")
    work = frame.assign(exact_neighbours=(exact_counts - 1).clip(lower=0))
    rows: list[dict[str, object]] = []
    for (domain, station, year), group in work.groupby(["domain", "station_id", "year"], sort=False):
        group = group.sort_values("timestamp", kind="stable")
        delta = group["timestamp"].diff().dt.total_seconds().div(60)
        plausible = delta[(delta > 0) & (delta <= 360)].round()
        cadence = float(plausible.mode().iloc[0]) if len(plausible) else np.nan
        ratio = delta[delta > 0].div(cadence) if np.isfinite(cadence) and cadence > 0 else pd.Series(dtype=float)
        days = 366 if int(year) == 2024 else (365 if int(year) != 2020 else 366)
        expected = days * 1440.0 / cadence if np.isfinite(cadence) and cadence > 0 else np.nan
        complete = group[PRIMARY].notna().all(axis=1)
        rows.append({
            "domain": str(domain),
            "station_id": str(station),
            "year": int(year),
            "cluster": str(group["cluster"].iloc[0]),
            "evaluation_role": str(group["evaluation_role"].iloc[0]),
            "rows": int(len(group)),
            "complete_primary_fraction": float(complete.mean()),
            "mode_cadence_minutes": cadence,
            "regular_cadence_fraction": float(ratio.between(0.75, 1.25).mean()) if len(ratio) else 0.0,
            "full_year_slot_coverage": float(min(1.0, len(group) / expected)) if np.isfinite(expected) else 0.0,
            "gap_ratio_q95": float(ratio.quantile(0.95)) if len(ratio) else np.nan,
            "gap_ratio_q99": float(ratio.quantile(0.99)) if len(ratio) else np.nan,
            "gap_ratio_q999": float(ratio.quantile(0.999)) if len(ratio) else np.nan,
            "long_gap_fraction_gt_4x": float(ratio.gt(4.0).mean()) if len(ratio) else 0.0,
            "max_gap_hours": float(delta.max() / 60.0) if len(delta.dropna()) else 0.0,
            "exact_time_neighbour_ge_1_fraction": float(group["exact_neighbours"].ge(1).mean()),
            "exact_time_neighbour_ge_2_fraction": float(group["exact_neighbours"].ge(2).mean()),
            "active_months": int(group["timestamp"].dt.to_period("M").nunique()),
            "duplicate_station_timestamps": int(group.duplicated(["station_id", "timestamp"]).sum()),
        })
    return pd.DataFrame(rows).sort_values(["domain", "station_id", "year"], kind="stable")


def domain_summary(
    frame: pd.DataFrame,
    station_metrics: pd.DataFrame,
    source_rows: int,
) -> dict[str, object]:
    domain = str(frame["domain"].iloc[0])
    station_rows = frame.groupby("station_id", sort=False).size().astype(float)
    cadence_counts = station_metrics.groupby("station_id")["mode_cadence_minutes"].median().round().value_counts().sort_index()
    pressure_sources = frame["pressure_source"].fillna("missing").astype(str).value_counts(normalize=True)
    return {
        "domain": domain,
        "source_rows_2022_2023": int(source_rows),
        "model_rows_2022_2023": int(len(frame)),
        "stations": int(frame["station_id"].nunique()),
        "clusters": int(frame["cluster"].nunique()),
        "rows_per_station_mean": float(station_rows.mean()),
        "rows_per_station_min": int(station_rows.min()),
        "rows_per_station_max": int(station_rows.max()),
        "rows_per_station_cv": float(station_rows.std(ddof=0) / max(station_rows.mean(), 1.0)),
        "median_mode_cadence_minutes": float(station_metrics["mode_cadence_minutes"].median()),
        "station_cadence_counts": {str(int(key)): int(value) for key, value in cadence_counts.items()},
        "median_regular_cadence_fraction": float(station_metrics["regular_cadence_fraction"].median()),
        "minimum_regular_cadence_fraction": float(station_metrics["regular_cadence_fraction"].min()),
        "median_full_year_slot_coverage": float(station_metrics["full_year_slot_coverage"].median()),
        "minimum_full_year_slot_coverage": float(station_metrics["full_year_slot_coverage"].min()),
        "median_gap_ratio_q999": float(station_metrics["gap_ratio_q999"].median()),
        "maximum_gap_ratio_q999": float(station_metrics["gap_ratio_q999"].max()),
        "median_long_gap_fraction_gt_4x": float(station_metrics["long_gap_fraction_gt_4x"].median()),
        "exact_time_neighbour_ge_2_fraction": float(
            frame.assign(
                count=frame.groupby(["cluster", "timestamp"], sort=False)["station_id"].transform("nunique")
            )["count"].ge(3).mean()
        ),
        "complete_primary_fraction": float(frame[PRIMARY].notna().all(axis=1).mean()),
        "duplicate_station_timestamps": int(frame.duplicated(["station_id", "timestamp"]).sum()),
        "pressure_source_fraction": {str(key): float(value) for key, value in pressure_sources.items()},
    }


def percentage(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def build_markdown(summary: dict[str, dict[str, object]]) -> str:
    india = summary["india"]
    dwd = summary["dwd"]
    return f"""# Iteration 10R India-vs-DWD data feasibility audit

## Scope

This report uses genuine 2022–2023 observations only. DWD is sampled at exact hourly timestamps to match the GPU notebook. No 2024/2025 observation was opened.

## Direct comparison

| Property | India NOAA/ISD corpus | DWD CDC corpus used by model |
|---|---:|---:|
| Model rows | {india['model_rows_2022_2023']:,} | {dwd['model_rows_2022_2023']:,} |
| Original source rows | {india['source_rows_2022_2023']:,} | {dwd['source_rows_2022_2023']:,} |
| Stations / clusters | {india['stations']} / {india['clusters']} | {dwd['stations']} / {dwd['clusters']} |
| Rows/station range | {india['rows_per_station_min']:,}–{india['rows_per_station_max']:,} | {dwd['rows_per_station_min']:,}–{dwd['rows_per_station_max']:,} |
| Rows/station coefficient of variation | {india['rows_per_station_cv']:.3f} | {dwd['rows_per_station_cv']:.3f} |
| Median cadence regularity | {percentage(india['median_regular_cadence_fraction'])} | {percentage(dwd['median_regular_cadence_fraction'])} |
| Worst station-year cadence regularity | {percentage(india['minimum_regular_cadence_fraction'])} | {percentage(dwd['minimum_regular_cadence_fraction'])} |
| Median full-year slot coverage | {percentage(india['median_full_year_slot_coverage'])} | {percentage(dwd['median_full_year_slot_coverage'])} |
| Worst station-year slot coverage | {percentage(india['minimum_full_year_slot_coverage'])} | {percentage(dwd['minimum_full_year_slot_coverage'])} |
| Exact-time rows with at least two neighbours | {percentage(india['exact_time_neighbour_ge_2_fraction'])} | {percentage(dwd['exact_time_neighbour_ge_2_fraction'])} |
| Median 99.9th-percentile gap/cadence ratio | {india['median_gap_ratio_q999']:.2f}x | {dwd['median_gap_ratio_q999']:.2f}x |
| Complete T/P/RH rows | {percentage(india['complete_primary_fraction'])} | {percentage(dwd['complete_primary_fraction'])} |

## Why DWD transfers more cleanly

1. DWD originates as synchronized 10-minute station observations and remains nearly uniform after hourly sampling.
2. India is a mixed archive: station cadences differ, reporting schedules change, and station row counts are highly unequal.
3. DWD clusters provide more simultaneous neighbour evidence. India often needs tolerance-based neighbour matching, increasing uncertainty and latency.
4. DWD pressure is normalized through one documented pipeline. India uses genuine station-pressure/sea-level-pressure fallbacks, so absolute or instantaneous cross-station pressure is unsafe.
5. Uniform DWD cadence makes frozen, dropout, slope and CUSUM episode lengths consistent. The same point-count rule represents different elapsed times in India.

## What can and cannot be claimed

- Injected-fault performance can be measured because the injected event boundaries and original values are known.
- Real-world India accuracy cannot be claimed from this archive alone because it has no confirmed sensor-maintenance fault labels.
- On genuine unlabelled India rows, the defensible operational measurements are false-alert rate, stability, neighbour consistency and expert-reviewed incident yield.
- Any accuracy range proposed for India is therefore a development target, not a measured real-world accuracy guarantee.
"""


def main() -> None:
    india_raw, india_source_rows = load_india()
    dwd_raw, dwd_source_rows = load_dwd()
    india = prepare(india_raw, "india")
    dwd = prepare(dwd_raw, "dwd")
    assert set(india["year"].unique()) == {2022, 2023}
    assert set(dwd["year"].unique()) == {2022, 2023}

    station = pd.concat([station_year_metrics(india), station_year_metrics(dwd)], ignore_index=True)
    summaries = {
        "india": domain_summary(india, station.loc[station["domain"].eq("india")], india_source_rows),
        "dwd": domain_summary(dwd, station.loc[station["domain"].eq("dwd")], dwd_source_rows),
    }
    payload = {
        "status": "PASS",
        "development_years": [2022, 2023],
        "locked_observation_years_opened": [],
        "domains": summaries,
    }
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    station.to_csv(REPORT_CSV, index=False)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(build_markdown(summaries), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Iteration 11: auditable all-India historical station discovery and preparation.

Independent experiment: never reads labelled 2024/2025 tests or writes old models.
NOAA ISD observations are a public Indian-station PROXY, not an IMD AWS export.
Only the explicit 2020--2023 historical ISD CSV schema is supported here. GHCNh
requires a separate parser; an HTML/error/new-format response fails validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

VERSION = "iteration11-v1"
YEARS = (2020, 2021, 2022, 2023)
BASE = "https://www.ncei.noaa.gov/data/global-hourly/access"
HISTORY_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
INVENTORY_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-inventory.csv"
PRIMARY = ["temperature_c", "pressure_hpa", "relative_humidity_pct"]
GOOD_QC = {"0", "1", "4", "5"}  # usable QC-screened proxy, not verified healthy
PRESSURES = ["station_pressure", "sea_level_pressure", "altimeter_pressure"]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(json.dumps(value, indent=2, default=str, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def download(url, path, min_free_gb=2):
    """Resumable at FILE boundaries, atomic completion, retries, content receipts."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = path.with_name(path.name + ".receipt.json")
    if path.exists() and receipt.exists():
        previous = json.loads(receipt.read_text())
        if previous.get("url") == url and previous.get("sha256") == digest(path):
            return previous
        raise RuntimeError(f"Cached file/receipt mismatch: {path}; use a new experiment folder")
    if path.exists():
        raise RuntimeError(f"Unreceipted file exists: {path}; will not silently adopt/overwrite it")
    last_error = None
    for attempt in range(3):
        try:
            if shutil.disk_usage(path.parent).free < min_free_gb * 1024**3:
                raise OSError("Insufficient disk space; pause and free space before resuming")
            with requests.get(url, stream=True, timeout=(20, 60), headers={
                "User-Agent": "SkyGuard-academic-data-audit/11 (bounded historical download)"
            }) as response:
                response.raise_for_status()
                tmp = path.with_name(path.name + ".partial")
                with tmp.open("wb") as stream:
                    for block in response.iter_content(1024 * 1024):
                        if block:
                            stream.write(block)
                if not tmp.stat().st_size:
                    raise ValueError("Empty response")
                if path.suffix == ".csv":
                    header = pd.read_csv(tmp, nrows=0).columns
                    required = {"STATION", "DATE", "TMP", "DEW", "SLP"} if "/access/" in url else {"USAF", "WBAN"}
                    if not required.issubset(header):
                        raise ValueError(f"Unsupported source schema: {list(header)[:10]}")
                tmp.replace(path)
                record = {"url": url, "retrieved_at_utc": utc_now(), "bytes": path.stat().st_size,
                          "sha256": digest(path), "last_modified": response.headers.get("Last-Modified")}
                write_json(receipt, record)
                return record
        except (requests.RequestException, ValueError, OSError) as exc:
            last_error = exc
            if isinstance(exc, OSError) and "disk space" in str(exc):
                break
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Download failed ({url}): {last_error}")


def discover(root, benchmark_ids=()):
    root = Path(root)
    download(HISTORY_URL, root / "metadata/isd-history.csv")
    download(INVENTORY_URL, root / "metadata/isd-inventory.csv")
    history = pd.read_csv(root / "metadata/isd-history.csv", dtype=str).fillna("")
    h = history.loc[history.CTRY.eq("IN")].copy()
    h["station_id"] = h.USAF.str.zfill(6) + h.WBAN.str.zfill(5)
    if h.station_id.duplicated().any():
        raise ValueError("Duplicate station IDs in history: resolve before selecting stations")
    for source, target in [("LAT", "latitude"), ("LON", "longitude"), ("ELEV(M)", "elevation_m")]:
        h[target] = pd.to_numeric(h[source], errors="coerce")
    h["coordinate_valid"] = h.latitude.between(-90, 90) & h.longitude.between(-180, 180) & ~((h.latitude == 0) & (h.longitude == 0))
    h["station_name"] = h["STATION NAME"]
    h["legacy_24_station"] = h.station_id.isin(set(benchmark_ids))
    # Co-located station aliases must not enter opposite train/holdout sides.
    h["geographic_block"] = (np.floor(h.latitude / 2).astype("Int64").astype(str) + ":" +
                              np.floor(h.longitude / 2).astype("Int64").astype(str))
    h["station_role"] = h.geographic_block.map(
        lambda x: "spatial_holdout" if int(hashlib.sha256(("i11:" + x).encode()).hexdigest()[:8], 16) % 5 == 0 else "development")
    inventory = pd.read_csv(root / "metadata/isd-inventory.csv", dtype={"USAF": str, "WBAN": str})
    inventory["station_id"] = inventory.USAF.str.zfill(6) + inventory.WBAN.str.zfill(5)
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    jobs = []
    for year in YEARS:
        index_path = root / f"metadata/index_{year}.html"
        download(f"{BASE}/{year}/", index_path)
        listed = set(re.findall(r'href="(\d{11})\.csv"', index_path.read_text(errors="replace")))
        if not listed:
            raise ValueError(f"No ISD CSV links found for {year}; source availability must be reviewed")
        counts = inventory.loc[inventory.YEAR.eq(year)].set_index("station_id")[months].sum(axis=1)
        h[f"inventory_reports_{year}"] = h.station_id.map(counts).fillna(0).astype(int)
        h[f"file_listed_{year}"] = h.station_id.isin(listed)
        for sid in h.loc[h.coordinate_valid & h[f"file_listed_{year}"], "station_id"]:
            jobs.append({"station_id": sid, "year": year, "url": f"{BASE}/{year}/{sid}.csv"})
    h.to_csv(root / "station_catalog.csv", index=False)
    jobs = pd.DataFrame(jobs)
    jobs.to_csv(root / "download_plan.csv", index=False)
    summary = {
        "version": VERSION, "created_at_utc": utc_now(), "source": "NOAA ISD Indian-station historical proxy; not IMD AWS network",
        "indian_metadata_station_ids": len(h), "with_coordinates": int(h.coordinate_valid.sum()),
        "candidate_station_ids_with_any_listed_file": int(jobs.station_id.nunique()),
        "listed_station_year_files": len(jobs), "listed_by_year": jobs.groupby("year").station_id.nunique().to_dict(),
        "usable_T_P_RH_station_count": "NOT KNOWN until raw downloads and quality profiling complete",
        "imd_1008": "Separate IMD network count, NOT denominator for NOAA archive coverage",
        "no_2024_or_2025_data": True,
    }
    write_json(root / "discovery_receipt.json", summary)
    return h, jobs, summary


def acquire(root, station_ids=None, workers=3):
    root = Path(root)
    jobs = pd.read_csv(root / "download_plan.csv", dtype={"station_id": str})
    if station_ids is not None:
        jobs = jobs[jobs.station_id.isin(station_ids)]
    results = []
    def fetch(row):
        try:
            rec = download(row["url"], root / f"raw/{row['year']}/{row['station_id']}.csv")
            return {**row, **rec, "status": "complete", "error": ""}
        except Exception as exc:
            return {**row, "status": "failed", "error": str(exc)}
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
        futures = [pool.submit(fetch, row) for row in jobs.to_dict("records")]
        for done in as_completed(futures):
            result = done.result()
            results.append(result)
            pd.DataFrame(results).to_csv(root / "download_status.csv", index=False)
            if len(results) % 20 == 0 or result["status"] == "failed":
                print(f"Downloaded/checked {len(results)}/{len(jobs)}: {result['station_id']} {result['status']}", flush=True)
    return pd.DataFrame(results)


def parse_group(series, index=0):
    parts = series.fillna("").astype(str).str.split(",", expand=True)
    raw = parts[index].str.strip() if index in parts else pd.Series("", index=series.index)
    values = pd.to_numeric(raw, errors="coerce").div(10)
    values = values.mask(raw.str.match(r"^[+-]?999"))
    quality = parts[index + 1].fillna("").str.strip() if index + 1 in parts else pd.Series("", index=series.index)
    return values, quality


def normalize(raw, meta):
    sid = str(meta["station_id"])
    r = raw.loc[raw.STATION.astype(str).eq(sid)].copy()
    o = pd.DataFrame(index=r.index)
    o["timestamp_utc"] = pd.to_datetime(r.DATE, utc=True, errors="coerce")
    o["temperature_c"], o["temperature_qc"] = parse_group(r.TMP)
    dew, dew_qc = parse_group(r.DEW)
    o["dew_point_c"] = dew  # provenance only: never a model feature
    o["dew_point_qc"] = dew_qc
    # No silent RH clipping: supersaturation and invalid derivations stay auditable.
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        rh = 100 * np.exp(17.625 * dew / (243.04 + dew) - 17.625 * o.temperature_c / (243.04 + o.temperature_c))
    o["relative_humidity_pct"] = rh.replace([np.inf, -np.inf], np.nan)
    o["rh_source"] = "derived_from_T_and_dewpoint_NOT_direct_sensor_RH"
    o["sea_level_pressure"], o["sea_level_pressure_qc"] = parse_group(r.SLP)
    ma = r.get("MA1", pd.Series("", index=r.index))
    o["altimeter_pressure"], o["altimeter_pressure_qc"] = parse_group(ma, 0)
    o["station_pressure"], o["station_pressure_qc"] = parse_group(ma, 2)
    for key in ["station_id", "latitude", "longitude", "elevation_m", "station_role", "geographic_block", "legacy_24_station"]:
        o[key] = meta[key]
    o["report_type"] = r.get("REPORT_TYPE", "")
    o["source"] = "NOAA_NCEI_ISD"
    o["source_qc_temperature_ok"] = o.temperature_qc.isin(GOOD_QC)
    o["source_qc_humidity_ok"] = o.temperature_qc.isin(GOOD_QC) & dew_qc.isin(GOOD_QC)
    o = o.loc[o.timestamp_utc.notna() & o.timestamp_utc.dt.year.isin(YEARS)]
    # Deterministic duplicate report selection; no label information involved.
    o["_complete"] = o[["temperature_c", "relative_humidity_pct", *PRESSURES]].notna().sum(axis=1)
    o["_qc"] = o.source_qc_temperature_ok.astype(int) + o.source_qc_humidity_ok.astype(int)
    o = o.sort_values(["timestamp_utc", "_qc", "_complete"], ascending=[True, False, False], kind="stable")
    return o.drop_duplicates("timestamp_utc").drop(columns=["_complete", "_qc"]).sort_values("timestamp_utc").reset_index(drop=True)


def choose_pressure(frame):
    """Choose ONE pressure type using 2020--21 only; never row-wise datum fallback."""
    fit = frame.loc[frame.timestamp_utc.dt.year.isin([2020, 2021])]
    counts = {p: int((fit[p].notna() & fit[p + "_qc"].isin(GOOD_QC)).sum()) for p in PRESSURES}
    choice = max(PRESSURES, key=lambda p: counts[p]) if max(counts.values(), default=0) else None
    o = frame.copy()
    o["pressure_datum"] = choice or "unavailable"
    o["pressure_hpa"] = o[choice] if choice else np.nan
    o["source_qc_pressure_ok"] = o[choice + "_qc"].isin(GOOD_QC) if choice else False
    plausible = o.temperature_c.between(-90, 65) & o.pressure_hpa.between(300, 1100) & o.relative_humidity_pct.between(0, 100, inclusive="right")
    o["qc_screened_proxy"] = plausible & o.source_qc_temperature_ok & o.source_qc_humidity_ok & o.source_qc_pressure_ok
    o["label_status"] = np.where(o.qc_screened_proxy, "presumed_normal_NOT_verified", "unknown")
    o["ground_truth_fault"] = -1  # archived observations are NOT sensor-fault ground truth
    return o, counts


def profile(frame, split):
    d = frame.loc[frame.timestamp_utc.dt.year.isin([2020, 2021] if split == "fit" else [2022, 2023])]
    delta = d.timestamp_utc.diff().dt.total_seconds().div(60)
    complete = d[PRIMARY].notna().all(axis=1)
    screened = d.qc_screened_proxy
    return {
        "rows": len(d), "complete_triples": int(complete.sum()), "screened_proxy_rows": int(screened.sum()),
        "screened_days": int(d.loc[screened, "timestamp_utc"].dt.floor("D").nunique()),
        "median_cadence_minutes": float(delta.median()) if delta.notna().any() else None,
        "gaps_over_6h": int(delta.gt(360).sum()),
        "missing_pressure_fraction": float(d.pressure_hpa.isna().mean()) if len(d) else None,
    }


def haversine(lat1, lon1, lat2, lon2):
    a, b, c, d = map(np.radians, [lat1, lon1, lat2, lon2])
    x = np.sin((c-a)/2)**2 + np.cos(a)*np.cos(c)*np.sin((d-b)/2)**2
    return 6371 * 2 * np.arcsin(np.sqrt(np.clip(x, 0, 1)))


def neighbor_graph(stations, radius_km=150, elevation_tolerance_m=300, max_neighbors=8):
    edges = []
    rows = stations.to_dict("records")
    for a in rows:
        options = []
        for b in rows:
            if a["station_id"] == b["station_id"]:
                continue
            if not np.isfinite(a["elevation_m"]) or not np.isfinite(b["elevation_m"]):
                continue  # no invented zero elevation
            km = float(haversine(a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
            dz = abs(a["elevation_m"] - b["elevation_m"])
            if km <= radius_km and dz <= elevation_tolerance_m:
                # Exclude near-coincident aliases; they are not independent buddies.
                if km < 1:
                    continue
                options.append({"station_id": a["station_id"], "neighbor_id": b["station_id"],
                                "distance_km": km, "elevation_difference_m": dz,
                                "pressure_compatible": a["pressure_datum"] == b["pressure_datum"],
                                "neighbor_role": b["station_role"]})
        edges.extend(sorted(options, key=lambda x: x["distance_km"])[:max_neighbors])
    return pd.DataFrame(edges, columns=["station_id", "neighbor_id", "distance_km", "elevation_difference_m", "pressure_compatible", "neighbor_role"])


def prepare(root):
    root = Path(root)
    catalog = pd.read_csv(root / "station_catalog.csv", dtype={"station_id": str})
    rows = []
    processed = root / "processed"
    processed.mkdir(exist_ok=True)
    for meta in catalog.to_dict("records"):
        paths = [root / f"raw/{y}/{meta['station_id']}.csv" for y in YEARS]
        paths = [p for p in paths if p.exists() and p.with_name(p.name + ".receipt.json").exists()]
        if not paths:
            continue
        data = []
        for path in paths:
            if digest(path) != json.loads(path.with_name(path.name + ".receipt.json").read_text())["sha256"]:
                raise ValueError(f"Corrupt raw cache: {path}")
            raw = pd.read_csv(path, dtype=str, low_memory=False)
            data.append(normalize(raw, meta))
        frame, counts = choose_pressure(pd.concat(data, ignore_index=True).sort_values("timestamp_utc"))
        frame = frame.drop_duplicates(["station_id", "timestamp_utc"]).reset_index(drop=True)
        train = profile(frame, "fit")
        eligible = train["screened_proxy_rows"] >= 1000 and train["screened_days"] >= 180
        record = {**{k: meta[k] for k in ["station_id", "station_name", "latitude", "longitude", "elevation_m", "station_role", "geographic_block", "legacy_24_station"]},
                  "pressure_datum": frame.pressure_datum.iloc[0] if len(frame) else "unavailable",
                  "training_eligible": eligible, "exclusion_reason": "" if eligible else "fewer_than_1000_screened_rows_or_180_days_in_2020_21",
                  **{"fit_" + k: v for k, v in train.items()}, **{"eval_" + k: v for k, v in profile(frame, "eval").items()},
                  **{"fit_count_" + k: v for k, v in counts.items()}, "raw_files": len(paths)}
        target = processed / f"{meta['station_id']}.parquet"
        tmp = target.with_suffix(".partial.parquet")
        frame.to_parquet(tmp, index=False)
        tmp.replace(target)
        record["processed_sha256"] = digest(target)
        rows.append(record)
        print(f"Prepared {meta['station_id']}: {len(frame):,} rows; training eligible={eligible}", flush=True)
    summary = pd.DataFrame(rows)
    if summary.empty:
        raise ValueError("No downloaded station files. Run acquisition first.")
    summary.to_csv(root / "station_quality.csv", index=False)
    ready = summary.loc[summary.training_eligible]
    graph = neighbor_graph(ready)
    graph.to_csv(root / "neighbor_graph.csv", index=False)
    support = ready[["station_id", "station_role", "pressure_datum", "legacy_24_station"]].copy()
    support["geographic_buddies"] = support.station_id.map(graph.groupby("station_id").size()).fillna(0).astype(int)
    support["pressure_compatible_buddies"] = support.station_id.map(graph.loc[graph.pressure_compatible].groupby("station_id").size()).fillna(0).astype(int)
    support.to_csv(root / "spatial_support.csv", index=False)
    receipt = {"version": VERSION, "created_at_utc": utc_now(), "downloaded_stations": len(summary),
               "training_eligible_stations": len(ready), "new_eligible_outside_old24": int((~ready.legacy_24_station).sum()),
               "fit_screened_proxy_rows": int(ready.fit_screened_proxy_rows.sum()),
               "stations_with_at_least_2_geographic_buddies": int(support.geographic_buddies.ge(2).sum()),
               "stations_with_at_least_2_pressure_buddies": int(support.pressure_compatible_buddies.ge(2).sum()),
               "caveat": "Geographic support is an upper bound; contemporaneous non-stale readings also required",
               "ready_for_expanded_training": bool(len(ready) >= 50 and (~ready.legacy_24_station).sum() >= 25),
               "no_verified_real_fault_labels": True, "pressure_contract": "one type per station fitted on 2020-21; missing retained, no fallback",
               "all_data_hash": hashlib.sha256(summary[["station_id", "processed_sha256"]].sort_values("station_id").to_csv(index=False).encode()).hexdigest()}
    write_json(root / "data_readiness.json", receipt)
    return summary, graph, receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["discover", "download", "prepare"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--stations", nargs="*")
    args = parser.parse_args()
    if args.action == "discover":
        old = pd.read_csv(args.benchmark, dtype=str).station_id if args.benchmark else []
        print(discover(args.root, old)[2])
    elif args.action == "download":
        print(acquire(args.root, args.stations).status.value_counts())
    else:
        print(prepare(args.root)[2])

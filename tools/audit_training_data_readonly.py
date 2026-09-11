"""Independent descriptive audit of stored development data; no fitting/scoring.

Reads underlying CSVs and a representative DWD raw product, not Markdown
verdicts. Does not modify any data/model file or open labelled 2024/2025 tests.
The original combined India archive is scanned but only 2022/2023 records are
analysed; its aggregate stored row count includes 2024. One JSON audit report
is the only output, outside the source data directories.
"""
from __future__ import annotations

import io
import hashlib
import json
import math
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/TRAINING_DATA_AUDIT_2026_09_11.json"
PRIMARY = ["temperature_c", "pressure_hpa", "relative_humidity_pct"]


def packaged_data_identity():
    checks=[]
    for package,source in (
        ("SkyGuard_Iteration10_Final_Starter_Bundle.zip", "data/iteration10/processed/india_aws_2022_2023.csv.gz"),
        ("SkyGuard_Iteration8_Development_Data_Bundle.zip", "data/iteration8/processed/dwd_aws_10min_2022.csv.gz"),
        ("SkyGuard_Iteration8_Development_Data_Bundle.zip", "data/iteration8/processed/dwd_aws_10min_2023.csv.gz"),
    ):
        with zipfile.ZipFile(ROOT/"deliverables"/package) as archive:
            member=next(n for n in archive.namelist() if n.endswith("/"+Path(source).name))
            embedded_hash=hashlib.sha256(archive.read(member)).hexdigest()
            local_hash=hashlib.sha256((ROOT/source).read_bytes()).hexdigest()
            checks.append({"package":package,"member":member,"local_file":source,"same_bytes":embedded_hash==local_hash,"local_sha256":local_hash,"embedded_sha256":embedded_hash})
    return checks


def counts(series):
    return {str(k): int(v) for k, v in series.fillna("<missing>").value_counts(dropna=False).items()}


def frame(relative):
    return pd.read_csv(ROOT / relative, dtype={"station_id": str}, low_memory=False)


def summary(df):
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df.timestamp_utc, utc=True, errors="coerce")
    values = df[PRIMARY].apply(pd.to_numeric, errors="coerce")
    result = {
        "rows": len(df), "stations": int(df.station_id.nunique()),
        "start": str(df.timestamp_utc.min()), "end": str(df.timestamp_utc.max()),
        "invalid_timestamps": int(df.timestamp_utc.isna().sum()),
        "duplicate_station_times": int(df.duplicated(["station_id", "timestamp_utc"]).sum()),
        "missing": {c: int(values[c].isna().sum()) for c in PRIMARY},
        "complete_triples": int(values.notna().all(axis=1).sum()),
        "rows_on_whole_hour": int(df.timestamp_utc.dt.minute.eq(0).sum()),
        "ranges": {c: {"min": float(values[c].min()), "max": float(values[c].max()), "integer_value_percent": float(np.isclose(values[c].dropna() % 1, 0).mean() * 100)} for c in PRIMARY},
        "categories": {c: counts(df[c]) for c in ("source", "pressure_source", "report_type", "temperature_quality", "pressure_quality", "cluster", "evaluation_role") if c in df},
        "by_station": [],
    }
    if "dew_point_c" in df:
        dew = pd.to_numeric(df.dew_point_c, errors="coerce")
        rh = (100 * np.exp(17.625 * dew / (243.04 + dew) - 17.625 * values.temperature_c / (243.04 + values.temperature_c))).clip(0, 100)
        result["dewpoint_above_temperature_rows"] = int((dew > values.temperature_c).sum())
        result["rh_matches_magnus_to_0_001_percent"] = float(np.isclose(rh[values.relative_humidity_pct.notna()], values.relative_humidity_pct.dropna(), atol=.001, rtol=0, equal_nan=False).mean() * 100)
    all_gaps = []
    for station, group in df.groupby("station_id", sort=True):
        group = group.sort_values("timestamp_utc")
        delta = group.timestamp_utc.diff().dt.total_seconds().div(60)
        positive = delta[delta > 0]
        all_gaps.append(positive)
        source = group.pressure_source.fillna("") if "pressure_source" in group else pd.Series("", index=group.index)
        switch = source.ne(source.shift()) & source.ne("") & source.shift().fillna("").ne("")
        numeric = group[PRIMARY].apply(pd.to_numeric, errors="coerce")
        result["by_station"].append({
            "station_id": station, "name": str(group.station_name.iloc[0]) if "station_name" in group else station,
            "rows": len(group), "complete_triple_pct": float(numeric.notna().all(axis=1).mean()*100),
            "median_gap_minutes": float(positive.median()), "p90_gap_minutes": float(positive.quantile(.9)),
            "max_gap_hours": float(positive.max()/60), "gaps_over_6h": int((positive>360).sum()),
            "reporting_days": int(group.timestamp_utc.dt.floor("D").nunique()),
            "pressure_sources": counts(source), "pressure_source_switches": int(switch.sum()),
            "pressure_switch_jump_median_hpa": float(numeric.pressure_hpa.diff().abs()[switch].median()),
        })
    gaps = pd.concat(all_gaps)
    result["report_gaps_minutes_counts"] = counts(gaps.round(3))
    result["gap_over_6h_count"] = int((gaps>360).sum())
    return result


def config_distance(relative):
    config = frame(relative)
    clusters = {}
    for cluster, group in config.groupby("cluster"):
        pairs = []
        records = group.to_dict("records")
        for i, a in enumerate(records):
            for b in records[i+1:]:
                lat1, lon1, lat2, lon2 = map(math.radians, (a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
                hav = math.sin((lat1-lat2)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon1-lon2)/2)**2
                distance = 6371 * 2 * math.asin(min(1, math.sqrt(hav)))
                pairs.append({"a": a["station_name"], "b": b["station_name"], "distance_km": round(distance, 1), "elevation_difference_m": round(abs(a["elevation_m"]-b["elevation_m"]),1)})
        clusters[cluster] = {"stations": len(group), "min_km": min(p["distance_km"] for p in pairs), "max_km": max(p["distance_km"] for p in pairs), "pairs_over_200km": sum(p["distance_km"]>200 for p in pairs), "pairs": pairs}
    return clusters


def raw_noaa_spotcheck(df):
    # Recover MA1 station-pressure fields independently of the project parser.
    examples = []
    manifest = frame("data/manifest/raw_files.csv")
    for station in ("42181099999", "43295099999", "43296099999"):
        path = ROOT / "data/raw/noaa/2022" / f"{station}.csv"
        if not path.exists():
            continue
        raw = pd.read_csv(path, dtype=str, usecols=lambda c:c in {"STATION","DATE","TMP","DEW","SLP","MA1","REPORT_TYPE"})
        ma1 = raw.get("MA1", pd.Series("",index=raw.index)).fillna("").str.split(",",expand=True)
        if ma1.shape[1]<3:
            continue
        station_pressure = pd.to_numeric(ma1[2],errors="coerce")/10
        valid_station = station_pressure.between(500,1100)
        examples.append({"station_id": station, "raw_rows": len(raw), "raw_rows_with_MA1_station_pressure": int(valid_station.sum()), "sample": raw.loc[valid_station].head(2).fillna("").to_dict("records"), "source_url": manifest.loc[manifest.station_id.eq(station)&pd.to_numeric(manifest.year,errors="coerce").eq(2022),"url"].tolist()})
    return examples


def main():
    report = {"audit_time_utc": datetime.now(timezone.utc).isoformat(), "scope": "Descriptive 2022/2023 data audit, no fitting, no new accuracy scoring; saved source code does not prove original artifact training execution"}
    legacy = frame("data/processed/aws_observations_2022_2024.csv")
    report["legacy_archive_total_rows"] = len(legacy)
    legacy = legacy[legacy.year.isin([2022,2023])].copy()
    report["india_legacy_development"] = summary(legacy)
    print("Audited original India development records", flush=True)
    revised = frame("data/iteration10/processed/india_aws_2022_2023.csv.gz")
    report["india_iteration10_development"] = summary(revised)
    joined = legacy.merge(revised, on=["station_id","timestamp_utc"], suffixes=("_legacy","_revised"), how="outer", indicator=True)
    both = joined._merge.eq("both")
    report["india_revision_comparison"] = {
        "join": counts(joined._merge.astype(str)),
        "pressure_newly_available": int((both & joined.pressure_hpa_legacy.isna() & joined.pressure_hpa_revised.notna()).sum()),
        "pressure_changed_over_0_01_hpa": int((both & (joined.pressure_hpa_legacy-joined.pressure_hpa_revised).abs().gt(.01)).sum()),
    }
    bangalore = revised[revised.station_id.eq("43295099999")].sort_values("timestamp_utc").copy()
    switches = bangalore.pressure_source.ne(bangalore.pressure_source.shift()) & bangalore.pressure_hpa.diff().abs().gt(100)
    report["bangalore_pressure_switch_examples"] = []
    for position in np.flatnonzero(switches.to_numpy())[:3]:
        report["bangalore_pressure_switch_examples"].append(bangalore.iloc[position-1:position+1][["timestamp_utc", "pressure_hpa", "pressure_source"]].to_dict("records"))
    report["raw_noaa_spotchecks"] = raw_noaa_spotcheck(revised)
    del joined, revised
    report["dwd_development"] = {}
    for year in (2022,2023):
        dwd = frame(f"data/iteration8/processed/dwd_aws_10min_{year}.csv.gz")
        report["dwd_development"][str(year)] = summary(dwd)
        if year==2022:
            report["dwd_saved_samples"] = dwd.head(2).to_dict("records")
        del dwd
        print(f"Audited DWD {year}",flush=True)
    config = frame("config/iteration8_dwd_stations.csv")
    selected = config.iloc[0]
    with zipfile.ZipFile(ROOT / "data/iteration8/raw/dwd/historical" / selected.archive_file) as archive:
        member = next(n for n in archive.namelist() if n.startswith("produkt_zehn_min_tu_"))
        with archive.open(member) as stream:
            pieces=[]
            for chunk in pd.read_csv(stream,sep=";",dtype=str,chunksize=100000):
                chunk.columns=chunk.columns.str.strip()
                times=chunk.MESS_DATUM.str.strip()
                keep=times.str[:4].isin(["2022","2023"])
                pieces.append(chunk[keep].copy())
            raw=pd.concat(pieces,ignore_index=True)
            raw.columns=raw.columns.str.strip()
            vals=raw[["TT_10","PP_10","RF_10"]].apply(pd.to_numeric,errors="coerce")
            report["dwd_raw_station_spotcheck"]={"station_id":selected.station_id,"archive":selected.archive_file,"development_rows":len(raw),"missing_or_sentinel_counts":{c:int((vals[c].isna()|vals[c].le(-999)).sum()) for c in vals},"quality_levels":counts(raw["QN"].str.strip()) if "QN" in raw else {},"sample":raw.head(2).to_dict("records")}
    report["labels"]={}
    report["feature_tables"]={}
    feature_spec=json.loads((ROOT/"data/features_phase10/feature_spec.json").read_text())
    feature_names=feature_spec["model_features"]
    for split in ("train","validation"):
        labelled=frame(f"data/labelled/{split}.csv")
        report["labels"][split]={"rows":len(labelled),"station_count":int(labelled.station_id.nunique()),"label_sources":counts(labelled.label_source),"categories":counts(labelled.label_category),"faults":counts(labelled.anomaly_type),"fault_rows":int(labelled.is_anomaly.sum()),"weather_rows":int(labelled.is_weather_event.sum()),"fault_episodes":int(labelled.loc[labelled.is_anomaly.eq(1),"episode_id"].nunique()),"original_value_columns":[c for c in labelled if c.startswith("original_")]}
        normal = labelled[labelled.label_category.eq("normal")]
        report["labels"][split]["normal_label_with_missing_primary"] = int(normal[PRIMARY].isna().any(axis=1).sum())
        report["labels"][split]["normal_label_with_source_qc_suspect"] = int(normal[["temperature_quality", "pressure_quality"]].apply(lambda s:pd.to_numeric(s,errors="coerce").isin([2,3,6,7])).any(axis=1).sum())
        features=frame(f"data/features_phase10/{split}_features.csv.gz")
        visible=features[features.available_to_detector.eq(1)].copy()
        times=pd.to_datetime(visible.emitted_timestamp_utc,utc=True)
        report["feature_tables"][split]={"rows":len(features),"visible_rows":len(visible),"visible_station_count":int(visible.station_id.nunique()),"year_counts":counts(times.dt.year),"h1_rows":int(times.dt.month.le(6).sum()),"h2_rows":int(times.dt.month.gt(6).sum()),"non_india_station_ids":sorted(set(visible.station_id)-set(legacy.station_id)),"raw_input_missing":{c:int(features[c].isna().sum()) for c in ("temperature_value","pressure_value","humidity_value")},"neighbour_count":counts(visible.neighbor_station_count) if "neighbor_station_count" in visible else {},"features_with_label_like_names":[c for c in feature_names if any(term in c.lower() for term in ("label","episode","original","injection","station_id","source","dew"))]}
        del features,visible,labelled
    report["configured_distances"]={"india":config_distance("config/stations.csv"),"dwd":config_distance("config/iteration8_dwd_stations.csv")}
    # Inspect latest notebook code/data flow without executing its cells.
    notebook=json.loads((ROOT/"notebooks/SkyGuard_AI_GPU_Iteration_10R_Calibration_Integrity_Repair_Colab.ipynb").read_text(encoding="utf-8"))
    matches=[]
    terms=("india_aws_2022_2023", "dwd_aws_10min_", "resample(", ".dt.minute", "I10_INDIA", "read_csv(")
    for index,cell in enumerate(notebook["cells"]):
        if cell["cell_type"]!="code":continue
        lines="".join(cell["source"]).splitlines()
        for i,line in enumerate(lines):
            if any(term in line for term in terms):matches.append({"cell":index+1,"code":"\n".join(lines[max(0,i-2):i+3])})
    report["latest_notebook_data_code"]=matches
    report["packaged_development_identity"]=packaged_data_identity()
    def clean(value):
        if isinstance(value,dict): return {str(k):clean(v) for k,v in value.items()}
        if isinstance(value,list):return [clean(v) for v in value]
        if isinstance(value,float) and not math.isfinite(value):return None
        if isinstance(value,np.generic):return clean(value.item())
        return value
    OUTPUT.write_text(json.dumps(clean(report),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Audit report: {OUTPUT}",flush=True)


if __name__=="__main__":
    if "--packages-only" in sys.argv:
        report=json.loads(OUTPUT.read_text(encoding="utf-8"))
        report["packaged_development_identity"]=packaged_data_identity()
        OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(json.dumps(report["packaged_development_identity"],indent=2))
    else:main()

"""Iteration 12: authenticated, immutable IMD AWS observation collection.

This module collects the official IMD AWS endpoint only.  It never fabricates
observations, silently substitutes another provider, or treats unlabelled rows
as verified healthy/faulty examples.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

VERSION = "iteration12-imd-aws-v1"
AWS_URL = "https://api.imd.gov.in/api/v1/aws_data"
MAPPING_URL = "https://api.imd.gov.in/api/v1/aws_data_mapping"
MODEL_INPUTS = ["temperature_c", "pressure_hpa", "relative_humidity_pct"]
RAW_FIELDS = {
    "ID": "imd_sensor_id",
    "CALL_SIGN": "station_id",
    "DISTRICT": "district",
    "STATE": "state",
    "STATION": "station_name",
    "CURR_TEMP": "temperature_c",
    "RH": "relative_humidity_pct",
    "MSLP": "pressure_hpa",
    "Latitude": "latitude",
    "Longitude": "longitude",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _json_rows(payload):
    """Extract the records list without assuming an undocumented envelope."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "records", "result", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
        if set(RAW_FIELDS).intersection(payload):
            return [payload]
    raise ValueError("IMD response has no supported record list; preserve it and review the API contract")


def fetch_json(url: str, api_key: str, jwt_token: str, *, params=None, timeout=60):
    if not api_key or not jwt_token:
        raise ValueError("Both IMD_API_KEY and IMD_JWT_TOKEN are required")
    headers = {
        "x-api-key": api_key.strip(),
        "Authorization": "Bearer " + jwt_token.strip(),
        "Accept": "application/json",
        "User-Agent": "SkyGuard-SIH26073-academic-collector/12",
    }
    last = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=(20, timeout))
            if response.status_code == 401:
                raise PermissionError("IMD rejected the API key/JWT; renew credentials in the official portal")
            response.raise_for_status()
            if "json" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("IMD returned non-JSON content")
            payload = response.json()
            return payload, {
                "url": response.url,
                "retrieved_at_utc": utc_now(),
                "http_status": response.status_code,
                "content_type": response.headers.get("Content-Type"),
                "last_modified": response.headers.get("Last-Modified"),
                "payload_sha256": sha256_bytes(response.content),
                "bytes": len(response.content),
            }
        except PermissionError:
            raise
        except (requests.RequestException, ValueError) as exc:
            last = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise RuntimeError(f"Official IMD request failed after retries: {last}")


def normalize_aws(payload, *, source_timezone="UTC", collected_at_utc=None):
    rows = _json_rows(payload)
    if not rows:
        raise ValueError("IMD AWS response contains zero records")
    raw = pd.DataFrame(rows)
    missing = [key for key in ("CALL_SIGN", "DATE", "TIME", "CURR_TEMP", "RH", "MSLP") if key not in raw]
    if missing:
        raise ValueError(f"IMD AWS schema is missing required fields: {missing}")
    out = pd.DataFrame(index=raw.index)
    for source, target in RAW_FIELDS.items():
        out[target] = raw[source] if source in raw else pd.NA
    source_text = raw["DATE"].astype(str).str.strip() + " " + raw["TIME"].astype(str).str.strip()
    local = pd.to_datetime(source_text, errors="coerce")
    if source_timezone.upper() == "UTC":
        timestamp = local.dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
    else:
        timestamp = local.dt.tz_localize(source_timezone, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    out["timestamp_utc"] = timestamp
    out["source_date"] = raw["DATE"].astype(str)
    out["source_time"] = raw["TIME"].astype(str)
    out["source_timezone_contract"] = source_timezone
    out["collected_at_utc"] = collected_at_utc or utc_now()
    for col in MODEL_INPUTS + ["latitude", "longitude"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["station_id", "imd_sensor_id", "station_name", "district", "state"]:
        out[col] = out[col].fillna("").astype(str).str.strip()
    out["temperature_reported_directly"] = True
    out["humidity_reported_directly"] = True
    out["pressure_source"] = "IMD_MSLP"
    out["source"] = "IMD_AUTHORIZED_AWS_API"
    out["generated_or_simulated"] = False
    out["timestamp_valid"] = out.timestamp_utc.notna()
    out["coordinates_valid"] = (out.latitude.between(6, 38) & out.longitude.between(68, 98))
    out["primary_complete"] = out[MODEL_INPUTS].notna().all(axis=1)
    out["broad_physical_range_ok"] = (
        out.temperature_c.between(-60, 65)
        & out.pressure_hpa.between(850, 1100)
        & out.relative_humidity_pct.between(0, 100)
    )
    out["eligible_for_unlabelled_baseline"] = (
        out.timestamp_valid & out.coordinates_valid & out.primary_complete & out.broad_physical_range_ok
    )
    out["ground_truth_fault"] = -1
    out["label_status"] = "unlabelled_observation"
    out = out.sort_values(["station_id", "timestamp_utc"], kind="stable")
    return out.drop_duplicates(["station_id", "timestamp_utc"], keep="last").reset_index(drop=True)


def archive_snapshot(root, payload, receipt, *, source_timezone="UTC"):
    root = Path(root)
    retrieved = pd.Timestamp(receipt["retrieved_at_utc"])
    stamp = retrieved.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = root / "raw" / retrieved.strftime("%Y/%m/%d")
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"imd_aws_{stamp}.json"
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_hash = sha256_bytes(encoded)
    if raw_path.exists() and sha256_file(raw_path) != payload_hash:
        raise FileExistsError(f"Immutable snapshot collision: {raw_path}")
    raw_path.write_bytes(encoded)
    frame = normalize_aws(payload, source_timezone=source_timezone, collected_at_utc=receipt["retrieved_at_utc"])
    clean_dir = root / "normalized" / retrieved.strftime("%Y/%m/%d")
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_path = clean_dir / f"imd_aws_{stamp}.parquet"
    if not clean_path.exists():
        frame.to_parquet(clean_path, index=False)
    record = {**receipt, "version": VERSION, "raw_path": str(raw_path.relative_to(root)),
              "raw_saved_sha256": sha256_file(raw_path),
              "normalized_path": str(clean_path.relative_to(root)), "normalized_sha256": sha256_file(clean_path),
              "records": len(frame), "stations": int(frame.station_id.nunique()),
              "complete_primary_records": int(frame.primary_complete.sum()),
              "credentials_recorded": False, "generated_rows": 0}
    receipt_path = raw_path.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return frame, record


def collect_once(root, api_key, jwt_token, *, state_id=None, source_timezone="UTC"):
    params = {"sid": str(state_id)} if state_id is not None else None
    payload, receipt = fetch_json(AWS_URL, api_key, jwt_token, params=params)
    return archive_snapshot(root, payload, receipt, source_timezone=source_timezone)


def collect_mapping(root, api_key, jwt_token):
    payload, receipt = fetch_json(MAPPING_URL, api_key, jwt_token)
    root = Path(root)
    target = root / "metadata" / "imd_aws_mapping.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    target.write_bytes(encoded)
    receipt.update({"version": VERSION, "path": str(target.relative_to(root)),
                    "saved_sha256": sha256_file(target), "credentials_recorded": False})
    target.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return payload, receipt


def assemble(root):
    paths = sorted(Path(root).glob("normalized/**/*.parquet"))
    if not paths:
        raise ValueError("No normalized IMD snapshots found; run authenticated collection first")
    frames = [pd.read_parquet(path) for path in paths]
    data = pd.concat(frames, ignore_index=True)
    data["timestamp_utc"] = pd.to_datetime(data.timestamp_utc, utc=True, errors="coerce")
    data = data.sort_values(["station_id", "timestamp_utc", "collected_at_utc"], kind="stable")
    data = data.drop_duplicates(["station_id", "timestamp_utc"], keep="last").reset_index(drop=True)
    return data


def readiness(data, *, timestamp_timezone_confirmed=False):
    d = data.copy()
    d["timestamp_utc"] = pd.to_datetime(d.timestamp_utc, utc=True, errors="coerce")
    valid = d.loc[d.eligible_for_unlabelled_baseline.astype(bool)]
    per_station = valid.groupby("station_id").agg(
        rows=("timestamp_utc", "size"), first_timestamp=("timestamp_utc", "min"),
        last_timestamp=("timestamp_utc", "max"), distinct_days=("timestamp_utc", lambda x: x.dt.floor("D").nunique()),
        latitude=("latitude", "median"), longitude=("longitude", "median"),
    ).reset_index()
    if len(per_station):
        per_station["span_days"] = (per_station.last_timestamp - per_station.first_timestamp).dt.total_seconds().div(86400)
    else:
        per_station["span_days"] = pd.Series(dtype=float)
    complete_fraction = float(d.primary_complete.mean()) if len(d) else 0.0
    report = {
        "version": VERSION, "created_at_utc": utc_now(), "source": "authorized IMD AWS API",
        "rows": len(d), "stations": int(d.station_id.nunique()), "valid_unlabelled_rows": len(valid),
        "complete_primary_fraction": complete_fraction,
        "first_timestamp_utc": d.timestamp_utc.min().isoformat() if d.timestamp_utc.notna().any() else None,
        "last_timestamp_utc": d.timestamp_utc.max().isoformat() if d.timestamp_utc.notna().any() else None,
        "stations_30_days": int(per_station.distinct_days.ge(30).sum()),
        "stations_90_days": int(per_station.distinct_days.ge(90).sum()),
        "stations_365_days": int(per_station.distinct_days.ge(365).sum()),
        "timestamp_timezone_contracts": sorted(d.source_timezone_contract.dropna().astype(str).unique().tolist()),
        "timestamp_timezone_confirmed": bool(timestamp_timezone_confirmed),
        "ready_for_pilot_training": bool(timestamp_timezone_confirmed and len(per_station) >= 50 and per_station.distinct_days.ge(30).sum() >= 50 and complete_fraction >= .90),
        "ready_for_seasonal_claims": bool(timestamp_timezone_confirmed and len(per_station) >= 50 and per_station.distinct_days.ge(365).sum() >= 50),
        "verified_real_fault_labels": False, "generated_rows": int(d.generated_or_simulated.astype(bool).sum()),
        "model_inputs": MODEL_INPUTS,
        "warning": "Unlabelled official observations are not proof of sensor health; inject faults only in evaluation copies.",
    }
    return per_station, report

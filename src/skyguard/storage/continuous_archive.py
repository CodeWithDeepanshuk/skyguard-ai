"""Continuous IMD AWS Observation Archiver for 30-Day Model Retraining.

Saves every incoming 15-minute IMD AWS telemetry reading into persistent,
daily-partitioned JSONL and CSV archives in data/archive/imd_aws_continuous/,
and maintains an immutable manifest for automated 30-day neural retraining.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("skyguard.continuous_archive")

ARCHIVE_DIR = Path(__file__).resolve().parents[3] / "data" / "archive" / "imd_aws_continuous"
MANIFEST_PATH = ARCHIVE_DIR / "manifest.json"


def ensure_archive_dir() -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    return ARCHIVE_DIR


def archive_observation_batch(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Append a batch of live 15-minute IMD AWS records to the continuous archive.
    
    Deduplicates within the active file by (station_id, timestamp_utc).
    Updates manifest.json with continuous retention statistics.
    """
    if not records:
        return {"archived": 0, "status": "empty"}

    ensure_archive_dir()
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    
    jsonl_file = ARCHIVE_DIR / f"observations_{today_str}.jsonl"
    csv_file = ARCHIVE_DIR / f"observations_{today_str}.csv"
    
    # Load existing keys for today to prevent duplicates
    existing_keys = set()
    if jsonl_file.exists():
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        k = (str(obj.get("station_id")), str(obj.get("timestamp_utc")))
                        existing_keys.add(k)
        except Exception as e:
            logger.debug("Archive key load note: %s", e)

    new_records = []
    for r in records:
        sid = str(r.get("station_id") or r.get("canonical_station_id") or r.get("ID") or "").strip()
        ts = str(r.get("timestamp_utc") or r.get("observation_timestamp_utc") or "").strip()
        if not sid or not ts:
            continue
        key = (sid, ts)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        
        entry = {
            "station_id": sid,
            "station_name": str(r.get("station_name") or sid),
            "timestamp_utc": ts,
            "temperature_c": float(r["temperature_c"]) if r.get("temperature_c") not in (None, "") else (float(r["temperature"]) if r.get("temperature") not in (None, "") else None),
            "pressure_hpa": float(r["pressure_hpa"]) if r.get("pressure_hpa") not in (None, "") else (float(r["pressure"]) if r.get("pressure") not in (None, "") else None),
            "relative_humidity_pct": float(r["relative_humidity_pct"]) if r.get("relative_humidity_pct") not in (None, "") else (float(r["humidity"]) if r.get("humidity") not in (None, "") else None),
            "latitude": float(r["latitude"]) if r.get("latitude") not in (None, "") else None,
            "longitude": float(r["longitude"]) if r.get("longitude") not in (None, "") else None,
            "elevation_m": float(r["elevation_m"]) if r.get("elevation_m") not in (None, "") else None,
            "state": str(r.get("state") or ""),
            "district": str(r.get("district") or ""),
            "climate_zone": str(r.get("climate_zone") or ""),
            "provider": str(r.get("provider") or "IMD_AWS"),
            "archived_at_utc": now_utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        new_records.append(entry)

    if new_records:
        # Write to JSONL
        with open(jsonl_file, "a", encoding="utf-8") as f:
            for rec in new_records:
                f.write(json.dumps(rec, default=str) + "\n")
        
        # Write to CSV
        csv_exists = csv_file.exists() and csv_file.stat().st_size > 0
        fieldnames = [
            "station_id", "station_name", "timestamp_utc", "temperature_c",
            "pressure_hpa", "relative_humidity_pct", "latitude", "longitude",
            "elevation_m", "state", "district", "climate_zone", "provider", "archived_at_utc"
        ]
        with open(csv_file, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not csv_exists:
                writer.writeheader()
            for rec in new_records:
                writer.writerow(rec)

    # Update manifest
    manifest = update_manifest(len(new_records), today_str)
    
    return {
        "status": "success",
        "newly_archived": len(new_records),
        "total_archived": manifest.get("total_observations", len(new_records)),
        "file": str(jsonl_file.name),
        "days_accumulated": manifest.get("days_accumulated", 1),
    }


def update_manifest(added_count: int, today_str: str) -> Dict[str, Any]:
    """Recalculate or update the 30-day continuous retraining buffer manifest."""
    manifest_data: Dict[str, Any] = {
        "purpose": "30-day IMD AWS continuous observation buffer for scheduled ML & neural retraining",
        "target_retraining_window_days": 30,
        "total_observations": 0,
        "daily_partitions": [],
        "unique_stations_observed": 0,
        "earliest_observation_utc": None,
        "latest_observation_utc": None,
        "last_archived_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception:
            pass

    # Scan partitions in archive directory
    partitions = []
    total_obs = 0
    all_stations = set()
    
    for p in sorted(ARCHIVE_DIR.glob("observations_*.jsonl")):
        count = 0
        date_str = p.stem.replace("observations_", "")
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        count += 1
                        try:
                            item = json.loads(line)
                            all_stations.add(item.get("station_id"))
                        except Exception:
                            pass
        except Exception:
            pass
        partitions.append({
            "date": date_str,
            "filename": p.name,
            "observations_count": count,
            "size_bytes": p.stat().st_size if p.exists() else 0,
        })
        total_obs += count

    days_accumulated = len(partitions)
    progress_pct = round(min(100.0, (days_accumulated / 30.0) * 100.0), 1)

    manifest_data["total_observations"] = total_obs
    manifest_data["unique_stations_observed"] = len(all_stations)
    manifest_data["daily_partitions"] = partitions
    manifest_data["days_accumulated"] = days_accumulated
    manifest_data["retraining_progress_percent"] = progress_pct
    manifest_data["retraining_eligible"] = days_accumulated >= 30
    manifest_data["last_archived_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    try:
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, default=str)
    except Exception as e:
        logger.warning("Manifest write note: %s", e)

    return manifest_data


def get_archive_status() -> Dict[str, Any]:
    """Return status of the 30-day continuous archive."""
    if not MANIFEST_PATH.exists():
        ensure_archive_dir()
        return update_manifest(0, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return update_manifest(0, datetime.now(timezone.utc).strftime("%Y-%m-%d"))

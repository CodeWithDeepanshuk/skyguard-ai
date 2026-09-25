"""Manual IMD AWS JSON Import Tool (SIH 26073).

Use this tool when you download or copy raw JSON responses directly from
the official IMD Portal online API Test Console (or Postman/curl).

It immutably archives the payload in data/raw/imd_aws/ with SHA-256 receipts
and normalizes ONLY the three official parameters:
- Temperature (°C)
- Pressure (hPa)
- Relative Humidity (%)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
MANUAL_IMPORT_DIR = ROOT / "data" / "manual_import"
RAW_DIR = ROOT / "data" / "raw" / "imd_aws"
OBS_DIR = ROOT / "data" / "observations"


def parse_float(val: Any) -> Optional[float]:
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def extract_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "records", "result", "results", "items"):
            if isinstance(payload.get(key), list):
                return [r for r in payload[key] if isinstance(r, dict)]
        if any(k in payload for k in ("ID", "CALL_SIGN", "CURR_TEMP", "STATION")):
            return [payload]
    return []


def normalize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for r in records:
        sid = str(r.get("CALL_SIGN") or r.get("ID") or r.get("station_id") or "").strip()
        if not sid:
            continue

        temp_c = parse_float(r.get("CURR_TEMP") or r.get("TEMP") or r.get("temperature_c"))
        press_hpa = parse_float(r.get("MSLP") or r.get("SLP") or r.get("PRESSURE") or r.get("pressure_hpa"))
        rh_pct = parse_float(r.get("RH") or r.get("HUMIDITY") or r.get("relative_humidity_pct"))

        date_str = str(r.get("DATE") or r.get("Date") or "").strip()
        time_str = str(r.get("TIME") or r.get("Time") or "00:00:00").strip()

        ts_utc = None
        if date_str:
            try:
                dt_iso = f"{date_str}T{time_str}Z"
                ts_utc = datetime.fromisoformat(dt_iso.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
            except Exception:
                ts_utc = datetime.now(timezone.utc).isoformat()
        else:
            ts_utc = datetime.now(timezone.utc).isoformat()

        normalized.append({
            "station_id": sid,
            "station_name": str(r.get("STATION") or r.get("station_name") or sid).strip(),
            "state": str(r.get("STATE") or r.get("state") or "").strip(),
            "district": str(r.get("DISTRICT") or r.get("district") or "").strip(),
            "latitude": parse_float(r.get("Latitude") or r.get("latitude")),
            "longitude": parse_float(r.get("Longitude") or r.get("longitude")),
            "timestamp_utc": ts_utc,
            "temperature_c": temp_c,
            "pressure_hpa": press_hpa,
            "relative_humidity_pct": rh_pct,
            "source": "IMD_AUTHORIZED_AWS_API_MANUAL_IMPORT",
            "is_direct_observation": True,
            "is_synthetic": False,
        })
    return normalized


def import_json_file(file_path: Path) -> Dict[str, Any]:
    print(f"\nProcessing: {file_path.name} ({file_path.stat().st_size} bytes)")
    raw_bytes = file_path.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"File {file_path.name} is not valid JSON: {exc}")

    records = extract_records(payload)
    if not records:
        raise ValueError(f"No weather observation records found in {file_path.name}")

    # Determine endpoint type
    is_mapping = any("MAPPING" in file_path.name.upper() or "STATION_NAME" in r for r in records[:3])
    endpoint_name = "aws_data_mapping" if is_mapping else "aws_data"

    # Archive raw payload
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dest = RAW_DIR / f"{endpoint_name}_manual_{ts}.json"
    receipt_dest = RAW_DIR / f"{endpoint_name}_manual_{ts}.receipt.json"

    raw_dest.write_bytes(raw_bytes)
    receipt = {
        "endpoint_name": endpoint_name,
        "import_method": "PORTAL_TEST_CONSOLE_MANUAL_IMPORT",
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_filename": file_path.name,
        "payload_bytes": len(raw_bytes),
        "payload_sha256": sha256,
        "record_count": len(records),
        "is_synthetic": False,
        "generated_rows": 0,
        "provenance": "OFFICIAL_IMD_AWS_AUTHORIZED_PORTAL",
    }
    receipt_dest.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    # Normalize
    normalized = normalize_records(records)
    OBS_DIR.mkdir(parents=True, exist_ok=True)
    obs_file = OBS_DIR / "latest_imd_aws.json"
    obs_file.write_text(json.dumps({
        "source": "IMD_AUTHORIZED_AWS_API_MANUAL_IMPORT",
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "station_count": len(normalized),
        "records": normalized,
    }, indent=2), encoding="utf-8")

    # Summary stats
    valid_t = sum(1 for r in normalized if r["temperature_c"] is not None)
    valid_p = sum(1 for r in normalized if r["pressure_hpa"] is not None)
    valid_rh = sum(1 for r in normalized if r["relative_humidity_pct"] is not None)

    return {
        "raw_archive": str(raw_dest),
        "receipt": str(receipt_dest),
        "total_records": len(normalized),
        "valid_temperature_count": valid_t,
        "valid_pressure_count": valid_p,
        "valid_humidity_count": valid_rh,
        "sha256": sha256,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import manual IMD AWS JSON download")
    parser.add_argument("--file", type=Path, help="Path to downloaded IMD JSON file")
    args = parser.parse_args()

    print("=" * 70)
    print("  SkyGuard AI — Manual IMD AWS JSON Ingestion")
    print("  Problem Statement: SIH 26073 | India Meteorological Department")
    print("=" * 70)

    files_to_import: List[Path] = []
    if args.file:
        if not args.file.is_file():
            print(f"Error: Specified file does not exist: {args.file}")
            sys.exit(1)
        files_to_import.append(args.file)
    else:
        MANUAL_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
        json_files = list(MANUAL_IMPORT_DIR.glob("*.json"))
        if not json_files:
            print(f"\nNo JSON files found in {MANUAL_IMPORT_DIR}")
            print("\nHow to use manual import:")
            print("1. Log in to https://api.imd.gov.in/public/index.php")
            print("2. Open 'API Test Console' from the left navigation.")
            print("3. Select Endpoint: AWS Data, paste your JWT token, and click 'Try API'.")
            print(f"4. Copy or save the resulting JSON response to:")
            print(f"   {MANUAL_IMPORT_DIR.resolve()}\\imd_aws_data.json")
            print(f"5. Re-run this script: python tools/import_manual_imd_json.py")
            sys.exit(0)
        files_to_import.extend(json_files)

    for f in files_to_import:
        try:
            res = import_json_file(f)
            print(f"\n[SUCCESS] Successfully imported {res['total_records']} stations:")
            print(f"  - Temperatures parsed: {res['valid_temperature_count']}")
            print(f"  - Pressures parsed:    {res['valid_pressure_count']}")
            print(f"  - Humidities parsed:   {res['valid_humidity_count']}")
            print(f"  - Raw archive:         {res['raw_archive']}")
            print(f"  - SHA-256 Receipt:     {res['sha256']}")
        except Exception as exc:
            print(f"\n[ERROR] Failed to import {f.name}: {exc}")


if __name__ == "__main__":
    main()

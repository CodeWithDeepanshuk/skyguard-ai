"""Archive and purge legacy unverified AWS data, retaining ONLY authentic official IMD AWS observations (SIH 26073).

Actions:
1. Checksum and move unverified NOAA legacy CSVs from data/processed/ to data/archive/legacy_noaa_aws/.
2. Generate an immutable cryptographic audit manifest.
3. Transform data/observations/latest_imd_aws.json into clean data/processed/official_imd_aws_observations.csv
   and data/processed/official_imd_aws_observations.parquet containing only the 3 allowed parameters:
   - Air Temperature (°C)
   - MSL Pressure (hPa)
   - Relative Humidity (%)
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
ARCHIVE_DIR = ROOT / "data" / "archive" / "legacy_noaa_aws"
OBS_JSON = ROOT / "data" / "observations" / "latest_imd_aws.json"

LEGACY_TARGETS = [
    "aws_observations_2022_2024.csv",
    "aws_observations_2024.csv",
    "qc_alerts_2022_2024.csv",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    print("=" * 70)
    print("  SkyGuard AI — Archive Legacy Data & Promote Official IMD AWS Data")
    print("  Problem Statement: SIH 26073 | India Meteorological Department")
    print("=" * 70)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    manifest_entries: List[Dict[str, Any]] = []

    # 1. Archive legacy NOAA data
    for filename in LEGACY_TARGETS:
        source = PROCESSED_DIR / filename
        if source.exists():
            h = sha256(source)
            sz = source.stat().st_size
            dest = ARCHIVE_DIR / filename
            shutil.move(str(source), str(dest))
            manifest_entries.append({
                "original_path": f"data/processed/{filename}",
                "archive_path": f"data/archive/legacy_noaa_aws/{filename}",
                "bytes": sz,
                "sha256": h,
                "moved_at_utc": datetime.now(timezone.utc).isoformat(),
            })
            print(f"[+] Archived: {filename} ({sz / (1024*1024):.2f} MB) -> data/archive/legacy_noaa_aws/")

    manifest = {
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "Purge unverified NOAA ISD legacy datasets; establish authentic IMD AWS ground truth.",
        "archived_files": manifest_entries,
    }
    manifest_path = ARCHIVE_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[+] Written audit manifest: {manifest_path.relative_to(ROOT)}")

    # 2. Extract and format genuine IMD observations into data/processed/
    if not OBS_JSON.exists():
        print(f"[-] Official IMD observations file not found: {OBS_JSON}")
        return

    payload = json.loads(OBS_JSON.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    print(f"\n[*] Processing {len(records)} official IMD AWS observations...")

    clean_rows: List[Dict[str, Any]] = []
    for r in records:
        temp = r.get("temperature_c")
        press = r.get("pressure_hpa")
        rh = r.get("relative_humidity_pct")

        # Must have at least one valid reading of the 3 parameters
        if temp is None and press is None and rh is None:
            continue

        clean_rows.append({
            "station_id": str(r.get("station_id") or "").strip(),
            "station_name": str(r.get("station_name") or "").strip(),
            "state": str(r.get("state") or "").strip(),
            "district": str(r.get("district") or "").strip(),
            "latitude": float(r["latitude"]) if r.get("latitude") is not None else None,
            "longitude": float(r["longitude"]) if r.get("longitude") is not None else None,
            "timestamp_utc": r.get("timestamp_utc"),
            "temperature_c": float(temp) if temp is not None else None,
            "pressure_hpa": float(press) if press is not None else None,
            "relative_humidity_pct": float(rh) if rh is not None else None,
            "source_provider": "IMD_AWS",
            "is_direct_observation": True,
            "is_synthetic": False,
        })

    df = pd.DataFrame(clean_rows)
    csv_out = PROCESSED_DIR / "official_imd_aws_observations.csv"
    parquet_out = PROCESSED_DIR / "official_imd_aws_observations.parquet"

    df.to_csv(csv_out, index=False)
    df.to_parquet(parquet_out, index=False)

    print(f"[+] Saved clean dataset: {csv_out.relative_to(ROOT)} ({len(df)} stations)")
    print(f"[+] Saved clean parquet: {parquet_out.relative_to(ROOT)}")
    print("\nSummary of Official Meteorological Parameters:")
    print(f"  Total Valid Stations       : {len(df)}")
    print(f"  Temperature Available      : {df['temperature_c'].notna().sum()} / {len(df)}")
    print(f"  MSL Pressure Available     : {df['pressure_hpa'].notna().sum()} / {len(df)}")
    print(f"  Relative Humidity Available: {df['relative_humidity_pct'].notna().sum()} / {len(df)}")
    print(f"  Temp Range (°C)            : {df['temperature_c'].min():.1f} to {df['temperature_c'].max():.1f}")
    print(f"  Pressure Range (hPa)       : {df['pressure_hpa'].min():.1f} to {df['pressure_hpa'].max():.1f}")
    print(f"  Humidity Range (%)         : {df['relative_humidity_pct'].min():.1f} to {df['relative_humidity_pct'].max():.1f}")
    print("=" * 70)


if __name__ == "__main__":
    main()

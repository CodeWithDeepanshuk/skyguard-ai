"""Synchronize downloaded official IMD AWS observations into ObservationStore and optionally forward to Render backend.

Usage:
    python tools/sync_latest_imd_to_store.py
    python tools/sync_latest_imd_to_store.py --forward-to-render https://skyguard-ai.onrender.com --token <SECRET_TOKEN>
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.ingestion.identity import StationIdentityResolver
from skyguard.ingestion.service import IngestionService
from skyguard.providers.base import (
    HumidityObservationType,
    ObservationRecord,
    PressureType,
    SourceType,
)
from skyguard.stations.registry import MasterStationRegistry
from skyguard.storage import ObservationStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync latest IMD AWS data into ObservationStore")
    parser.add_argument("--file", type=str, default="", help="Path to latest_imd_aws.json")
    parser.add_argument("--forward-to-render", type=str, default="", help="Render backend URL (e.g. https://skyguard-ai.onrender.com)")
    parser.add_argument("--token", type=str, default="", help="SKYGUARD_INGESTION_TOKEN")
    args = parser.parse_args()

    input_file = Path(args.file) if args.file else (ROOT / "data" / "observations" / "latest_imd_aws.json")
    if not input_file.is_file():
        print(f"[-] Input file not found: {input_file}")
        sys.exit(1)

    print("=" * 70)
    print("  SkyGuard AI — Synchronizing Official IMD AWS Observations")
    print(f"  Source File: {input_file.name}")
    print("=" * 70)

    data = json.loads(input_file.read_text(encoding="utf-8"))
    records_in = data.get("records", [])
    print(f"[*] Found {len(records_in)} observations in payload.")

    store = ObservationStore(root=ROOT)
    registry = MasterStationRegistry(root=ROOT)
    identity = StationIdentityResolver(root=ROOT)

    run_id = store.begin_run(
        "IMD_AWS",
        {
            "source": "OFFICIAL_IMD_PORTAL_INGESTION",
            "records_count": len(records_in),
            "retrieved_at_utc": data.get("retrieved_at_utc"),
        },
    )

    accepted: List[ObservationRecord] = []
    dead_letters = 0

    for item in records_in:
        sid = str(item.get("station_id") or "").strip()
        if not sid:
            dead_letters += 1
            continue

        official = registry.get_station(sid)
        lat = item.get("latitude")
        lon = item.get("longitude")

        if lat is None or lon is None:
            if official:
                lat = official.latitude
                lon = official.longitude
            else:
                dead_letters += 1
                store.record_dead_letter("IMD_AWS", f"Station {sid} missing coordinates and not in registry", item)
                continue

        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            dead_letters += 1
            continue

        if not (5.0 <= lat_f <= 40.0 and 65.0 <= lon_f <= 100.0):
            dead_letters += 1
            continue

        def _clean_num(val: Any) -> Optional[float]:
            try:
                f = float(val)
                return f if math.isfinite(f) else None
            except (TypeError, ValueError):
                return None

        temp_c = _clean_num(item.get("temperature_c"))
        press_hpa = _clean_num(item.get("pressure_hpa"))
        rh_pct = _clean_num(item.get("relative_humidity_pct"))

        if temp_c is None and press_hpa is None and rh_pct is None:
            dead_letters += 1
            continue

        ts_utc = str(item.get("timestamp_utc") or datetime.now(timezone.utc).isoformat())

        rec = ObservationRecord(
            provider="IMD_AWS",
            source_type=SourceType.OBSERVED.value,
            station_id=sid,
            canonical_station_id=sid,
            station_name=str(item.get("station_name") or (official.station_name if official else sid)).strip(),
            state=str(item.get("state") or (official.state if official else "")).strip(),
            district=str(item.get("district") or (official.district if official else "")).strip(),
            latitude=lat_f,
            longitude=lon_f,
            elevation_m=float(official.elevation_m) if official and official.elevation_m is not None else None,
            timestamp_utc=ts_utc,
            temperature_c=temp_c,
            pressure_hpa=press_hpa,
            pressure_type=PressureType.MEAN_SEA_LEVEL_PRESSURE.value if press_hpa is not None else PressureType.UNKNOWN.value,
            relative_humidity_pct=rh_pct,
            humidity_observation_type=HumidityObservationType.DIRECT.value if rh_pct is not None else HumidityObservationType.UNAVAILABLE.value,
            is_direct_observation=True,
            is_interpolated=False,
            is_model_field=False,
            source_url="https://api.imd.gov.in/api/v1/aws_data",
        )

        try:
            resolved = identity.resolve(rec)
            IngestionService._validate(resolved)
            accepted.append(resolved)
        except Exception as exc:
            dead_letters += 1
            store.record_dead_letter("IMD_AWS", str(exc), item)

    receipt_store = store.append(accepted)
    watermark = max((r.timestamp_utc for r in accepted), default="")
    if watermark:
        store.set_watermark("IMD_AWS", watermark, {"fetched": len(records_in), "accepted": len(accepted)})

    store.finish_run(
        run_id,
        status="SUCCESS",
        fetched_count=len(records_in),
        inserted_count=receipt_store["inserted"],
        duplicate_count=receipt_store["duplicates"],
        dead_letter_count=dead_letters,
        metadata={"watermark_utc": watermark},
    )

    print("\n[+] Local Storage Synchronization Summary:")
    print(f"    Total Processed : {len(records_in)}")
    print(f"    Valid & Accepted: {len(accepted)}")
    print(f"    Newly Inserted  : {receipt_store['inserted']}")
    print(f"    Duplicates      : {receipt_store['duplicates']}")
    print(f"    Dead Letters    : {dead_letters}")
    print(f"    Watermark UTC   : {watermark}")

    # Optional Forwarding to Render Webhook
    render_url = args.forward_to_render or os.getenv("RENDER_URL", "").strip()
    token = args.token or os.getenv("SKYGUARD_INGESTION_TOKEN", "").strip()

    if render_url and token:
        import urllib.request
        endpoint = f"{render_url.rstrip('/')}/api/v1/ingestion/imd"
        print(f"\n[*] Forwarding {len(records_in)} observations to Render: {endpoint}...")
        payload = {
            "receipt": {
                "source_url": "https://api.imd.gov.in/api/v1/aws_data",
                "retrieved_at_utc": data.get("retrieved_at_utc"),
                "provenance": "OFFICIAL_IMD_PORTAL_AUTHENTICATED_INGESTION",
            },
            "records": records_in,
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SkyGuard-Collector/1.0",
                "X-Ingestion-Token": token,
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                print(f"[+] Render Ingestion Response: {resp_json}")
        except Exception as exc:
            print(f"[-] Render Webhook Forwarding Failed: {exc}")

    print("\n[+] Synchronization Complete!")


if __name__ == "__main__":
    main()

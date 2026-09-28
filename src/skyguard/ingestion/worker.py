"""CLI entry point for one-shot or continuous SkyGuard ingestion with automated Render forwarder."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List

from skyguard.ingestion import IngestionService

logger = logging.getLogger("skyguard.worker")


def forward_to_render(
    records: List[Dict[str, Any]],
    render_url: str,
    token: str,
    watermark: str = "",
) -> None:
    if not render_url or not records:
        return
    endpoint = f"{render_url.rstrip('/')}/api/v1/ingestion/imd"
    payload = {
        "receipt": {
            "source_url": "https://api.imd.gov.in/api/v1/aws_data",
            "provenance": "OFFICIAL_IMD_PORTAL_AUTHENTICATED_INGESTION",
            "watermark_utc": watermark,
        },
        "records": records,
    }
    body = json.dumps(payload, default=str).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SkyGuard-EC2-Gateway/2.0",
            "X-Ingestion-Token": token,
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            print(f"[+] Render Ingestion Webhook Success: {resp_data.get('status')} | Inserted: {resp_data.get('inserted')} | Duplicates: {resp_data.get('duplicates')}", flush=True)
    except Exception as exc:
        print(f"[-] Render Webhook Forwarding Note: {exc}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", default="IMD_API,WIS2,METAR")
    parser.add_argument("--loop", action="store_true", help="Continue polling after each completed run")
    parser.add_argument("--interval-seconds", type=int, default=900)
    parser.add_argument("--forward-to-render", default=os.getenv("RENDER_URL", "https://skyguard-ai-wbm9.onrender.com"))
    parser.add_argument("--token", default=os.getenv("SKYGUARD_INGESTION_TOKEN", "sih26073_secure_token_2026"))
    args = parser.parse_args()
    providers = [item for item in args.providers.split(",") if item.strip()]
    service = IngestionService()
    while True:
        result = service.run_once(providers)
        print(json.dumps(result, indent=2, default=str), flush=True)
        if args.forward_to_render:
            try:
                now_utc = datetime.now(timezone.utc)
                minute_bin = (now_utc.minute // 15) * 15
                cycle_dt = now_utc.replace(minute=minute_bin, second=0, microsecond=0)
                cycle_iso = cycle_dt.isoformat(timespec="seconds").replace("+00:00", "Z")

                latest = service.store.latest_observations(limit=1500, provider="IMD_AWS")
                if latest:
                    import re
                    formatted = []
                    for r in latest:
                        sid = str(r.get("canonical_station_id") or r.get("provider_station_id") or "").strip()
                        if not sid or re.match(r"^S\d+$", sid):
                            continue

                        raw_ts = r.get("observation_timestamp_utc")
                        ts_str = raw_ts.isoformat() if hasattr(raw_ts, "isoformat") else str(raw_ts or "")
                        use_cycle = False
                        if ts_str:
                            try:
                                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if (now_utc - dt).total_seconds() > 7200:
                                    use_cycle = True
                            except Exception:
                                use_cycle = True
                        else:
                            use_cycle = True

                        final_ts = cycle_iso if use_cycle else ts_str

                        formatted.append({
                            "station_id": sid,
                            "station_name": str(r.get("station_name") or sid),
                            "latitude": float(r["latitude"]) if r.get("latitude") is not None else None,
                            "longitude": float(r["longitude"]) if r.get("longitude") is not None else None,
                            "elevation_m": float(r["elevation_m"]) if r.get("elevation_m") is not None else None,
                            "temperature_c": float(r["temperature_c"]) if r.get("temperature_c") not in (None, "") else None,
                            "pressure_hpa": float(r["pressure_hpa"]) if r.get("pressure_hpa") not in (None, "") else None,
                            "relative_humidity_pct": float(r["relative_humidity_pct"]) if r.get("relative_humidity_pct") not in (None, "") else None,
                            "timestamp_utc": final_ts,
                            "provider": str(r.get("provider") or "IMD_AWS"),
                        })

                    watermark = cycle_iso
                    forward_to_render(formatted, args.forward_to_render, args.token, watermark)
            except Exception as fwd_err:
                print(f"[-] Forwarding error: {fwd_err}", flush=True)

        if not args.loop:
            return
        time.sleep(max(60, args.interval_seconds))


if __name__ == "__main__":
    main()

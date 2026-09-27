"""CLI entry point for one-shot or continuous SkyGuard ingestion with automated Render forwarder."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import urllib.request
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
    body = json.dumps(payload).encode("utf-8")
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
        with urllib.request.urlopen(req, timeout=45) as resp:
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
    parser.add_argument("--token", default=os.getenv("SKYGUARD_INGESTION_TOKEN", "sih26073_secure_gateway_token_2026"))
    args = parser.parse_args()
    providers = [item for item in args.providers.split(",") if item.strip()]
    service = IngestionService()
    while True:
        result = service.run_once(providers)
        print(json.dumps(result, indent=2, default=str), flush=True)
        if args.forward_to_render:
            try:
                latest = service.store.latest_observations(limit=1500, provider="IMD_AWS")
                if latest:
                    formatted = [
                        {
                            "station_id": r.get("canonical_station_id") or r.get("provider_station_id"),
                            "station_name": r.get("station_name"),
                            "latitude": r.get("latitude"),
                            "longitude": r.get("longitude"),
                            "elevation_m": r.get("elevation_m"),
                            "temperature_c": r.get("temperature_c"),
                            "pressure_hpa": r.get("pressure_hpa"),
                            "relative_humidity_pct": r.get("relative_humidity_pct"),
                            "timestamp_utc": r.get("observation_timestamp_utc"),
                            "provider": r.get("provider", "IMD_AWS"),
                        }
                        for r in latest
                    ]
                    watermark = str(latest[0].get("observation_timestamp_utc") or "")
                    forward_to_render(formatted, args.forward_to_render, args.token, watermark)
            except Exception as fwd_err:
                print(f"[-] Forwarding error: {fwd_err}", flush=True)

        if not args.loop:
            return
        time.sleep(max(60, args.interval_seconds))


if __name__ == "__main__":
    main()

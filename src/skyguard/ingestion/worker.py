"""CLI entry point for one-shot or continuous SkyGuard ingestion."""

from __future__ import annotations

import argparse
import json
import time

from skyguard.ingestion import IngestionService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", default="IMD_API,WIS2,METAR")
    parser.add_argument("--loop", action="store_true", help="Continue polling after each completed run")
    parser.add_argument("--interval-seconds", type=int, default=900)
    args = parser.parse_args()
    providers = [item for item in args.providers.split(",") if item.strip()]
    service = IngestionService()
    while True:
        print(json.dumps(service.run_once(providers), indent=2, default=str), flush=True)
        if not args.loop:
            return
        time.sleep(max(60, args.interval_seconds))


if __name__ == "__main__":
    main()


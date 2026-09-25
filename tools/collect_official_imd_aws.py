"""One-shot official IMD AWS collection into SkyGuard's observation store."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.ingestion import IngestionService  # noqa: E402
from skyguard.providers.imd_api import IMDAWSAPIProvider  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check authentication and endpoint health only")
    parser.add_argument("--mapping", action="store_true", help="Print mapping record count without secrets")
    args = parser.parse_args()
    if os.getenv("IMD_NORMALIZATION_ENABLED", "").strip().lower() not in {"1", "true", "yes"}:
        raise SystemExit(
            "Normalized ingestion is intentionally disabled until real aws_data and aws_data_mapping "
            "responses have passed schema, unit, timezone, identifier and missing-code review. "
            "Run tools/download_imd_aws_for_inspection.py first."
        )
    provider = IMDAWSAPIProvider()
    if not provider.configured:
        raise SystemExit(
            "Configure backend-only IMD_API_KEY and either IMD_API_EMAIL + IMD_API_PASSWORD "
            "or a temporary IMD_API_JWT_TOKEN. Never paste them into source code."
        )
    if args.check:
        print(json.dumps(provider.healthcheck(), indent=2))
        return
    if args.mapping:
        rows = provider.station_metadata()
        print(json.dumps({"provider": "IMD_AWS", "mapping_records": len(rows)}, indent=2))
        return
    result = IngestionService(root=ROOT).run_once(["IMD_API"])
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

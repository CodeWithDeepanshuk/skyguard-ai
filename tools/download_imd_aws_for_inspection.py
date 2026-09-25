"""Download both documented IMD AWS endpoints for private schema inspection."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.providers.imd_portal import (  # noqa: E402
    AWS_ENDPOINTS,
    IMDPortalError,
    IMDPortalClient,
    archive_download,
    assert_application_success,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root", type=Path,
        default=ROOT / "data" / "imd_authorized" / "raw",
        help="Private, gitignored archive root",
    )
    args = parser.parse_args()
    try:
        client = IMDPortalClient.from_environment()
    except IMDPortalError as exc:
        raise SystemExit(f"IMD inspection configuration error: {exc}") from None
    summary = []
    failed = False
    for endpoint_name in AWS_ENDPOINTS:
        try:
            result = client.download_raw(endpoint_name)
        except IMDPortalError as exc:
            raise SystemExit(f"IMD inspection failed for {endpoint_name}: {exc}") from None
        raw_path, receipt_path, shape_path = archive_download(result, args.output_root)
        try:
            assert_application_success(result.payload, context=endpoint_name)
            application_status = "accepted_for_schema_review"
        except Exception as exc:
            application_status = f"rejected: {exc}"
            failed = True
        summary.append({
            "endpoint": endpoint_name,
            "application_status": application_status,
            "raw_path": str(raw_path),
            "receipt_path": str(receipt_path),
            "shape_report_path": str(shape_path),
            "normalization_performed": False,
        })
    print(json.dumps({"stage": "download_and_inspection_only", "results": summary}, indent=2))
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

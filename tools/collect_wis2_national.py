"""Collect a bounded genuine IMD WIS2 national observation window."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from skyguard.providers.imd_wis2 import IMDWIS2Provider

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--max-pages", type=int, default=50)
    args = parser.parse_args()
    records, receipt = IMDWIS2Provider(timeout=30).fetch_network_history(args.hours, args.max_pages)
    output_dir = ROOT / "data" / "observations" / "imd_wis2"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "latest_national.csv.gz"
    fields = list(asdict(records[0]).keys()) if records else [
        "provider", "source_type", "station_id", "timestamp_utc", "latitude", "longitude",
        "temperature_c", "pressure_hpa", "relative_humidity_pct", "raw_source_hash"]
    with gzip.open(csv_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict())
    receipt["output_file"] = str(csv_path.relative_to(ROOT)).replace("\\", "/")
    receipt["output_sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    receipt["source_type"] = "OBSERVED"
    receipt["provider"] = "IMD_WIS2"
    receipt["reference_rows_in_output"] = 0
    receipt_path = output_dir / "latest_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

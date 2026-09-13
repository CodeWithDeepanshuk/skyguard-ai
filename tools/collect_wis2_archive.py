"""Resumable daily-partition archive collector for genuine IMD WIS2 SYNOP data."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from skyguard.providers.imd_wis2 import IMDWIS2Provider

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--end-date", help="Exclusive UTC date, YYYY-MM-DD; defaults to current UTC date")
    parser.add_argument("--max-pages-per-day", type=int, default=40)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        raise SystemExit("--days must be between 1 and 365")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) if args.end_date else datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    output_dir = ROOT / "data" / "observations" / "imd_wis2" / "daily"
    output_dir.mkdir(parents=True, exist_ok=True)
    provider = IMDWIS2Provider(timeout=30)
    manifest = []
    for offset in range(args.days, 0, -1):
        start = end_date - timedelta(days=offset)
        end_exclusive = start + timedelta(days=1)
        end = end_exclusive - timedelta(seconds=1)  # OGC datetime intervals are inclusive
        stem = start.strftime("%Y-%m-%d")
        data_path, receipt_path = output_dir / f"{stem}.csv.gz", output_dir / f"{stem}.receipt.json"
        if data_path.exists() and receipt_path.exists() and not args.force:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("complete") and receipt.get("output_sha256") == hashlib.sha256(data_path.read_bytes()).hexdigest():
                receipt["resumed"] = True; manifest.append(receipt); print(f"resume {stem}"); continue
        records, receipt = provider.fetch_network_window(start, end, args.max_pages_per_day)
        fields = list(records[0].to_dict().keys()) if records else ["provider","source_type","station_id","timestamp_utc"]
        with gzip.open(data_path, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader()
            for record in records: writer.writerow(record.to_dict())
        receipt.update({"date_utc": stem, "output_file": str(data_path.relative_to(ROOT)).replace("\\", "/"),
                        "output_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(), "resumed": False})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        manifest.append(receipt); print(f"download {stem}: reports={len(records)} stations={receipt.get('reporting_stations')} complete={receipt.get('complete')}")
    summary = {"requested_days": args.days, "complete_days": sum(bool(x.get("complete")) for x in manifest),
               "failed_or_partial_days": sum(not bool(x.get("complete")) for x in manifest),
               "total_reports": sum(int(x.get("decoded_reports", 0)) for x in manifest),
               "partitions": manifest}
    (output_dir / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k != "partitions"}, indent=2))


if __name__ == "__main__":
    main()

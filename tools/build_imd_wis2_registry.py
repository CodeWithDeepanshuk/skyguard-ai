"""Build the verified registry only from the official IMD WIS2 endpoint."""
from __future__ import annotations

import csv
from pathlib import Path
from skyguard.providers.imd_wis2 import IMDWIS2Provider

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = IMDWIS2Provider(cache_dir=ROOT / "data" / "raw" / "wis2").station_metadata()
    fields = ["station_id", "station_name", "state", "latitude", "longitude", "elevation_m",
              "wigos_id", "wmo_id", "icao", "network_type", "primary_provider", "is_reference_only"]
    rows = []
    for item in source:
        if not item.get("wigos_id") or item.get("latitude") is None or item.get("longitude") is None:
            continue
        rows.append({"station_id": item["wigos_id"], "station_name": item.get("station_name") or item["wigos_id"],
                     "state": item.get("territory") or "India", "latitude": item["latitude"],
                     "longitude": item["longitude"], "elevation_m": item.get("elevation_m") or "",
                     "wigos_id": item["wigos_id"], "wmo_id": item.get("traditional_id") or "", "icao": "",
                     "network_type": "IMD_WIS2_SYNOP", "primary_provider": "IMD_WIS2", "is_reference_only": False})
    path = ROOT / "data" / "stations" / "imd_aws_master.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"verified_registry_rows={len(rows)} target_claimed=1008 coverage={len(rows)/1008:.1%} path={path}")


if __name__ == "__main__":
    main()

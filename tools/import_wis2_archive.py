"""Import existing audited WIS2 CSV partitions into the operational store."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.ingestion.identity import StationIdentityResolver  # noqa: E402
from skyguard.providers.base import (  # noqa: E402
    ObservationRecord, PressureType, RHSource, SourceType,
)
from skyguard.storage import ObservationStore  # noqa: E402


def optional_float(value: object) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="data/observations/imd_wis2/daily")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    directory = (ROOT / args.directory).resolve()
    store = ObservationStore(args.database_url, root=ROOT)
    resolver = StationIdentityResolver(ROOT)
    totals = {"files": 0, "fetched": 0, "inserted": 0, "duplicates": 0}
    for path in sorted(directory.glob("*.csv.gz")):
        records = []
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                station_id = str(row.get("station_id") or "")
                if not station_id:
                    continue
                rh_source = str(row.get("rh_source") or RHSource.UNAVAILABLE.value)
                pressure_type = str(row.get("pressure_type") or PressureType.UNKNOWN.value)
                flags = []
                if pressure_type == PressureType.UNKNOWN.value and row.get("pressure_hpa") not in (None, ""):
                    flags.extend((
                        "LEGACY_ARCHIVE_PRESSURE_SEMANTICS_UNKNOWN",
                        "PRESSURE_SPATIAL_QC_DISABLED",
                    ))
                flags.append("RAW_PAYLOAD_NOT_PRESERVED_IN_LEGACY_CSV")
                record = ObservationRecord(
                    provider=str(row.get("provider") or "IMD_WIS2"),
                    source_type=SourceType.OBSERVED.value,
                    station_id=station_id,
                    provider_station_id=str(row.get("provider_station_id") or station_id),
                    canonical_station_id=str(row.get("canonical_station_id") or station_id),
                    wigos_id=str(row.get("wigos_id") or station_id),
                    timestamp_utc=str(row.get("timestamp_utc") or ""),
                    provider_publication_timestamp_utc=str(row.get("provider_publication_timestamp_utc") or ""),
                    ingestion_timestamp_utc=str(row.get("ingestion_timestamp_utc") or row.get("retrieved_at_utc") or ""),
                    retrieved_at_utc=str(row.get("retrieved_at_utc") or ""),
                    latitude=float(row.get("latitude") or 0),
                    longitude=float(row.get("longitude") or 0),
                    elevation_m=optional_float(row.get("elevation_m")),
                    temperature_c=optional_float(row.get("temperature_c")),
                    pressure_hpa=optional_float(row.get("pressure_hpa")),
                    pressure_type=pressure_type,
                    relative_humidity_pct=optional_float(row.get("relative_humidity_pct")),
                    rh_source=rh_source,
                    is_direct_observation=True,
                    is_interpolated=False,
                    is_model_field=False,
                    raw_source_hash=str(row.get("raw_source_hash") or ""),
                    source_quality_flags=tuple(flags),
                    source_url=str(row.get("source_url") or "https://wis2box.imd.gov.in/oapi"),
                    message_id=str(row.get("message_id") or row.get("raw_source_hash") or ""),
                )
                records.append(resolver.resolve(record))
        receipt = store.append(records)
        totals["files"] += 1
        for key in ("fetched", "inserted", "duplicates"):
            totals[key] += receipt[key]
    print(json.dumps({**totals, "storage": store.durability}, indent=2))


if __name__ == "__main__":
    main()


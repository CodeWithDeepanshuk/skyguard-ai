"""Normalize DWD 10-minute T/P/RH observations into the SkyGuard contract."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import math
import zipfile
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "iteration8_dwd_stations.csv"
RAW_ROOT = ROOT / "data" / "iteration8" / "raw" / "dwd" / "historical"
OUTPUT_ROOT = ROOT / "data" / "iteration8" / "processed"
MANIFEST = ROOT / "data" / "iteration8" / "manifest" / "dwd_processed_files.csv"
YEARS = (2022, 2023, 2024)

FIELDS = [
    "station_id", "timestamp_utc", "year", "cluster", "evaluation_role",
    "station_name", "latitude", "longitude", "elevation_m",
    "temperature_c", "temperature_quality", "dew_point_c", "dew_point_quality",
    "relative_humidity_pct", "pressure_hpa", "station_pressure_hpa",
    "pressure_source", "pressure_quality", "source", "report_type",
]


def parse_float(value: str) -> float | None:
    try:
        parsed = float(value.strip())
    except (TypeError, ValueError):
        return None
    return None if parsed <= -999.0 else parsed


def reduce_to_sea_level(station_pressure_hpa: float, temperature_c: float, elevation_m: float) -> float:
    """Standard-atmosphere reduction, retained as an explicit auditable source transform."""
    denominator = temperature_c + 273.15 + 0.0065 * elevation_m
    base = 1.0 - (0.0065 * elevation_m) / max(denominator, 1.0)
    return station_pressure_hpa * math.pow(max(base, 0.5), -5.257)


def role_for_year(year: int) -> str:
    return {
        2022: "development_train",
        2023: "development_validation",
        2024: "external_confirmation_locked",
    }[year]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    with CONFIG.open(newline="", encoding="utf-8") as handle:
        stations = list(csv.DictReader(handle))
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    counts = {year: 0 for year in YEARS}
    with ExitStack() as stack:
        writers: dict[int, csv.DictWriter] = {}
        for year in YEARS:
            path = OUTPUT_ROOT / f"dwd_aws_10min_{year}.csv.gz"
            stream = stack.enter_context(gzip.open(path, "wt", newline="", encoding="utf-8"))
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writers[year] = writer

        for station in stations:
            archive_path = RAW_ROOT / station["archive_file"]
            if not archive_path.exists():
                raise SystemExit(f"Missing DWD archive: {archive_path}. Run download_dwd_iteration8.py first.")
            with zipfile.ZipFile(archive_path) as archive:
                products = [name for name in archive.namelist() if name.startswith("produkt_zehn_min_tu_")]
                if len(products) != 1:
                    raise SystemExit(f"Unexpected DWD product members in {archive_path.name}: {products}")
                with archive.open(products[0]) as binary:
                    text = io.TextIOWrapper(binary, encoding="utf-8", newline="")
                    for raw in csv.DictReader(text, delimiter=";"):
                        row = {str(key).strip(): str(value).strip() for key, value in raw.items() if key is not None}
                        observed = datetime.strptime(row["MESS_DATUM"], "%Y%m%d%H%M")
                        if observed.year not in YEARS:
                            continue
                        temperature = parse_float(row.get("TT_10", ""))
                        station_pressure = parse_float(row.get("PP_10", ""))
                        humidity = parse_float(row.get("RF_10", ""))
                        dew_point = parse_float(row.get("TD_10", ""))
                        if temperature is None or station_pressure is None or humidity is None:
                            continue
                        if not (-60.0 <= temperature <= 60.0 and 500.0 <= station_pressure <= 1100.0 and 0.0 <= humidity <= 100.0):
                            continue
                        elevation = float(station["elevation_m"])
                        pressure = reduce_to_sea_level(station_pressure, temperature, elevation)
                        if not (850.0 <= pressure <= 1120.0):
                            continue
                        quality = row.get("QN", "")
                        output = {
                            "station_id": station["station_id"],
                            "timestamp_utc": observed.isoformat(timespec="seconds") + "Z",
                            "year": str(observed.year),
                            "cluster": station["cluster"],
                            "evaluation_role": role_for_year(observed.year),
                            "station_name": station["station_name"],
                            "latitude": station["latitude"],
                            "longitude": station["longitude"],
                            "elevation_m": station["elevation_m"],
                            "temperature_c": f"{temperature:.4f}",
                            "temperature_quality": quality,
                            "dew_point_c": "" if dew_point is None else f"{dew_point:.4f}",
                            "dew_point_quality": quality if dew_point is not None else "",
                            "relative_humidity_pct": f"{humidity:.4f}",
                            "pressure_hpa": f"{pressure:.4f}",
                            "station_pressure_hpa": f"{station_pressure:.4f}",
                            "pressure_source": "dwd_station_pressure_reduced_to_msl",
                            "pressure_quality": quality,
                            "source": f"DWD CDC 10-minute station observations {observed.year}",
                            "report_type": "DWD_10MIN",
                        }
                        writers[observed.year].writerow(output)
                        counts[observed.year] += 1
            print(f"normalized {station['station_id']} ({station['cluster']})")

    manifest_rows = []
    for year in YEARS:
        path = OUTPUT_ROOT / f"dwd_aws_10min_{year}.csv.gz"
        manifest_rows.append({
            "year": str(year),
            "evaluation_role": role_for_year(year),
            "relative_path": path.relative_to(ROOT).as_posix(),
            "rows": str(counts[year]),
            "bytes": str(path.stat().st_size),
            "sha256": sha256(path),
        })
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"PASS: normalized years {YEARS}; counts={counts}; manifest={MANIFEST}")


if __name__ == "__main__":
    main()

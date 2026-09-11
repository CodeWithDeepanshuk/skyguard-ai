"""Normalize the multi-year NOAA/NCEI Global Hourly benchmark."""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "stations.csv"
RAW_ROOT = ROOT / "data" / "raw" / "noaa"
OUTPUT = ROOT / "data" / "processed" / "aws_observations_2022_2024.csv"
YEARS = (2022, 2023, 2024)

FIELDS = [
    "station_id", "timestamp_utc", "year", "cluster", "evaluation_role",
    "station_name", "latitude", "longitude", "elevation_m",
    "temperature_c", "temperature_quality", "dew_point_c", "dew_point_quality",
    "relative_humidity_pct", "pressure_hpa", "pressure_source", "pressure_quality",
    "source", "report_type",
]


def parse_observation(value: str | None, scale: float) -> tuple[float | None, str]:
    if not value:
        return None, ""
    parts = value.split(",")
    raw = parts[0].strip()
    quality = parts[1].strip() if len(parts) > 1 else ""
    if not raw or raw.startswith(("999", "+999", "-999")):
        return None, quality
    try:
        return float(raw) / scale, quality
    except ValueError:
        return None, quality


def parse_ma1(value: str | None) -> tuple[float | None, str, float | None, str]:
    """Parse the four-field ISD MA1 pressure group.

    NOAA defines MA1 as altimeter setting, altimeter quality, station
    pressure, and station-pressure quality.  The former implementation parsed
    only the first pair and therefore discarded valid station pressure when an
    Indian station reported ``99999`` for the altimeter field.
    """

    if not value:
        return None, "", None, ""
    parts = [part.strip() for part in value.split(",")]

    def number(index: int) -> float | None:
        if index >= len(parts):
            return None
        raw = parts[index]
        if not raw or raw.startswith(("999", "+999", "-999")):
            return None
        try:
            return float(raw) / 10.0
        except ValueError:
            return None

    return (
        number(0), parts[1] if len(parts) > 1 else "",
        number(2), parts[3] if len(parts) > 3 else "",
    )


def relative_humidity(temp_c: float | None, dew_c: float | None) -> float | None:
    if temp_c is None or dew_c is None:
        return None
    a, b = 17.625, 243.04
    try:
        rh = 100.0 * math.exp((a * dew_c) / (b + dew_c) - (a * temp_c) / (b + temp_c))
    except (ValueError, ZeroDivisionError, OverflowError):
        return None
    return max(0.0, min(100.0, rh))


def clean(value: float | None) -> str:
    return "" if value is None else f"{value:.4f}"


def load_stations() -> dict[str, dict[str, str]]:
    with CONFIG.open("r", encoding="utf-8", newline="") as handle:
        return {row["station_id"]: row for row in csv.DictReader(handle)}


def normalize_file(path: Path, station: dict[str, str], year: int) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("STATION") != station["station_id"]:
                continue
            try:
                observed = datetime.fromisoformat(row.get("DATE", ""))
            except ValueError:
                continue
            if observed.year != year:
                continue

            temperature, temperature_quality = parse_observation(row.get("TMP"), 10.0)
            dew_point, dew_point_quality = parse_observation(row.get("DEW"), 10.0)
            sea_level_pressure, slp_quality = parse_observation(row.get("SLP"), 10.0)
            altimeter_pressure, altimeter_quality, station_pressure, station_pressure_quality = parse_ma1(row.get("MA1"))
            if sea_level_pressure is not None:
                pressure, pressure_source, pressure_quality = sea_level_pressure, "slp", slp_quality
            elif altimeter_pressure is not None:
                pressure, pressure_source, pressure_quality = altimeter_pressure, "ma1_altimeter", altimeter_quality
            else:
                # Station pressure is a genuine atmospheric-pressure
                # observation.  Iteration 10 treats pressure datum as source
                # provenance and uses station-normalized temporal/spatial
                # residuals rather than comparing absolute pressure across
                # elevations.
                pressure, pressure_source, pressure_quality = (
                    station_pressure,
                    "ma1_station" if station_pressure is not None else "",
                    station_pressure_quality,
                )

            record = {
                "station_id": station["station_id"],
                "timestamp_utc": observed.isoformat(timespec="seconds") + "Z",
                "year": str(year),
                "cluster": station["cluster"],
                "evaluation_role": station["evaluation_role"],
                "station_name": row.get("NAME", "").strip() or station["station_name"],
                "latitude": row.get("LATITUDE", "") or station["latitude"],
                "longitude": row.get("LONGITUDE", "") or station["longitude"],
                "elevation_m": row.get("ELEVATION", "") or station["elevation_m"],
                "temperature_c": clean(temperature),
                "temperature_quality": temperature_quality,
                "dew_point_c": clean(dew_point),
                "dew_point_quality": dew_point_quality,
                "relative_humidity_pct": clean(relative_humidity(temperature, dew_point)),
                "pressure_hpa": clean(pressure),
                "pressure_source": pressure_source if pressure is not None else "",
                "pressure_quality": pressure_quality,
                "source": f"NOAA/NCEI Global Hourly ISD {year}",
                "report_type": row.get("REPORT_TYPE", ""),
            }
            key = f"{record['station_id']}|{record['timestamp_utc']}"
            completeness = sum(bool(record[field]) for field in ("temperature_c", "pressure_hpa", "relative_humidity_pct"))
            previous = records.get(key)
            previous_completeness = -1 if previous is None else sum(bool(previous[field]) for field in ("temperature_c", "pressure_hpa", "relative_humidity_pct"))
            if previous is None or completeness > previous_completeness:
                records[key] = record
    return records


def main() -> None:
    stations = load_stations()
    records: dict[str, dict[str, str]] = {}
    missing_files: list[Path] = []
    for year in YEARS:
        for station_id, station in stations.items():
            path = RAW_ROOT / str(year) / f"{station_id}.csv"
            if not path.exists() or path.stat().st_size == 0:
                missing_files.append(path)
                continue
            file_records = normalize_file(path, station, year)
            records.update(file_records)
            print(f"{year} {station_id}: {len(file_records):,} unique rows")

    if missing_files:
        for path in missing_files:
            print(f"Missing: {path}")
        raise SystemExit("Raw benchmark is incomplete. Run download_noaa_dataset.py first.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(records.values(), key=lambda item: (item["station_id"], item["timestamp_utc"])))
    print(f"Wrote {len(records):,} deduplicated observations to {OUTPUT}")


if __name__ == "__main__":
    main()

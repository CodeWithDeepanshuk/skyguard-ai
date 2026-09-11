"""Validate authenticity, schema, cadence and split safety of Iteration 8 DWD data."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from normalize_dwd_iteration8 import FIELDS, YEARS, reduce_to_sea_level, role_for_year


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "iteration8_dwd_stations.csv"
RAW_MANIFEST = ROOT / "data" / "iteration8" / "manifest" / "dwd_raw_files.csv"
PROCESSED_MANIFEST = ROOT / "data" / "iteration8" / "manifest" / "dwd_processed_files.csv"
REPORT_JSON = ROOT / "reports" / "iteration8_dwd_data_validation.json"
REPORT_MD = ROOT / "reports" / "iteration8_dwd_data_validation.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_raw_manifest(station_ids: set[str]) -> dict[str, object]:
    with RAW_MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    observation_rows = [row for row in rows if row["kind"] == "station_observations"]
    errors: list[str] = []
    for row in rows:
        path = ROOT / row["relative_path"]
        if not path.exists():
            errors.append(f"missing raw file {row['relative_path']}")
            continue
        if path.stat().st_size != int(row["bytes"]):
            errors.append(f"raw byte mismatch {row['relative_path']}")
        if sha256(path) != row["sha256"]:
            errors.append(f"raw hash mismatch {row['relative_path']}")
        if not row["url"].startswith("https://opendata.dwd.de/"):
            errors.append(f"non-DWD source URL {row['url']}")
    if {row["station_id"] for row in observation_rows} != station_ids:
        errors.append("raw station archives do not match the frozen station contract")
    return {
        "files": len(rows),
        "station_archives": len(observation_rows),
        "all_urls_official_dwd": all(row["url"].startswith("https://opendata.dwd.de/") for row in rows),
        "all_hashes_match": not any("hash mismatch" in error for error in errors),
        "all_sizes_match": not any("byte mismatch" in error for error in errors),
        "errors": errors,
    }


def validate_year(year: int, stations: dict[str, dict[str, str]], expected_manifest: dict[str, str]) -> dict[str, object]:
    path = ROOT / expected_manifest["relative_path"]
    errors: list[str] = []
    if sha256(path) != expected_manifest["sha256"]:
        errors.append("processed SHA-256 mismatch")
    if path.stat().st_size != int(expected_manifest["bytes"]):
        errors.append("processed byte-count mismatch")

    rows = 0
    by_station: Counter[str] = Counter()
    by_cluster: Counter[str] = Counter()
    quality_codes: Counter[str] = Counter()
    last_timestamp: dict[str, datetime] = {}
    cadence_total: Counter[str] = Counter()
    cadence_ten: Counter[str] = Counter()
    bounds = {
        "temperature_c": [float("inf"), float("-inf")],
        "pressure_hpa": [float("inf"), float("-inf")],
        "station_pressure_hpa": [float("inf"), float("-inf")],
        "relative_humidity_pct": [float("inf"), float("-inf")],
    }
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            errors.append(f"schema mismatch: {reader.fieldnames}")
        for row in reader:
            rows += 1
            station_id = row["station_id"]
            if station_id not in stations:
                errors.append(f"unknown station {station_id}")
                break
            station = stations[station_id]
            if row["year"] != str(year) or row["evaluation_role"] != role_for_year(year):
                errors.append(f"year/role mismatch at {station_id} {row['timestamp_utc']}")
                break
            if row["cluster"] != station["cluster"] or row["source"] != f"DWD CDC 10-minute station observations {year}":
                errors.append(f"source/cluster mismatch at {station_id} {row['timestamp_utc']}")
                break
            observed = datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z"))
            previous = last_timestamp.get(station_id)
            if previous is not None:
                delta = (observed - previous).total_seconds() / 60.0
                if delta <= 0:
                    errors.append(f"duplicate/out-of-order timestamp at {station_id} {row['timestamp_utc']}")
                    break
                cadence_total[station_id] += 1
                if abs(delta - 10.0) < 1e-9:
                    cadence_ten[station_id] += 1
            last_timestamp[station_id] = observed

            temperature = float(row["temperature_c"])
            pressure = float(row["pressure_hpa"])
            station_pressure = float(row["station_pressure_hpa"])
            humidity = float(row["relative_humidity_pct"])
            expected_pressure = reduce_to_sea_level(station_pressure, temperature, float(station["elevation_m"]))
            if abs(pressure - expected_pressure) > 0.001:
                errors.append(f"pressure transform mismatch at {station_id} {row['timestamp_utc']}")
                break
            if not (-60.0 <= temperature <= 60.0 and 850.0 <= pressure <= 1120.0 and 500.0 <= station_pressure <= 1100.0 and 0.0 <= humidity <= 100.0):
                errors.append(f"physical range failure at {station_id} {row['timestamp_utc']}")
                break
            for name, value in (
                ("temperature_c", temperature),
                ("pressure_hpa", pressure),
                ("station_pressure_hpa", station_pressure),
                ("relative_humidity_pct", humidity),
            ):
                bounds[name][0] = min(bounds[name][0], value)
                bounds[name][1] = max(bounds[name][1], value)
            by_station[station_id] += 1
            by_cluster[row["cluster"]] += 1
            quality_codes[row["temperature_quality"]] += 1

    expected_rows = int(expected_manifest["rows"])
    if rows != expected_rows:
        errors.append(f"row count {rows} does not match manifest {expected_rows}")
    missing_stations = sorted(set(stations) - set(by_station))
    if missing_stations:
        errors.append(f"missing stations: {missing_stations}")
    sparse = {station: count for station, count in by_station.items() if count < 30_000}
    if sparse:
        errors.append(f"unexpectedly sparse station-years: {sparse}")
    cadence_ratio = {
        station: cadence_ten[station] / max(cadence_total[station], 1)
        for station in sorted(stations)
    }
    if any(value < 0.90 for value in cadence_ratio.values()):
        errors.append("at least one station has less than 90% exact 10-minute continuity")
    return {
        "year": year,
        "role": role_for_year(year),
        "rows": rows,
        "stations": len(by_station),
        "clusters": dict(sorted(by_cluster.items())),
        "rows_per_station": dict(sorted(by_station.items())),
        "exact_10_minute_ratio": cadence_ratio,
        "quality_codes": dict(sorted(quality_codes.items())),
        "bounds": {name: {"min": values[0], "max": values[1]} for name, values in bounds.items()},
        "sha256": expected_manifest["sha256"],
        "errors": errors,
    }


def main() -> None:
    with CONFIG.open(newline="", encoding="utf-8") as handle:
        station_rows = list(csv.DictReader(handle))
    stations = {row["station_id"]: row for row in station_rows}
    with PROCESSED_MANIFEST.open(newline="", encoding="utf-8") as handle:
        processed = {int(row["year"]): row for row in csv.DictReader(handle)}

    contract_errors = []
    if len(stations) != 16:
        contract_errors.append(f"expected 16 stations, found {len(stations)}")
    clusters = Counter(row["cluster"] for row in station_rows)
    if set(clusters.values()) != {4} or len(clusters) != 4:
        contract_errors.append(f"expected four balanced clusters, found {dict(clusters)}")
    if set(processed) != set(YEARS):
        contract_errors.append(f"processed years mismatch: {sorted(processed)}")

    raw = validate_raw_manifest(set(stations))
    yearly = [validate_year(year, stations, processed[year]) for year in YEARS]
    errors = contract_errors + list(raw["errors"])
    for item in yearly:
        errors.extend(f"{item['year']}: {message}" for message in item["errors"])
    report = {
        "status": "PASS" if not errors else "FAIL",
        "provider": "Deutscher Wetterdienst (DWD)",
        "product": "CDC 10-minute station observations of air temperature",
        "official_base_url": "https://opendata.dwd.de/",
        "station_contract": {
            "stations": len(stations),
            "clusters": dict(sorted(clusters.items())),
            "observation_inputs": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
        },
        "raw_integrity": raw,
        "yearly": yearly,
        "split_safety": {
            "development_train": 2022,
            "development_validation": 2023,
            "external_confirmation_locked": 2024,
            "2025_loaded": False,
        },
        "errors": errors,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Iteration 8 DWD data validation",
        "",
        f"- Status: **{report['status']}**",
        "- Provider: Deutscher Wetterdienst (DWD)",
        "- Product: CDC 10-minute station observations",
        f"- Raw integrity files: {raw['files']} ({raw['station_archives']} station archives)",
        f"- Balanced station contract: {len(stations)} stations across {len(clusters)} clusters",
        "- Model observation inputs: temperature, pressure, relative humidity",
        "- DWD 2024 role: external confirmation locked",
        "- 2025 loaded: no",
        "",
        "| Year | Role | Rows | Stations | Minimum exact 10-minute ratio |",
        "|---:|---|---:|---:|---:|",
    ]
    for item in yearly:
        lines.append(
            f"| {item['year']} | {item['role']} | {item['rows']:,} | {item['stations']} | "
            f"{min(item['exact_10_minute_ratio'].values()):.2%} |"
        )
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {error}" for error in errors] or ["- None"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if errors:
        raise SystemExit(f"FAIL: {len(errors)} validation errors; see {REPORT_JSON}")
    print(f"PASS: authentic, checksummed, schema-valid DWD corpus; report={REPORT_JSON}")


if __name__ == "__main__":
    main()

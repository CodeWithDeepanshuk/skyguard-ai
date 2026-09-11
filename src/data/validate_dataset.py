"""Validate provenance, integrity, schema, coverage, and values for SkyGuard data."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "stations.csv"
INVENTORY = ROOT / "data" / "raw" / "metadata" / "isd-history.csv"
MANIFEST = ROOT / "data" / "manifest" / "raw_files.csv"
DATA = ROOT / "data" / "processed" / "aws_observations_2022_2024.csv"
REPORT_JSON = ROOT / "reports" / "data_validation.json"
REPORT_MD = ROOT / "reports" / "data_validation.md"
EXPECTED_YEARS = {"2022", "2023", "2024"}
REQUIRED_RAW_COLUMNS = {"STATION", "DATE", "LATITUDE", "LONGITUDE", "NAME", "TMP", "DEW", "SLP", "MA1"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percent(value: int, total: int) -> float:
    return round(100.0 * value / total, 4) if total else 0.0


def validate() -> dict[str, object]:
    with CONFIG.open("r", encoding="utf-8", newline="") as handle:
        configured = list(csv.DictReader(handle))
    station_ids = {row["station_id"] for row in configured}

    with INVENTORY.open("r", encoding="utf-8-sig", newline="") as handle:
        inventory = {row["USAF"] + row["WBAN"]: row for row in csv.DictReader(handle)}

    metadata_errors: list[str] = []
    for station in configured:
        official = inventory.get(station["station_id"])
        if official is None:
            metadata_errors.append(f"{station['station_id']}: absent from official inventory")
            continue
        if official["CTRY"] != "IN":
            metadata_errors.append(f"{station['station_id']}: country is {official['CTRY']}, not IN")
        if official["END"] < "20241231":
            metadata_errors.append(f"{station['station_id']}: official record ended {official['END']}")
        for config_key, official_key in (("latitude", "LAT"), ("longitude", "LON")):
            if abs(float(station[config_key]) - float(official[official_key])) > 0.01:
                metadata_errors.append(f"{station['station_id']}: {config_key} does not match inventory")

    with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    integrity_errors: list[str] = []
    observation_entries = [row for row in manifest if row["kind"] == "station_observations"]
    for entry in manifest:
        path = ROOT / entry["relative_path"]
        if not path.exists():
            integrity_errors.append(f"missing file: {entry['relative_path']}")
            continue
        if str(path.stat().st_size) != entry["bytes"]:
            integrity_errors.append(f"size mismatch: {entry['relative_path']}")
        if sha256(path) != entry["sha256"]:
            integrity_errors.append(f"SHA-256 mismatch: {entry['relative_path']}")
        if "ncei.noaa.gov" not in entry["url"]:
            integrity_errors.append(f"non-NCEI source URL: {entry['url']}")

    raw_schema_errors: list[str] = []
    for entry in observation_entries:
        path = ROOT / entry["relative_path"]
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            first = next(reader, None)
        missing_columns = sorted(REQUIRED_RAW_COLUMNS - columns)
        if missing_columns:
            raw_schema_errors.append(f"{entry['relative_path']}: missing {missing_columns}")
        if first is None:
            raw_schema_errors.append(f"{entry['relative_path']}: no observations")
        elif first.get("STATION") != entry["station_id"]:
            raw_schema_errors.append(f"{entry['relative_path']}: station ID mismatch")

    rows = 0
    stations: set[str] = set()
    years: Counter[str] = Counter()
    clusters: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    missing = Counter()
    violations = Counter()
    ranges = {field: [math.inf, -math.inf] for field in ("temperature_c", "pressure_hpa", "relative_humidity_pct")}
    timestamps: defaultdict[tuple[str, str], list[datetime]] = defaultdict(list)
    seen_keys: set[tuple[str, str]] = set()
    duplicates = 0
    clean_candidates = 0

    with DATA.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        processed_columns = set(reader.fieldnames or [])
        for row in reader:
            rows += 1
            station_id = row["station_id"]
            year = row["year"]
            stations.add(station_id)
            years[year] += 1
            clusters[row["cluster"]] += 1
            roles[row["evaluation_role"]] += 1
            observed = datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z"))
            timestamps[(station_id, year)].append(observed)
            key = (station_id, row["timestamp_utc"])
            if key in seen_keys:
                duplicates += 1
            seen_keys.add(key)

            values: dict[str, float | None] = {}
            for field in ranges:
                if not row[field]:
                    missing[field] += 1
                    values[field] = None
                else:
                    value = float(row[field])
                    values[field] = value
                    ranges[field][0] = min(ranges[field][0], value)
                    ranges[field][1] = max(ranges[field][1], value)

            temp = values["temperature_c"]
            pressure = values["pressure_hpa"]
            humidity = values["relative_humidity_pct"]
            physical = True
            if temp is not None and not -60.0 <= temp <= 60.0:
                violations["temperature_out_of_bounds"] += 1
                physical = False
            if pressure is not None and not 870.0 <= pressure <= 1075.0:
                violations["pressure_out_of_bounds"] += 1
                physical = False
            if humidity is not None and not 0.0 <= humidity <= 100.0:
                violations["humidity_out_of_bounds"] += 1
                physical = False
            if row["dew_point_c"] and temp is not None and float(row["dew_point_c"]) > temp + 1.0:
                violations["dew_point_above_temperature"] += 1
                physical = False
            if physical and temp is not None and pressure is not None and humidity is not None:
                clean_candidates += 1

    coverage: list[dict[str, object]] = []
    for (station_id, year), values in sorted(timestamps.items()):
        values.sort()
        gaps = [(right - left).total_seconds() / 60.0 for left, right in zip(values, values[1:])]
        coverage.append({
            "station_id": station_id,
            "year": year,
            "rows": len(values),
            "start_utc": values[0].isoformat() + "Z",
            "end_utc": values[-1].isoformat() + "Z",
            "median_interval_minutes": round(median(gaps), 2) if gaps else None,
            "sampling_tier": "high" if len(values) >= 8000 else "medium" if len(values) >= 1500 else "low",
        })

    expected_pairs = len(station_ids) * len(EXPECTED_YEARS)
    required_processed = {
        "station_id", "timestamp_utc", "year", "cluster", "evaluation_role",
        "temperature_c", "relative_humidity_pct", "pressure_hpa", "pressure_source",
    }
    checks = {
        "official_source_urls_only": not any("non-NCEI" in item for item in integrity_errors),
        "all_expected_files_present": len(manifest) == expected_pairs + 2 and len(observation_entries) == expected_pairs,
        "all_sha256_checks_pass": not integrity_errors,
        "official_station_metadata_matches": not metadata_errors,
        "raw_schema_valid": not raw_schema_errors,
        "processed_schema_valid": required_processed.issubset(processed_columns),
        "all_stations_present": stations == station_ids,
        "all_years_present": set(years) == EXPECTED_YEARS,
        "all_station_year_pairs_present": len(coverage) == expected_pairs,
        "minimum_1500_rows_per_station_year": min(item["rows"] for item in coverage) >= 1500,
        "no_processed_duplicate_timestamps": duplicates == 0,
        "temperature_missing_below_0_1_percent": percent(missing["temperature_c"], rows) < 0.1,
        "humidity_missing_below_0_1_percent": percent(missing["relative_humidity_pct"], rows) < 0.1,
        "pressure_missing_below_5_percent": percent(missing["pressure_hpa"], rows) < 5.0,
    }

    return {
        "ready_for_anomaly_injection": all(checks.values()),
        "provenance": {
            "provider": "NOAA/NCEI",
            "product": "Global Hourly / Integrated Surface Database (ISD)",
            "manifest_entries": len(manifest),
            "observation_files": len(observation_entries),
            "total_raw_bytes_in_manifest": sum(int(row["bytes"]) for row in manifest),
        },
        "summary": {
            "processed_rows": rows,
            "stations": len(stations),
            "years": dict(sorted(years.items())),
            "clusters": dict(sorted(clusters.items())),
            "roles": dict(sorted(roles.items())),
            "clean_candidate_rows": clean_candidates,
            "clean_candidate_percent": percent(clean_candidates, rows),
            "duplicate_station_timestamps": duplicates,
        },
        "missing": {field: {"rows": missing[field], "percent": percent(missing[field], rows)} for field in ranges},
        "ranges": {field: {"min": values[0], "max": values[1]} for field, values in ranges.items()},
        "physical_violations": dict(violations),
        "checks": checks,
        "metadata_errors": metadata_errors,
        "integrity_errors": integrity_errors,
        "raw_schema_errors": raw_schema_errors,
        "coverage": coverage,
        "limitation": "ISD observations are genuine, but confirmed sensor-fault labels are not included. Controlled fault injection is required for supervised evaluation.",
    }


def write_markdown(report: dict[str, object]) -> None:
    summary = report["summary"]
    provenance = report["provenance"]
    violation_count = sum(report["physical_violations"].values())
    lines = [
        "# SkyGuard AI data validation report",
        "",
        f"**Ready for anomaly injection: {'YES' if report['ready_for_anomaly_injection'] else 'NO'}**",
        "",
        "## Authenticity and integrity",
        "",
        f"- Provider: {provenance['provider']}",
        f"- Product: {provenance['product']}",
        f"- Files in checksum manifest: {provenance['manifest_entries']}",
        f"- Station-year observation files: {provenance['observation_files']}",
        f"- Raw bytes covered by manifest: {provenance['total_raw_bytes_in_manifest']:,}",
        "",
        "## Processed corpus",
        "",
        f"- Rows: {summary['processed_rows']:,}",
        f"- Stations: {summary['stations']}",
        f"- Years: {', '.join(summary['years'])}",
        f"- Regional clusters: {len(summary['clusters'])}",
        f"- Clean candidate rows: {summary['clean_candidate_rows']:,} ({summary['clean_candidate_percent']:.4f}%)",
        f"- Duplicate station/timestamps: {summary['duplicate_station_timestamps']}",
        "",
        "## Missingness",
        "",
        "| Variable | Missing rows | Missing % |",
        "|---|---:|---:|",
    ]
    for field, values in report["missing"].items():
        lines.append(f"| {field} | {values['rows']:,} | {values['percent']:.4f}% |")
    lines.extend(["", "## Validation checks", "", "| Check | Result |", "|---|---|"])
    for name, passed in report["checks"].items():
        lines.append(f"| {name.replace('_', ' ')} | {'PASS' if passed else 'FAIL'} |")
    lines.extend([
        "",
        "## Known source-value flags",
        "",
        f"Physical-bound violations detected: {violation_count}",
        "",
        "Violating rows, if present in a future refresh, remain auditable in the normalized source table and are excluded from the clean candidate pool used for synthetic fault injection.",
        "",
        "## Important limitation",
        "",
        report["limitation"],
        "",
        "## Station-year coverage",
        "",
        "| Station | Year | Rows | Median interval (min) | Tier |",
        "|---|---:|---:|---:|---|",
    ])
    for item in report["coverage"]:
        lines.append(f"| {item['station_id']} | {item['year']} | {item['rows']:,} | {item['median_interval_minutes']} | {item['sampling_tier']} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = validate()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)
    print(json.dumps({
        "ready_for_anomaly_injection": report["ready_for_anomaly_injection"],
        "summary": report["summary"],
        "missing": report["missing"],
        "physical_violations": report["physical_violations"],
        "failed_checks": [name for name, passed in report["checks"].items() if not passed],
        "reports": [str(REPORT_JSON), str(REPORT_MD)],
    }, indent=2))


if __name__ == "__main__":
    main()

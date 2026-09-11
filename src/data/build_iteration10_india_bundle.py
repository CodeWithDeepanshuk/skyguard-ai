"""Build and audit the locked-year-safe Iteration 10 India development bundle.

The source observations were downloaded from the official NOAA/NCEI Global
Hourly archive and already have a checksummed raw manifest.  This builder does
not open 2024 or 2025 observations.  It creates a compact 2022--2023 snapshot,
re-verifies every relevant raw hash, measures cadence and causal neighbour
availability, and packages the exact development files used by the GPU
notebook.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.normalize_noaa_isd import normalize_file  # noqa: E402


STATIONS = ROOT / "config" / "stations.csv"
RAW_MANIFEST = ROOT / "data" / "manifest" / "raw_files.csv"
INVENTORY = ROOT / "data" / "iteration10" / "raw" / "metadata" / "isd-inventory.csv"
ITER10_ROOT = ROOT / "data" / "iteration10"
OUTPUT = ITER10_ROOT / "processed" / "india_aws_2022_2023.csv.gz"
STATION_SNAPSHOT = ITER10_ROOT / "config" / "india_stations.csv"
SPLIT_CONTRACT = ITER10_ROOT / "config" / "split_contract.json"
MANIFEST = ITER10_ROOT / "manifest" / "india_development_files.csv"
REPORT_JSON = ROOT / "reports" / "iteration10_india_data_validation.json"
REPORT_MD = ROOT / "reports" / "iteration10_india_data_validation.md"
PACKAGE = ROOT / "deliverables" / "SkyGuard_Iteration10_India_Development_Data_Bundle.zip"

DEVELOPMENT_YEARS = (2022, 2023)
LOCKED_YEARS = (2024, 2025)
REQUIRED_OBSERVATIONS = ("temperature_c", "pressure_hpa", "relative_humidity_pct")
OUTPUT_COLUMNS = (
    "station_id", "timestamp_utc", "year", "cluster", "evaluation_role",
    "station_name", "latitude", "longitude", "elevation_m",
    "temperature_c", "relative_humidity_pct", "pressure_hpa",
    "pressure_source", "source", "report_type",
)
OFFICIAL_PREFIX = "https://www.ncei.noaa.gov/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentage(mask: pd.Series | np.ndarray) -> float:
    values = np.asarray(mask, dtype=bool)
    return float(values.mean() * 100.0) if values.size else 0.0


def load_station_contract() -> pd.DataFrame:
    frame = pd.read_csv(STATIONS, dtype={"station_id": str, "icao": str})
    frame["station_id"] = frame["station_id"].astype(str)
    if len(frame) != 24 or frame.station_id.nunique() != 24:
        raise RuntimeError("The India station contract must contain 24 unique stations.")
    cluster_sizes = frame.groupby("cluster").size().to_dict()
    if cluster_sizes != {"bengaluru": 6, "chennai": 6, "delhi": 6, "hyderabad": 6}:
        raise RuntimeError(f"Unexpected regional station contract: {cluster_sizes}")
    holdouts = frame.loc[frame.evaluation_role.eq("station_holdout")].groupby("cluster").size()
    if not (holdouts == 1).all() or len(holdouts) != 4:
        raise RuntimeError("Exactly one station per India cluster must be a station holdout.")
    return frame


def verify_raw_files(stations: pd.DataFrame) -> tuple[list[dict[str, object]], list[str]]:
    manifest_rows = list(csv.DictReader(RAW_MANIFEST.open("r", encoding="utf-8", newline="")))
    lookup = {
        (row["station_id"], int(row["year"])): row
        for row in manifest_rows
        if row["kind"] == "station_observations" and row["year"]
    }
    verified: list[dict[str, object]] = []
    errors: list[str] = []
    for station_id in stations.station_id:
        for year in DEVELOPMENT_YEARS:
            item = lookup.get((station_id, year))
            if item is None:
                errors.append(f"missing manifest entry: {station_id}/{year}")
                continue
            path = ROOT / item["relative_path"]
            if not item["url"].startswith(OFFICIAL_PREFIX):
                errors.append(f"non-official URL: {item['url']}")
            if not path.exists():
                errors.append(f"missing raw file: {path}")
                continue
            actual_hash = sha256(path)
            if actual_hash != item["sha256"]:
                errors.append(f"hash mismatch: {station_id}/{year}")
            if path.stat().st_size != int(item["bytes"]):
                errors.append(f"size mismatch: {station_id}/{year}")
            verified.append({
                "kind": "station_observations",
                "station_id": station_id,
                "year": year,
                "url": item["url"],
                "relative_path": item["relative_path"],
                "bytes": path.stat().st_size,
                "sha256": actual_hash,
            })
    for kind in ("station_metadata", "format_documentation"):
        item = next((row for row in manifest_rows if row["kind"] == kind), None)
        if item is None:
            errors.append(f"missing support manifest entry: {kind}")
            continue
        path = ROOT / item["relative_path"]
        if not path.exists() or sha256(path) != item["sha256"]:
            errors.append(f"support-file integrity failure: {kind}")
        else:
            verified.append({
                "kind": kind, "station_id": "", "year": "", "url": item["url"],
                "relative_path": item["relative_path"], "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    return verified, errors


def load_development_observations(stations: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, str]] = []
    station_rows = stations.set_index("station_id").to_dict("index")
    for station_id, station in station_rows.items():
        station_contract = {key: "" if pd.isna(value) else str(value) for key, value in station.items()}
        station_contract["station_id"] = str(station_id)
        for year in DEVELOPMENT_YEARS:
            raw_path = ROOT / "data" / "raw" / "noaa" / str(year) / f"{station_id}.csv"
            records.extend(normalize_file(raw_path, station_contract, year).values())
    frame = pd.DataFrame.from_records(records, columns=list(OUTPUT_COLUMNS))
    frame["station_id"] = frame.station_id.astype(str)
    frame["year"] = pd.to_numeric(frame.year, errors="raise").astype(np.int16)
    for column in REQUIRED_OBSERVATIONS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["timestamp_utc"] = pd.to_datetime(frame.timestamp_utc, utc=True)
    frame = frame.sort_values(["station_id", "timestamp_utc"], kind="stable").reset_index(drop=True)
    if frame.empty:
        raise RuntimeError("No Iteration 10 India development rows were loaded.")
    if set(frame.year.unique()) != set(DEVELOPMENT_YEARS):
        raise RuntimeError(f"Development years are incomplete: {sorted(frame.year.unique())}")
    station_ids = set(stations.station_id)
    if set(frame.station_id.unique()) != station_ids:
        missing = station_ids - set(frame.station_id.unique())
        raise RuntimeError(f"Development stations are incomplete: {sorted(missing)}")
    if frame.timestamp_utc.dt.year.isin(LOCKED_YEARS).any():
        raise RuntimeError("A locked year entered the Iteration 10 India development snapshot.")
    return frame


def station_year_coverage(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (station, year), group in frame.groupby(["station_id", "year"], sort=True):
        ordered = group.sort_values("timestamp_utc")
        delta = ordered.timestamp_utc.diff().dt.total_seconds().div(60.0)
        positive = delta.loc[delta.gt(0)]
        triple = ordered.loc[:, REQUIRED_OBSERVATIONS].notna().all(axis=1)
        rows.append({
            "station_id": str(station), "year": int(year), "rows": int(len(ordered)),
            "valid_triple_rows": int(triple.sum()), "valid_triple_percent": percentage(triple),
            "start_utc": ordered.timestamp_utc.iloc[0].isoformat().replace("+00:00", "Z"),
            "end_utc": ordered.timestamp_utc.iloc[-1].isoformat().replace("+00:00", "Z"),
            "median_interval_minutes": float(positive.median()),
            "p90_interval_minutes": float(positive.quantile(.90)),
            "intervals_within_2x_median_percent": percentage(
                positive.le(max(float(positive.median()) * 2.0, 1.0))
            ),
            "unique_reporting_days": int(ordered.timestamp_utc.dt.date.nunique()),
        })
    return rows


def causal_neighbour_counts(frame: pd.DataFrame, tolerance_minutes: float) -> np.ndarray:
    """Count other-cluster stations last seen causally within a time tolerance."""

    counts = np.zeros(len(frame), dtype=np.int16)
    valid = frame.loc[:, REQUIRED_OBSERVATIONS].notna().all(axis=1).to_numpy()
    nanoseconds = frame.timestamp_utc.astype("int64").to_numpy()
    tolerance_ns = int(tolerance_minutes * 60.0 * 1e9)
    for _, cluster_group in frame.groupby("cluster", sort=False):
        station_arrays = {
            str(station): nanoseconds[group.index.to_numpy()][valid[group.index.to_numpy()]]
            for station, group in cluster_group.groupby("station_id", sort=False)
        }
        for station, target_group in cluster_group.groupby("station_id", sort=False):
            target_indices = target_group.index.to_numpy()
            target_times = nanoseconds[target_indices]
            target_counts = np.zeros(len(target_indices), dtype=np.int16)
            for neighbour, neighbour_times in station_arrays.items():
                if neighbour == str(station) or neighbour_times.size == 0:
                    continue
                positions = np.searchsorted(neighbour_times, target_times, side="right") - 1
                usable = positions >= 0
                ages = np.full(len(target_times), tolerance_ns + 1, dtype=np.int64)
                ages[usable] = target_times[usable] - neighbour_times[positions[usable]]
                target_counts += (usable & (ages >= 0) & (ages <= tolerance_ns)).astype(np.int16)
            counts[target_indices] = target_counts
    return counts


def neighbour_support(frame: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    summary: list[dict[str, object]] = []
    station_summary: list[dict[str, object]] = []
    for tolerance in (90.0, 180.0, 360.0):
        counts = causal_neighbour_counts(frame, tolerance)
        for cluster, indices in frame.groupby("cluster", sort=True).groups.items():
            values = counts[np.asarray(list(indices), dtype=np.int64)]
            summary.append({
                "cluster": cluster, "tolerance_minutes": tolerance, "rows": int(len(values)),
                "at_least_1_neighbour_percent": percentage(values >= 1),
                "at_least_2_neighbours_percent": percentage(values >= 2),
                "at_least_3_neighbours_percent": percentage(values >= 3),
                "mean_causal_neighbours": float(values.mean()),
            })
        if tolerance == 180.0:
            for station, indices in frame.groupby("station_id", sort=True).groups.items():
                values = counts[np.asarray(list(indices), dtype=np.int64)]
                station_summary.append({
                    "station_id": station, "rows": int(len(values)),
                    "at_least_1_neighbour_percent": percentage(values >= 1),
                    "at_least_2_neighbours_percent": percentage(values >= 2),
                    "mean_causal_neighbours": float(values.mean()),
                })
    return summary, station_summary


def write_snapshot(frame: pd.DataFrame, stations: pd.DataFrame) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output = frame.loc[:, OUTPUT_COLUMNS].copy()
    output["timestamp_utc"] = output.timestamp_utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    output.to_csv(OUTPUT, index=False, compression={"method": "gzip", "compresslevel": 6})
    STATION_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    stations.to_csv(STATION_SNAPSHOT, index=False)
    split = {
        "version": "iteration10_india_development_v1",
        "fit": {"year": 2022, "stations": "development_only"},
        "calibration": {"start": "2023-01-01", "end": "2023-02-28", "stations": "development_only"},
        "policy": {"start": "2023-03-01", "end": "2023-04-30", "stations": "development_only"},
        "discovery": {"start": "2023-05-01", "end": "2023-08-31", "stations": "all_including_station_holdout"},
        "confirmation": {"start": "2023-09-01", "end": "2023-12-31", "stations": "all_including_station_holdout"},
        "station_holdout_rule": "never enters fitting, early stopping, calibration, or policy selection",
        "episode_rule": "complete injected episodes remain in one split",
        "locked_years": list(LOCKED_YEARS),
        "random_row_split_forbidden": True,
    }
    SPLIT_CONTRACT.write_text(json.dumps(split, indent=2), encoding="utf-8")


def write_manifest(raw_rows: list[dict[str, object]]) -> None:
    rows = list(raw_rows)
    for kind, path, url in (
        ("isd_inventory", INVENTORY, "https://www.ncei.noaa.gov/pub/data/noaa/isd-inventory.csv"),
        ("processed_development_snapshot", OUTPUT, "derived from checksummed official NOAA/NCEI files"),
        ("station_contract", STATION_SNAPSHOT, "local frozen contract derived from official station metadata"),
        ("split_contract", SPLIT_CONTRACT, "local causal evaluation contract"),
    ):
        rows.append({
            "kind": kind, "station_id": "", "year": "", "url": url,
            "relative_path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    fields = ["kind", "station_id", "year", "url", "relative_path", "bytes", "sha256"]
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_package() -> None:
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    members = [OUTPUT, STATION_SNAPSHOT, SPLIT_CONTRACT, MANIFEST, REPORT_JSON]
    with zipfile.ZipFile(PACKAGE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in members:
            name = path.relative_to(ROOT).as_posix()
            if "2024" in name or "2025" in name:
                raise RuntimeError(f"Locked year leaked into package member name: {name}")
            archive.write(path, name)


def report_markdown(report: dict[str, object]) -> str:
    summary = report["summary"]
    lines = [
        "# Iteration 10 India development-data validation",
        "",
        f"Status: **{report['status']}**",
        "",
        "The bundle contains only official NOAA/NCEI-derived 2022–2023 observations. "
        "It does not contain or open a 2024/2025 observation file.",
        "",
        "## Summary",
        "",
        f"- Rows: {summary['rows']:,}",
        f"- Stations: {summary['stations']}",
        f"- Clusters: {summary['clusters']}",
        f"- Complete T/P/RH rows: {summary['valid_triple_percent']:.3f}%",
        f"- Duplicate station timestamps: {summary['duplicate_station_timestamps']}",
        f"- Development bundle: `{report['artifacts']['package']}`",
        "",
        "## Causal neighbour support",
        "",
        "| Cluster | Tolerance | >=1 neighbour | >=2 neighbours | Mean |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["neighbour_support"]:
        if row["tolerance_minutes"] != 180.0:
            continue
        lines.append(
            f"| {row['cluster']} | {row['tolerance_minutes']:.0f} min | "
            f"{row['at_least_1_neighbour_percent']:.2f}% | "
            f"{row['at_least_2_neighbours_percent']:.2f}% | {row['mean_causal_neighbours']:.2f} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The India corpus is genuine and sizeable, but its station cadences are mixed. "
        "The model must therefore use elapsed-time windows and expose stale/absent neighbour "
        "evidence; it must not assume a DWD-like uniform 10-minute network.",
        "",
        "## Checks",
        "",
    ])
    for name, passed in report["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    started = datetime.now(timezone.utc)
    stations = load_station_contract()
    raw_rows, raw_errors = verify_raw_files(stations)
    if not INVENTORY.exists() or INVENTORY.stat().st_size == 0:
        raise RuntimeError(
            "Official ISD inventory is missing. Download it from "
            "https://www.ncei.noaa.gov/pub/data/noaa/isd-inventory.csv"
        )
    frame = load_development_observations(stations)
    station_year = station_year_coverage(frame)
    neighbours, station_neighbours = neighbour_support(frame)
    duplicate_count = int(frame.duplicated(["station_id", "timestamp_utc"]).sum())
    valid_triple = frame.loc[:, REQUIRED_OBSERVATIONS].notna().all(axis=1)
    source_values = set(frame.source.astype(str).unique())
    checks = {
        "48_station_year_raw_files_verified": len([row for row in raw_rows if row["kind"] == "station_observations"]) == 48,
        "all_raw_hashes_match": not raw_errors,
        "official_source_urls_only": all(
            row["url"].startswith(OFFICIAL_PREFIX)
            for row in raw_rows if row["kind"] in {"station_observations", "station_metadata", "format_documentation"}
        ),
        "exactly_24_stations_and_4_clusters": frame.station_id.nunique() == 24 and frame.cluster.nunique() == 4,
        "both_development_years_present": set(frame.year.unique()) == set(DEVELOPMENT_YEARS),
        "all_48_station_year_pairs_present": len(station_year) == 48,
        "minimum_1500_rows_per_station_year": min(row["rows"] for row in station_year) >= 1500,
        "minimum_90_percent_complete_triples_per_station_year": min(row["valid_triple_percent"] for row in station_year) >= 90.0,
        "no_duplicate_station_timestamps": duplicate_count == 0,
        "temperature_missing_below_0_1_percent": percentage(frame.temperature_c.isna()) < 0.1,
        "humidity_missing_below_0_1_percent": percentage(frame.relative_humidity_pct.isna()) < 0.1,
        "pressure_missing_below_5_percent": percentage(frame.pressure_hpa.isna()) < 5.0,
        "temperature_range_plausible": bool(frame.temperature_c.dropna().between(-20.0, 60.0).all()),
        "humidity_range_valid": bool(frame.relative_humidity_pct.dropna().between(0.0, 100.0).all()),
        "pressure_range_plausible": bool(frame.pressure_hpa.dropna().between(850.0, 1100.0).all()),
        "source_labels_only_2022_2023": all("2024" not in value and "2025" not in value for value in source_values),
        "locked_observation_years_not_loaded": not frame.timestamp_utc.dt.year.isin(LOCKED_YEARS).any(),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    write_snapshot(frame, stations)
    write_manifest(raw_rows)
    report = {
        "status": status,
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": "NOAA/NCEI",
        "product": "Global Hourly / Integrated Surface Database (ISD)",
        "official_dataset_page": "https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database",
        "development_years": list(DEVELOPMENT_YEARS),
        "locked_years_opened": [],
        "summary": {
            "rows": int(len(frame)), "stations": int(frame.station_id.nunique()),
            "clusters": int(frame.cluster.nunique()),
            "rows_by_year": {str(key): int(value) for key, value in frame.groupby("year").size().items()},
            "rows_by_cluster": {str(key): int(value) for key, value in frame.groupby("cluster").size().items()},
            "roles": {str(key): int(value) for key, value in frame.groupby("evaluation_role").size().items()},
            "valid_triple_rows": int(valid_triple.sum()),
            "valid_triple_percent": percentage(valid_triple),
            "duplicate_station_timestamps": duplicate_count,
        },
        "missing_percent": {
            column: percentage(frame[column].isna()) for column in REQUIRED_OBSERVATIONS
        },
        "ranges": {
            column: {"min": float(frame[column].min()), "max": float(frame[column].max())}
            for column in REQUIRED_OBSERVATIONS
        },
        "pressure_sources": {str(key): int(value) for key, value in frame.groupby("pressure_source", dropna=False).size().items()},
        "station_year_coverage": station_year,
        "neighbour_support": neighbours,
        "station_neighbour_support_180m": station_neighbours,
        "raw_integrity_errors": raw_errors,
        "checks": checks,
        "artifacts": {
            "observations": OUTPUT.relative_to(ROOT).as_posix(),
            "station_contract": STATION_SNAPSHOT.relative_to(ROOT).as_posix(),
            "split_contract": SPLIT_CONTRACT.relative_to(ROOT).as_posix(),
            "manifest": MANIFEST.relative_to(ROOT).as_posix(),
            "package": PACKAGE.relative_to(ROOT).as_posix(),
        },
        "runtime_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    REPORT_MD.write_text(report_markdown(report), encoding="utf-8")
    build_package()
    # Package hash is deliberately written after packaging so the package cannot
    # contain a self-referential digest.
    receipt = {"package_sha256": sha256(PACKAGE), "package_bytes": PACKAGE.stat().st_size}
    print(json.dumps({"status": status, "summary": report["summary"], "receipt": receipt}, indent=2))
    if status != "PASS":
        raise SystemExit("Iteration 10 India data validation failed.")


if __name__ == "__main__":
    main()

"""Download and checksum the official DWD corpus selected for Iteration 8."""

from __future__ import annotations

import csv
import hashlib
import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "iteration8_dwd_stations.csv"
RAW_ROOT = ROOT / "data" / "iteration8" / "raw" / "dwd"
HISTORICAL_ROOT = RAW_ROOT / "historical"
METADATA_ROOT = RAW_ROOT / "metadata"
MANIFEST = ROOT / "data" / "iteration8" / "manifest" / "dwd_raw_files.csv"
BASE_URL = (
    "https://opendata.dwd.de/climate_environment/CDC/observations_germany/"
    "climate/10_minutes/air_temperature/historical/"
)
STATION_METADATA_URL = BASE_URL + "zehn_min_tu_Beschreibung_Stationen.txt"
DESCRIPTION_URL = (
    "https://opendata.dwd.de/climate_environment/CDC/observations_germany/"
    "climate/10_minutes/air_temperature/"
    "DESCRIPTION_obsgermany_climate_10min_air_temperature_en.pdf"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(kind: str, station_id: str, url: str, destination: Path) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    status = "reused"
    if not destination.exists() or destination.stat().st_size == 0:
        temporary = destination.with_suffix(destination.suffix + ".part")
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(destination)
        status = "downloaded"
    return {
        "kind": kind,
        "station_id": station_id,
        "url": url,
        "relative_path": destination.relative_to(ROOT).as_posix(),
        "bytes": str(destination.stat().st_size),
        "sha256": sha256(destination),
        "status": status,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> None:
    with CONFIG.open(newline="", encoding="utf-8") as handle:
        stations = list(csv.DictReader(handle))
    if len(stations) != 16 or len({row["cluster"] for row in stations}) != 4:
        raise SystemExit("Iteration 8 station contract must contain 16 stations in four clusters.")

    jobs: list[tuple[str, str, str, Path]] = [
        (
            "station_metadata",
            "",
            STATION_METADATA_URL,
            METADATA_ROOT / "zehn_min_tu_Beschreibung_Stationen.txt",
        ),
        (
            "dataset_documentation",
            "",
            DESCRIPTION_URL,
            METADATA_ROOT / "DESCRIPTION_obsgermany_climate_10min_air_temperature_en.pdf",
        ),
    ]
    for station in stations:
        archive = station["archive_file"]
        jobs.append((
            "station_observations",
            station["station_id"],
            BASE_URL + archive,
            HISTORICAL_ROOT / archive,
        ))

    results: list[dict[str, str]] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch, *job): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"{result['status']:10s} {result['station_id'] or result['kind']}: {int(result['bytes']):,} bytes")
            except Exception as exc:  # pragma: no cover - network failures are environment-specific
                failures.append(f"{job[1] or job[0]}: {exc}")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    fields = ["kind", "station_id", "url", "relative_path", "bytes", "sha256", "status", "checked_at_utc"]
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda row: (row["kind"], row["station_id"])))

    if failures or len(results) != len(jobs):
        raise SystemExit(f"DWD download incomplete: {len(results)}/{len(jobs)} files; {failures}")
    print(f"PASS: {len(stations)} official DWD station archives plus metadata; manifest={MANIFEST}")


if __name__ == "__main__":
    main()

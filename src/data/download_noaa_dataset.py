"""Download and checksum the complete SkyGuard NOAA benchmark corpus."""

from __future__ import annotations

import csv
import hashlib
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "stations.csv"
RAW_ROOT = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest" / "raw_files.csv"
YEARS = (2022, 2023, 2024)
BASE = "https://www.ncei.noaa.gov/data/global-hourly/access"
SUPPORT_FILES = (
    ("station_metadata", "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv", RAW_ROOT / "metadata" / "isd-history.csv"),
    ("format_documentation", "https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf", RAW_ROOT / "documentation" / "isd-format-document.pdf"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(kind: str, url: str, destination: Path, station_id: str = "", year: str = "") -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    status = "reused"
    if not destination.exists() or destination.stat().st_size == 0:
        status = "downloaded"
        temporary = destination.with_suffix(destination.suffix + ".part")
        request = urllib.request.Request(url, headers={"User-Agent": "SkyGuard-AI/1.0 SIH research"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
            os.replace(temporary, destination)
        except Exception:
            if temporary.exists():
                temporary.unlink()
            raise

    return {
        "kind": kind,
        "station_id": station_id,
        "year": year,
        "url": url,
        "relative_path": destination.relative_to(ROOT).as_posix(),
        "bytes": str(destination.stat().st_size),
        "sha256": sha256(destination),
        "status": status,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> None:
    with CONFIG.open("r", encoding="utf-8", newline="") as handle:
        stations = list(csv.DictReader(handle))

    jobs: list[tuple[str, str, Path, str, str]] = []
    for kind, url, destination in SUPPORT_FILES:
        jobs.append((kind, url, destination, "", ""))
    for station in stations:
        station_id = station["station_id"]
        for year in YEARS:
            url = f"{BASE}/{year}/{station_id}.csv"
            destination = RAW_ROOT / "noaa" / str(year) / f"{station_id}.csv"
            jobs.append(("station_observations", url, destination, station_id, str(year)))

    results: list[dict[str, str]] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(download, *job): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                result = future.result()
                results.append(result)
                label = result["station_id"] or result["kind"]
                print(f"{result['status']:10s} {label} {result['year']} ({int(result['bytes']):,} bytes)")
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                failures.append(f"{job[1]}: {exc}")
                print(f"failed     {job[1]}: {exc}")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    fields = ["kind", "station_id", "year", "url", "relative_path", "bytes", "sha256", "status", "checked_at_utc"]
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda row: (row["kind"], row["year"], row["station_id"])))

    expected = len(jobs)
    print(f"Manifest contains {len(results)}/{expected} expected files: {MANIFEST}")
    if failures or len(results) != expected:
        raise SystemExit("Dataset download is incomplete. See failed URLs above.")


if __name__ == "__main__":
    main()

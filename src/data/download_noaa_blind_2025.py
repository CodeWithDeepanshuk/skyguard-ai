"""Download the sealed 2025 NOAA/NCEI legacy-ISD compatibility benchmark."""

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
OUTPUT_ROOT = ROOT / "data" / "blind_2025" / "raw" / "noaa" / "2025"
MANIFEST = ROOT / "data" / "blind_2025" / "manifest" / "raw_files.csv"
BASE_URL = "https://www.ncei.noaa.gov/data/global-hourly/access/2025"
USER_AGENT = "SkyGuard-AI/1.0 SIH-26073 blind-benchmark research"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_station(station_id: str) -> dict[str, str]:
    url = f"{BASE_URL}/{station_id}.csv"
    destination = OUTPUT_ROOT / f"{station_id}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    status = "reused"
    if not destination.exists() or destination.stat().st_size == 0:
        status = "downloaded"
        temporary = destination.with_suffix(".csv.part")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as output:
                while block := response.read(4 << 20):
                    output.write(block)
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    return {
        "station_id": station_id,
        "year": "2025",
        "url": url,
        "relative_path": destination.relative_to(ROOT).as_posix(),
        "bytes": str(destination.stat().st_size),
        "sha256": sha256(destination),
        "status": status,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> None:
    with CONFIG.open("r", encoding="utf-8", newline="") as handle:
        station_ids = [row["station_id"] for row in csv.DictReader(handle)]

    results: list[dict[str, str]] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(download_station, station_id): station_id for station_id in station_ids}
        for future in as_completed(futures):
            station_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"{result['status']:10s} {station_id} ({int(result['bytes']):,} bytes)")
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                failures.append(f"{station_id}: {exc}")
                print(f"failed     {station_id}: {exc}")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    fields = ["station_id", "year", "url", "relative_path", "bytes", "sha256", "status", "checked_at_utc"]
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda row: row["station_id"]))

    if failures or len(results) != len(station_ids):
        raise SystemExit(f"Blind download incomplete: {len(results)}/{len(station_ids)} files. {failures}")
    print(f"PASS: {len(results)} official NOAA station files; manifest={MANIFEST}")


if __name__ == "__main__":
    main()

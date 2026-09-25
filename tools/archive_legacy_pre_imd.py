"""Create a recoverable, checksummed archive of pre-official-IMD artifacts.

Dry-run is the default. Use --apply only after a successful authenticated IMD
snapshot has been collected. Files are copied, not deleted or moved, so the
current website keeps working during the cutover.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    "config/all_india_aws_network.csv",
    "data/stations/imd_aws_master.csv",
    "data/live/latest.json",
    "data/live/raw_metar.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Copy allowlisted files into the archive")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = ROOT / "data" / "archive" / f"pre_imd_api_{stamp}"
    entries = []
    for relative in TARGETS:
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT.resolve()):
            raise RuntimeError(f"Refusing path outside repository: {source}")
        if not source.is_file():
            continue
        entries.append({"path": relative, "bytes": source.stat().st_size, "sha256": sha256(source)})
        if args.apply:
            destination = archive / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "copy; originals retained",
        "reason": "pre-official-IMD-API baseline",
        "files": entries,
    }
    if args.apply:
        archive.mkdir(parents=True, exist_ok=True)
        (archive / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Archived {len(entries)} files to {archive}")
    else:
        print(json.dumps({"dry_run": True, "planned_archive": str(archive), **manifest}, indent=2))


if __name__ == "__main__":
    main()

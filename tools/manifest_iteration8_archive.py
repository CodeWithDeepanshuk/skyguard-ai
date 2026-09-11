"""Write an immutable SHA-256 manifest for the returned Iteration 8 archive."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "reports" / "gpu_iterations" / "iteration8_returned_2026-08-29"
MANIFEST = ARCHIVE / "archive_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    files = []
    for path in sorted(ARCHIVE.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path == MANIFEST:
            continue
        files.append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "iteration": 8,
        "archive_date": date(2026, 8, 29).isoformat(),
        "source": "user-returned completed Colab artifacts",
        "immutable_checkpoint": True,
        "file_count": len(files),
        "files": files,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "manifest": str(MANIFEST),
        "file_count": len(files),
    }, indent=2))


if __name__ == "__main__":
    main()

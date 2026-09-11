"""Create the integrity-checked Google Drive data bundle for the GPU notebook."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "deliverables" / "SkyGuard_GPU_Data_Bundle.zip"
FILES = [
    "data/features_phase10/train_features.csv.gz",
    "data/features_phase10/validation_features.csv.gz",
    "data/features_phase10/time_test_features.csv.gz",
    "data/features_phase10/station_test_features.csv.gz",
    "data/features_phase10/feature_spec.json",
    "models/phase10_final.joblib",
    "models/phase10_tcn.pt",
    "reports/phase10_final.json",
    "reports/data_validation.json",
    "reports/fault_injection.json",
    "data/labelled/episodes.csv",
]


def sha256(path: Path, chunk_size: int = 4 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


missing = [name for name in FILES if not (ROOT / name).exists()]
if missing:
    raise FileNotFoundError(f"Missing required bundle files: {missing}")

manifest = {
    "bundle": "SkyGuard_GPU_Data_Bundle",
    "purpose": "SIH 26073 leakage-safe GPU model iterations",
    "files": [
        {
            "path": name,
            "bytes": (ROOT / name).stat().st_size,
            "sha256": sha256(ROOT / name),
        }
        for name in FILES
    ],
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="skyguard_gpu_bundle_") as temp_name:
    bundle_root = Path(temp_name) / "SkyGuard_GPU_Data_Bundle"
    for name in FILES:
        destination = bundle_root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    (bundle_root / "bundle_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for path in sorted(bundle_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(Path(temp_name)))

print(OUTPUT)
print(f"bytes={OUTPUT.stat().st_size}")
print(f"sha256={sha256(OUTPUT)}")

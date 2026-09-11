"""Build the complete, self-contained SkyGuard Iteration 11 All-India Starter Bundle.

Includes:
- All-India 543-station catalog (config/all_india_aws_network.csv)
- Development stations (config/india_stations.csv) matching india_aws_2022_2023.csv.gz
- Split contracts and validation reports (both iteration10 and iteration11 names)
- Iteration 9 baseline benchmark reference files
- All SkyGuard runtime, features, faults, incidents, and evaluation modules
- Strict bundle_manifest.json with SHA-256 integrity verification
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "SkyGuard_Iteration11_All_India_545_Stations_Bundle.zip"
PREFIX = Path("SkyGuard_Iteration11_All_India_545_Stations_Bundle")

FILES: tuple[tuple[Path, Path], ...] = (
    # All-India 543 stations catalog
    (
        ROOT / "config" / "all_india_aws_network.csv",
        Path("config/all_india_aws_network.csv"),
    ),
    # 24 core development stations matching the observation table
    (
        ROOT / "data" / "iteration10" / "config" / "india_stations.csv",
        Path("config/india_stations.csv"),
    ),
    (
        ROOT / "data" / "iteration10" / "processed" / "india_aws_2022_2023.csv.gz",
        Path("data/india_aws_2022_2023.csv.gz"),
    ),
    (
        ROOT / "data" / "iteration10" / "config" / "split_contract.json",
        Path("config/split_contract.json"),
    ),
    (
        ROOT / "data" / "iteration10" / "manifest" / "india_development_files.csv",
        Path("manifest/india_development_files.csv"),
    ),
    # Reports (both names for complete backward & forward compatibility)
    (
        ROOT / "reports" / "iteration10_india_data_validation.json",
        Path("reports/iteration10_india_data_validation.json"),
    ),
    (
        ROOT / "reports" / "iteration10_india_data_validation.json",
        Path("reports/iteration11_india_data_validation.json"),
    ),
    (
        ROOT / "reports" / "iteration10_india_data_validation.md",
        Path("reports/iteration10_india_data_validation.md"),
    ),
    (
        ROOT / "reports" / "iteration10_india_data_validation.md",
        Path("reports/iteration11_india_data_validation.md"),
    ),
    (
        ROOT / "docs" / "SKYGUARD_FINAL_COMPLETION_MASTER_PROMPT.md",
        Path("docs/SKYGUARD_FINAL_COMPLETION_MASTER_PROMPT.md"),
    ),
    # Core SkyGuard packages
    (ROOT / "src" / "skyguard" / "__init__.py", Path("src/skyguard/__init__.py")),
    (ROOT / "src" / "skyguard" / "features" / "__init__.py", Path("src/skyguard/features/__init__.py")),
    (ROOT / "src" / "skyguard" / "features" / "contracts.py", Path("src/skyguard/features/contracts.py")),
    (ROOT / "src" / "skyguard" / "features" / "builder.py", Path("src/skyguard/features/builder.py")),
    (ROOT / "src" / "skyguard" / "features" / "neighbors.py", Path("src/skyguard/features/neighbors.py")),
    (ROOT / "src" / "skyguard" / "features" / "temporal.py", Path("src/skyguard/features/temporal.py")),
    (ROOT / "src" / "skyguard" / "features" / "phase10.py", Path("src/skyguard/features/phase10.py")),
    (ROOT / "src" / "skyguard" / "features" / "spatial_qc.py", Path("src/skyguard/features/spatial_qc.py")),
    (ROOT / "src" / "skyguard" / "faults" / "__init__.py", Path("src/skyguard/faults/__init__.py")),
    (ROOT / "src" / "skyguard" / "faults" / "curriculum.py", Path("src/skyguard/faults/curriculum.py")),
    (ROOT / "src" / "skyguard" / "faults" / "injector.py", Path("src/skyguard/faults/injector.py")),
    (ROOT / "src" / "skyguard" / "faults" / "models.py", Path("src/skyguard/faults/models.py")),
    (ROOT / "src" / "skyguard" / "incidents" / "__init__.py", Path("src/skyguard/incidents/__init__.py")),
    (ROOT / "src" / "skyguard" / "incidents" / "triage.py", Path("src/skyguard/incidents/triage.py")),
    (ROOT / "src" / "skyguard" / "incidents" / "state.py", Path("src/skyguard/incidents/state.py")),
    (ROOT / "src" / "skyguard" / "incidents" / "drift.py", Path("src/skyguard/incidents/drift.py")),
    (ROOT / "src" / "skyguard" / "incidents" / "diagnosis.py", Path("src/skyguard/incidents/diagnosis.py")),
    (ROOT / "src" / "skyguard" / "evaluation" / "__init__.py", Path("src/skyguard/evaluation/__init__.py")),
    (
        ROOT / "src" / "skyguard" / "evaluation" / "incident_metrics.py",
        Path("src/skyguard/evaluation/incident_metrics.py"),
    ),
)

REFERENCE_DIR = ROOT / "reports" / "gpu_iterations" / "iteration9_returned_2026-08-30"
REFERENCE_PATTERNS = (
    "iteration9_result_block.json",
    "iteration9_problem_coverage.json",
    "iteration9_integrity_receipt.json",
    "iteration9_feature_contract.json",
    "iteration9_multidomain_confirmation.csv",
    "iteration9_fault_episode_recall.csv",
    "iteration9_root_cause_metrics.csv",
    "iteration9_seed_confidence_intervals.csv",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> str:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    selected = list(FILES)

    # Add reference iteration9 files
    for name in REFERENCE_PATTERNS:
        source_path = REFERENCE_DIR / name
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing reference file: {source_path}")
        selected.append((source_path, Path("reference/iteration9") / name))

    for source_path, _ in selected:
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing required file: {source_path}")

    manifest = {
        "bundle": "SkyGuard Iteration 11 All India 545 Stations Starter Bundle",
        "purpose": "development-only incident-intelligence training and confirmation across all 8 Indian climate zones",
        "development_years": [2022, 2023],
        "locked_observation_years_included": [],
        "locked_years": [2024, 2025],
        "station_count": 543,
        "files": [
            {
                "path": relative.as_posix(),
                "bytes": source_path.stat().st_size,
                "sha256": sha256(source_path),
            }
            for source_path, relative in selected
        ],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr((PREFIX / "bundle_manifest.json").as_posix(), manifest_bytes)
        for source_path, relative in selected:
            archive.write(source_path, (PREFIX / relative).as_posix())

    digest = sha256(OUT)
    print(f"Created {OUT.name}")
    print(f"Size: {round(OUT.stat().st_size / (1024*1024), 2)} MB")
    print(f"SHA-256: {digest}")
    print(f"Total files in bundle: {len(selected) + 1}")
    return digest


if __name__ == "__main__":
    main()

"""Build the self-contained Iteration 10 development starter bundle.

The bundle deliberately contains development years 2022-2023 only.  Locked
2024/2025 observations and blind-test artefacts are forbidden.  Iteration 9
metrics/models are included only as a frozen reference; Iteration 10 trains new
models and may not inherit Iteration 9's promotion decision.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "SkyGuard_Iteration10_Final_Starter_Bundle.zip"
PREFIX = Path("SkyGuard_Iteration10_Final_Starter_Bundle")


FILES: tuple[tuple[Path, Path], ...] = (
    (
        ROOT / "data" / "iteration10" / "processed" / "india_aws_2022_2023.csv.gz",
        Path("data/india_aws_2022_2023.csv.gz"),
    ),
    (
        ROOT / "data" / "iteration10" / "config" / "india_stations.csv",
        Path("config/india_stations.csv"),
    ),
    (
        ROOT / "data" / "iteration10" / "config" / "split_contract.json",
        Path("config/split_contract.json"),
    ),
    (
        ROOT / "data" / "iteration10" / "manifest" / "india_development_files.csv",
        Path("manifest/india_development_files.csv"),
    ),
    (
        ROOT / "reports" / "iteration10_india_data_validation.json",
        Path("reports/iteration10_india_data_validation.json"),
    ),
    (
        ROOT / "reports" / "iteration10_india_data_validation.md",
        Path("reports/iteration10_india_data_validation.md"),
    ),
    (
        ROOT / "docs" / "SKYGUARD_FINAL_COMPLETION_MASTER_PROMPT.md",
        Path("docs/SKYGUARD_FINAL_COMPLETION_MASTER_PROMPT.md"),
    ),
    (ROOT / "src" / "skyguard" / "__init__.py", Path("src/skyguard/__init__.py")),
    (ROOT / "src" / "skyguard" / "features" / "__init__.py", Path("src/skyguard/features/__init__.py")),
    (ROOT / "src" / "skyguard" / "features" / "contracts.py", Path("src/skyguard/features/contracts.py")),
    (ROOT / "src" / "skyguard" / "features" / "builder.py", Path("src/skyguard/features/builder.py")),
    (ROOT / "src" / "skyguard" / "features" / "neighbors.py", Path("src/skyguard/features/neighbors.py")),
    (ROOT / "src" / "skyguard" / "features" / "temporal.py", Path("src/skyguard/features/temporal.py")),
    (ROOT / "src" / "skyguard" / "features" / "phase10.py", Path("src/skyguard/features/phase10.py")),
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


def main() -> None:
    missing = [str(source) for source, _ in FILES if not source.is_file()]
    if missing:
        raise FileNotFoundError(f"Required Iteration 10 files are missing: {missing}")

    selected = list(FILES)
    for name in REFERENCE_PATTERNS:
        source = REFERENCE_DIR / name
        if not source.is_file():
            raise FileNotFoundError(source)
        selected.append((source, Path("reference/iteration9") / name))

    forbidden = [
        str(relative)
        for _source, relative in selected
        if "2024" in relative.as_posix().lower() or "2025" in relative.as_posix().lower()
    ]
    if forbidden:
        raise RuntimeError(f"Locked-year filenames cannot enter the bundle: {forbidden}")

    manifest = {
        "bundle": "SkyGuard Iteration 10 Final Starter Bundle",
        "purpose": "development-only incident-intelligence training and confirmation",
        "development_years": [2022, 2023],
        "locked_observation_years_included": [],
        "locked_years": [2024, 2025],
        "iteration9_reference_is_deployment_authority": False,
        "files": [
            {
                "path": relative.as_posix(),
                "bytes": source.stat().st_size,
                "sha256": sha256(source),
            }
            for source, relative in selected
        ],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr((PREFIX / "bundle_manifest.json").as_posix(), manifest_bytes)
        for source, relative in selected:
            archive.write(source, (PREFIX / relative).as_posix())

    print(json.dumps({
        "path": str(OUT),
        "bytes": OUT.stat().st_size,
        "sha256": sha256(OUT),
        "files": len(selected) + 1,
        "locked_observation_years_included": [],
    }, indent=2))


if __name__ == "__main__":
    main()

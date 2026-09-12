"""Build the complete, self-contained SkyGuard Final Ultimate Starter Bundle.

Includes:
- All-India 543-station catalog (config/all_india_aws_network.csv)
- Development observation data (data/india_aws_2022_2023.csv.gz)
- Split contracts and validation reports
- 25 Promotion gates registry (config/promotion_gates.yaml)
- All SkyGuard core packages:
  - Transport gap separation (src/skyguard/data/transport_status.py)
  - Quantization-aware freeze detection (src/skyguard/features/freeze.py)
  - Spatial QC & weather coherence veto (src/skyguard/features/spatial_qc.py)
  - Elevation-invariant pressure tendency (src/skyguard/features/pressure_tendency.py)
  - Two-sided CUSUM drift specialist (src/skyguard/features/drift_cusum.py)
  - Persistence incident state machine (src/skyguard/incidents/state_machine.py)
  - Controlled ablation framework (src/skyguard/evaluation/ablation.py)
- Reference benchmark artifacts from Iteration 9 and Iteration 11
- Master reproduction tool (tools/reproduce_final.py)
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "SkyGuard_Final_Ultimate_Bundle.zip"
PREFIX = Path("SkyGuard_Final_Ultimate_Bundle")

FILES = [
    # Station network & data
    (ROOT / "config" / "all_india_aws_network.csv", Path("config/all_india_aws_network.csv")),
    (ROOT / "data" / "iteration10" / "config" / "india_stations.csv", Path("config/india_stations.csv")),
    (ROOT / "data" / "iteration10" / "processed" / "india_aws_2022_2023.csv.gz", Path("data/india_aws_2022_2023.csv.gz")),
    (ROOT / "data" / "iteration10" / "config" / "split_contract.json", Path("config/split_contract.json")),
    (ROOT / "data" / "iteration10" / "manifest" / "india_development_files.csv", Path("manifest/india_development_files.csv")),
    (ROOT / "config" / "promotion_gates.yaml", Path("config/promotion_gates.yaml")),

    # Python core modules
    (ROOT / "src" / "skyguard" / "__init__.py", Path("src/skyguard/__init__.py")),
    (ROOT / "src" / "skyguard" / "data" / "__init__.py", Path("src/skyguard/data/__init__.py")),
    (ROOT / "src" / "skyguard" / "data" / "transport_status.py", Path("src/skyguard/data/transport_status.py")),
    (ROOT / "src" / "skyguard" / "features" / "__init__.py", Path("src/skyguard/features/__init__.py")),
    (ROOT / "src" / "skyguard" / "features" / "freeze.py", Path("src/skyguard/features/freeze.py")),
    (ROOT / "src" / "skyguard" / "features" / "spatial_qc.py", Path("src/skyguard/features/spatial_qc.py")),
    (ROOT / "src" / "skyguard" / "features" / "pressure_tendency.py", Path("src/skyguard/features/pressure_tendency.py")),
    (ROOT / "src" / "skyguard" / "features" / "drift_cusum.py", Path("src/skyguard/features/drift_cusum.py")),
    (ROOT / "src" / "skyguard" / "features" / "contracts.py", Path("src/skyguard/features/contracts.py")),
    (ROOT / "src" / "skyguard" / "features" / "builder.py", Path("src/skyguard/features/builder.py")),
    (ROOT / "src" / "skyguard" / "features" / "temporal.py", Path("src/skyguard/features/temporal.py")),
    (ROOT / "src" / "skyguard" / "features" / "neighbors.py", Path("src/skyguard/features/neighbors.py")),
    (ROOT / "src" / "skyguard" / "incidents" / "__init__.py", Path("src/skyguard/incidents/__init__.py")),
    (ROOT / "src" / "skyguard" / "incidents" / "state_machine.py", Path("src/skyguard/incidents/state_machine.py")),
    (ROOT / "src" / "skyguard" / "incidents" / "triage.py", Path("src/skyguard/incidents/triage.py")),
    (ROOT / "src" / "skyguard" / "evaluation" / "__init__.py", Path("src/skyguard/evaluation/__init__.py")),
    (ROOT / "src" / "skyguard" / "evaluation" / "ablation.py", Path("src/skyguard/evaluation/ablation.py")),
    (ROOT / "src" / "skyguard" / "evaluation" / "incident_metrics.py", Path("src/skyguard/evaluation/incident_metrics.py")),

    # Tools & reports
    (ROOT / "tools" / "reproduce_final.py", Path("tools/reproduce_final.py")),
    (ROOT / "reports" / "final_evaluation" / "ablation_study.csv", Path("reports/ablation_study.csv")),
    (ROOT / "reports" / "final_evaluation" / "gate_results.json", Path("reports/gate_results.json")),
]

# Add Iteration 9 reference files
REF_I9 = ROOT / "reports" / "gpu_iterations" / "iteration9_returned_2026-08-30"
for name in ("iteration9_result_block.json", "iteration9_feature_contract.json", "iteration9_multidomain_confirmation.csv"):
    p = REF_I9 / name
    if p.is_file():
        FILES.append((p, Path("reference/iteration9") / name))

# Add Iteration 11 reference files
REF_I11 = ROOT / "iteration 11 result"
for name in ("iteration11_result_block.json", "iteration11_policy_frontier.csv", "iteration11_multidomain_confirmation.csv"):
    p = REF_I11 / name
    if p.is_file():
        FILES.append((p, Path("reference/iteration11") / name))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> str:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "bundle": "SkyGuard Final Ultimate Starter Bundle",
        "purpose": "Scientific operational anomaly detection and 25 promotion gates validation (SIH 26073)",
        "development_years": [2022, 2023],
        "locked_observation_years_included": [],
        "locked_years": [2024, 2025],
        "station_count": 543,
        "files": [
            {
                "path": rel.as_posix(),
                "bytes": src.stat().st_size,
                "sha256": sha256(src),
            }
            for src, rel in FILES if src.is_file()
        ],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr((PREFIX / "bundle_manifest.json").as_posix(), manifest_bytes)
        for src, rel in FILES:
            if src.is_file():
                archive.write(src, (PREFIX / rel).as_posix())

    bundle_hash = sha256(OUT)
    print(f"Created {OUT.name} ({OUT.stat().st_size / (1024*1024):.2f} MB)")
    print(f"SHA-256: {bundle_hash}")
    return bundle_hash


if __name__ == "__main__":
    main()

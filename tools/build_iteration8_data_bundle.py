"""Build development and locked-confirmation bundles for GPU Iteration 8."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES = ROOT / "deliverables"
DEVELOPMENT_ZIP = DELIVERABLES / "SkyGuard_Iteration8_Development_Data_Bundle.zip"
LOCKED_ZIP = DELIVERABLES / "SkyGuard_Iteration8_Locked_2024_Confirmation.zip"
REPORT = ROOT / "reports" / "iteration8_bundle_build.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def member(path: Path, target: str) -> dict[str, object]:
    return {
        "source": path,
        "target": target,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def write_bundle(output: Path, root_name: str, members: list[dict[str, object]], metadata: dict[str, object]) -> dict[str, object]:
    manifest = {
        **metadata,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [
            {"relative_path": item["target"], "bytes": item["bytes"], "sha256": item["sha256"]}
            for item in members
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(f"{root_name}/bundle_manifest.json", json.dumps(manifest, indent=2))
        for item in members:
            archive.write(item["source"], f"{root_name}/{item['target']}")
    return {
        "path": output.relative_to(ROOT).as_posix(),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "members": len(members) + 1,
    }


def main() -> None:
    feature_files = [
        ROOT / "src" / "skyguard" / "__init__.py",
        ROOT / "src" / "skyguard" / "features" / "__init__.py",
        ROOT / "src" / "skyguard" / "features" / "contracts.py",
        ROOT / "src" / "skyguard" / "features" / "builder.py",
        ROOT / "src" / "skyguard" / "features" / "neighbors.py",
        ROOT / "src" / "skyguard" / "features" / "temporal.py",
        ROOT / "src" / "skyguard" / "features" / "phase10.py",
        ROOT / "src" / "skyguard" / "faults" / "__init__.py",
        ROOT / "src" / "skyguard" / "faults" / "curriculum.py",
    ]
    development_members = [
        member(ROOT / "data" / "iteration8" / "processed" / "dwd_aws_10min_2022.csv.gz", "data/dwd_aws_10min_2022.csv.gz"),
        member(ROOT / "data" / "iteration8" / "processed" / "dwd_aws_10min_2023.csv.gz", "data/dwd_aws_10min_2023.csv.gz"),
        member(ROOT / "config" / "iteration8_dwd_stations.csv", "config/iteration8_dwd_stations.csv"),
        member(ROOT / "config" / "iteration8_data_sources.json", "config/iteration8_data_sources.json"),
        member(ROOT / "data" / "iteration8" / "manifest" / "dwd_raw_files.csv", "manifest/dwd_raw_files.csv"),
        member(ROOT / "data" / "iteration8" / "manifest" / "dwd_processed_files.csv", "manifest/dwd_processed_files.csv"),
        member(ROOT / "reports" / "iteration8_dwd_data_validation.json", "reports/iteration8_dwd_data_validation.json"),
        member(ROOT / "reports" / "iteration8_dwd_data_validation.md", "reports/iteration8_dwd_data_validation.md"),
        member(ROOT / "data" / "iteration8" / "raw" / "dwd" / "metadata" / "zehn_min_tu_Beschreibung_Stationen.txt", "documentation/zehn_min_tu_Beschreibung_Stationen.txt"),
        member(ROOT / "data" / "iteration8" / "raw" / "dwd" / "metadata" / "DESCRIPTION_obsgermany_climate_10min_air_temperature_en.pdf", "documentation/DWD_10min_TU_description_en.pdf"),
    ]
    for path in feature_files:
        target = path.relative_to(ROOT / "src").as_posix()
        development_members.append(member(path, f"src/{target}"))

    development = write_bundle(
        DEVELOPMENT_ZIP,
        "SkyGuard_Iteration8_Development_Data_Bundle",
        development_members,
        {
            "bundle": "SkyGuard Iteration 8 development data",
            "provider": "Deutscher Wetterdienst (DWD)",
            "development_years": [2022, 2023],
            "contains_2024_observations": False,
            "contains_2025_observations": False,
            "station_count": 16,
            "cluster_count": 4,
            "cadence_minutes": 10,
            "observation_inputs": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
        },
    )

    locked_file = ROOT / "data" / "iteration8" / "processed" / "dwd_aws_10min_2024.csv.gz"
    lock_receipt = {
        "status": "LOCKED",
        "year": 2024,
        "role": "external_confirmation_locked",
        "open_only_after_model_and_threshold_freeze": True,
        "contains_2025_observations": False,
        "data_sha256": sha256(locked_file),
    }
    lock_receipt_path = ROOT / "reports" / "iteration8_2024_lock_receipt.json"
    lock_receipt_path.write_text(json.dumps(lock_receipt, indent=2), encoding="utf-8")
    locked = write_bundle(
        LOCKED_ZIP,
        "SkyGuard_Iteration8_Locked_2024_Confirmation",
        [
            member(locked_file, "data/dwd_aws_10min_2024.csv.gz"),
            member(lock_receipt_path, "lock_receipt.json"),
        ],
        {
            "bundle": "SkyGuard Iteration 8 locked external confirmation",
            "status": "LOCKED",
            "year": 2024,
            "contains_2025_observations": False,
        },
    )
    report = {"development": development, "locked_2024": locked}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

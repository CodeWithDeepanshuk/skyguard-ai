"""Package the final Iteration 10 Colab, both approved bundles, and guides."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "SkyGuard_Iteration10_Complete_Colab_Execution_Package.zip"
PREFIX = Path("SkyGuard_Iteration10_Complete_Colab_Execution_Package")
FILES = (
    ROOT / "deliverables" / "SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb",
    ROOT / "deliverables" / "SkyGuard_Iteration10_Final_Starter_Bundle.zip",
    ROOT / "deliverables" / "SkyGuard_Iteration8_Development_Data_Bundle.zip",
    ROOT / "docs" / "ITERATION10_COLAB_EXECUTION_GUIDE_ROMAN_HINDI.md",
    ROOT / "docs" / "SKYGUARD_FINAL_COMPLETION_MASTER_PROMPT.md",
    ROOT / "reports" / "iteration10_india_data_validation.json",
    ROOT / "reports" / "iteration10_india_data_validation.md",
    ROOT / "reports" / "ITERATION_10_FINAL_IMPLEMENTATION_AUDIT.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    missing = [str(path) for path in FILES if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    manifest = {
        "package": "SkyGuard Iteration 10 Complete Colab Execution Package",
        "development_years": [2022, 2023],
        "locked_observation_years_included": [],
        "automatic_deployment": False,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in FILES
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
        archive.writestr((PREFIX / "package_manifest.json").as_posix(),
                         json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        for path in FILES:
            folder = "guides" if path.suffix.lower() == ".md" else (
                "reports" if path.parent.name == "reports" else "run_files"
            )
            archive.write(path, (PREFIX / folder / path.name).as_posix())
    print(json.dumps({"path": str(OUT), "bytes": OUT.stat().st_size,
                      "sha256": sha256(OUT), "files": len(FILES) + 1}, indent=2))


if __name__ == "__main__":
    main()

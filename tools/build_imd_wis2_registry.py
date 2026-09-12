"""Build verified master AWS registry merging IMD WIS2, All-India AWS, and Airport METARs."""
from __future__ import annotations

from pathlib import Path
from skyguard.stations.registry import MasterStationRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    registry = MasterStationRegistry(root=ROOT)
    registry.build_master_catalog()
    audit = registry.coverage_audit()
    print(
        f"verified_registry_rows={audit['verified_in_situ_stations']} "
        f"target_claimed={audit['target_national_aws_coverage']} "
        f"coverage={audit['coverage_percentage']}% "
        f"path={registry.master_path}"
    )


if __name__ == "__main__":
    main()

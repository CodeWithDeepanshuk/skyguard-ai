"""Generate causal SkyGuard feature tables for every labelled split."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.features.builder import FeatureBuilder  # noqa: E402
from skyguard.features.contracts import (  # noqa: E402
    AUDIT_COLUMNS, FeatureConfig, IDENTITY_COLUMNS, LABEL_COLUMNS, MODEL_FEATURE_COLUMNS, OUTPUT_COLUMNS,
)
from skyguard.features.neighbors import NeighborIndex  # noqa: E402
from skyguard.features.temporal import TemporalFeatureBuilder  # noqa: E402


LABELLED = ROOT / "data" / "labelled"
OUTPUT_DIR = ROOT / "data" / "features"
CONFIG_FILE = ROOT / "config" / "stations.csv"
QC_REPORT = ROOT / "reports" / "qc_baseline.json"
MANIFEST = OUTPUT_DIR / "manifest.csv"
SPEC = OUTPUT_DIR / "feature_spec.json"
REPORT_JSON = ROOT / "reports" / "feature_generation.json"
REPORT_MD = ROOT / "reports" / "feature_generation.md"
SPLITS = ("train", "validation", "time_test", "station_test")


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_stations() -> dict[str, dict[str, str]]:
    with CONFIG_FILE.open("r", encoding="utf-8", newline="") as handle:
        return {row["station_id"]: row for row in csv.DictReader(handle)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard feature-generation report",
        "",
        f"- Model feature columns: {report['model_feature_count']}",
        f"- Label columns excluded from model inputs: {report['label_feature_overlap'] == []}",
        f"- Total rows transformed: {report['total_rows']:,}",
        f"- Generation time: {report['generation_seconds']:.2f} seconds",
        "",
        "## Outputs",
        "",
        "| Split | Rows | Compressed bytes | Neighbour context |",
        "|---|---:|---:|---|",
    ]
    for split, values in report["splits"].items():
        lines.append(f"| {split} | {values['rows']:,} | {values['bytes']:,} | {values['neighbor_context']} |")
    lines.extend([
        "",
        "All rolling and EWMA statistics use prior observations only. Neighbour alignment selects the latest observation at or before the query timestamp within 180 minutes. The station-holdout split uses 2024 development stations as value-only neighbour context.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    stations = load_stations()
    qc = json.loads(QC_REPORT.read_text(encoding="utf-8"))
    expected_intervals = {key: float(value) for key, value in qc["expected_interval_minutes"].items()}
    config = FeatureConfig()
    started = time.perf_counter()
    outputs: list[Path] = []
    split_reports: dict[str, dict[str, object]] = {}
    time_test_context: list[dict[str, str]] | None = None

    for split in SPLITS:
        rows = load_csv(LABELLED / f"{split}.csv")
        if split == "time_test":
            time_test_context = rows
        if split == "station_test":
            if time_test_context is None:
                time_test_context = load_csv(LABELLED / "time_test.csv")
            context_rows = time_test_context
            context_name = "time_test development stations"
        else:
            context_rows = rows
            context_name = f"{split} stations"

        builder = FeatureBuilder(
            TemporalFeatureBuilder(expected_intervals, config),
            NeighborIndex(context_rows, stations, config),
        )
        output = OUTPUT_DIR / f"{split}_features.csv.gz"
        with gzip.open(output, "wt", encoding="utf-8", newline="", compresslevel=6) as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(builder.transform(row))
        outputs.append(output)
        split_reports[split] = {
            "rows": len(rows),
            "bytes": output.stat().st_size,
            "sha256": sha256(output),
            "neighbor_context": context_name,
            "output": output.relative_to(ROOT).as_posix(),
        }
        print(f"{split}: {len(rows):,} rows -> {output.stat().st_size:,} compressed bytes")

    feature_spec = {
        "feature_config": asdict(config),
        "identity_columns": list(IDENTITY_COLUMNS),
        "model_feature_columns": list(MODEL_FEATURE_COLUMNS),
        "label_columns": list(LABEL_COLUMNS),
        "audit_columns": list(AUDIT_COLUMNS),
        "output_columns": list(OUTPUT_COLUMNS),
        "causality_rule": "Only prior station observations and neighbour observations at or before the query timestamp may be used.",
        "station_test_neighbor_context": "2024 development-station values from time_test; label and audit columns are not accessed.",
    }
    SPEC.write_text(json.dumps(feature_spec, indent=2), encoding="utf-8")
    outputs.append(SPEC)

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
        writer.writeheader()
        for output in outputs:
            writer.writerow({
                "relative_path": output.relative_to(ROOT).as_posix(),
                "bytes": output.stat().st_size,
                "sha256": sha256(output),
            })

    label_overlap = sorted(set(MODEL_FEATURE_COLUMNS) & set(LABEL_COLUMNS + AUDIT_COLUMNS))
    report = {
        "model_feature_count": len(MODEL_FEATURE_COLUMNS),
        "label_feature_overlap": label_overlap,
        "total_rows": sum(values["rows"] for values in split_reports.values()),
        "generation_seconds": round(time.perf_counter() - started, 4),
        "splits": split_reports,
        "feature_spec": SPEC.relative_to(ROOT).as_posix(),
        "manifest": MANIFEST.relative_to(ROOT).as_posix(),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

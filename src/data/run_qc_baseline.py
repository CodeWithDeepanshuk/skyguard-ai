"""Run deterministic SkyGuard quality control over the canonical benchmark."""

from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.quality.engine import QualityControlEngine  # noqa: E402
from skyguard.quality.models import Alert, Observation, QualityThresholds  # noqa: E402


DATA = ROOT / "data" / "processed" / "aws_observations_2022_2024.csv"
ALERTS = ROOT / "data" / "processed" / "qc_alerts_2022_2024.csv"
REPORT_JSON = ROOT / "reports" / "qc_baseline.json"
REPORT_MD = ROOT / "reports" / "qc_baseline.md"


def estimate_cadence() -> dict[str, float]:
    timestamps: defaultdict[str, list[datetime]] = defaultdict(list)
    with DATA.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["year"] == "2022":
                timestamps[row["station_id"]].append(datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z")))
    cadence: dict[str, float] = {}
    for station_id, values in timestamps.items():
        values.sort()
        positive_gaps = [
            (right - left).total_seconds() / 60.0
            for left, right in zip(values, values[1:])
            if right > left and (right - left).total_seconds() <= 24 * 3600
        ]
        if positive_gaps:
            cadence[station_id] = round(median(positive_gaps), 2)
    return cadence


def serializable_thresholds(thresholds: QualityThresholds) -> dict[str, object]:
    values = asdict(thresholds)
    for key, value in values.items():
        if isinstance(value, frozenset):
            values[key] = sorted(value)
    return values


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# SkyGuard deterministic QC baseline",
        "",
        "This is an alert-profile report on genuine observations, not an accuracy report. Precision and recall require the labelled fault-injection dataset built in Phase 2.",
        "",
        "## Summary",
        "",
        f"- Observations processed: {report['observations']:,}",
        f"- Alerts generated: {report['alerts']:,}",
        f"- Alerts per 1,000 observations: {report['alerts_per_1000_observations']:.3f}",
        f"- Processing time: {report['processing_seconds']:.2f} seconds",
        f"- Throughput: {report['observations_per_second']:,.0f} observations/second",
        "",
        "## Alerts by rule",
        "",
        "| Rule | Alerts |",
        "|---|---:|",
    ]
    for key, value in report["alerts_by_rule"].items():
        lines.append(f"| {key} | {value:,} |")
    lines.extend(["", "## Alerts by severity", "", "| Severity | Alerts |", "|---|---:|"])
    for key, value in report["alerts_by_severity"].items():
        lines.append(f"| {key} | {value:,} |")
    lines.extend(["", "## Configured station cadence", "", "| Station | Expected minutes |", "|---|---:|"])
    for station_id, minutes in report["expected_interval_minutes"].items():
        lines.append(f"| {station_id} | {minutes:.2f} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "Communication gaps and frozen-value warnings may include true reporting-schedule changes. They become anomaly labels only when created by the controlled injector or independently confirmed. Thresholds must be tuned on 2023 validation data, then frozen before 2024 testing.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    cadence = estimate_cadence()
    thresholds = QualityThresholds()
    engine = QualityControlEngine(cadence, thresholds)
    ALERTS.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)

    observations = 0
    alerts_count = 0
    by_rule: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()
    by_sensor: Counter[str] = Counter()
    by_year: Counter[str] = Counter()
    by_station: Counter[str] = Counter()
    started = time.perf_counter()

    alert_fields = [
        "alert_id", "station_id", "timestamp_utc", "year", "cluster", "evaluation_role",
        "rule_code", "sensor", "severity", "score", "observed_value", "expected_condition", "explanation",
    ]
    with DATA.open("r", encoding="utf-8", newline="") as source, ALERTS.open("w", encoding="utf-8", newline="") as target:
        reader = csv.DictReader(source)
        writer = csv.DictWriter(target, fieldnames=alert_fields)
        writer.writeheader()
        for row in reader:
            observations += 1
            observation = Observation.from_mapping(row)
            for alert in engine.process(observation):
                record = alert.to_dict()
                record.update({"year": row["year"], "cluster": row["cluster"], "evaluation_role": row["evaluation_role"]})
                writer.writerow(record)
                alerts_count += 1
                by_rule[alert.rule_code] += 1
                by_severity[alert.severity] += 1
                by_sensor[alert.sensor] += 1
                by_year[row["year"]] += 1
                by_station[alert.station_id] += 1

    elapsed = time.perf_counter() - started
    report = {
        "report_type": "unlabelled_qc_alert_profile",
        "observations": observations,
        "alerts": alerts_count,
        "alerts_per_1000_observations": round(1000.0 * alerts_count / observations, 4),
        "processing_seconds": round(elapsed, 4),
        "observations_per_second": round(observations / elapsed, 2),
        "alerts_by_rule": dict(sorted(by_rule.items())),
        "alerts_by_severity": dict(sorted(by_severity.items())),
        "alerts_by_sensor": dict(sorted(by_sensor.items())),
        "alerts_by_year": dict(sorted(by_year.items())),
        "top_alert_stations": dict(by_station.most_common(10)),
        "expected_interval_minutes": dict(sorted(cadence.items())),
        "thresholds": serializable_thresholds(thresholds),
        "alerts_file": ALERTS.relative_to(ROOT).as_posix(),
        "warning": "Counts on unlabelled observations do not measure model accuracy.",
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

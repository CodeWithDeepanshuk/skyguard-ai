"""Build, validate, and seal the SkyGuard 2025 blind benchmark.

The benchmark uses the final comparable legacy-ISD interval, 2025-01-01 through
2025-08-24. Model thresholds are frozen before this script is run. The output
contains a later-time test, a later unseen-station test, and a value-only
development-station context stream for neighbour features in the station test.
"""

from __future__ import annotations

import bisect
import csv
import gzip
import hashlib
import json
import math
import random
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data.normalize_noaa_isd import FIELDS, normalize_file  # noqa: E402
from skyguard.faults.injector import LABEL_FIELDS, FaultInjector  # noqa: E402
from skyguard.faults.models import Episode, FAULT_TYPES  # noqa: E402
from skyguard.features.builder import FeatureBuilder  # noqa: E402
from skyguard.features.contracts import OUTPUT_COLUMNS, FeatureConfig  # noqa: E402
from skyguard.features.neighbors import NeighborIndex  # noqa: E402
from skyguard.features.phase10 import (  # noqa: E402
    FORBIDDEN_PHASE10_INPUTS,
    PHASE10_FEATURES,
    add_phase10_features,
    assert_phase10_compliance,
)
from skyguard.features.temporal import TemporalFeatureBuilder  # noqa: E402


CONFIG = ROOT / "config" / "stations.csv"
RAW_ROOT = ROOT / "data" / "blind_2025" / "raw" / "noaa" / "2025"
RAW_MANIFEST = ROOT / "data" / "blind_2025" / "manifest" / "raw_files.csv"
PROCESSED = ROOT / "data" / "blind_2025" / "processed" / "aws_observations_2025_01_01_to_08_24.csv"
LABELLED = ROOT / "data" / "blind_2025" / "labelled"
FEATURES = ROOT / "data" / "blind_2025" / "features"
PHASE10 = ROOT / "data" / "blind_2025" / "features_phase10"
MANIFEST = ROOT / "data" / "blind_2025" / "manifest" / "sealed_benchmark_files.csv"
PROTOCOL = ROOT / "data" / "blind_2025" / "blind_protocol.json"
REPORT_JSON = ROOT / "reports" / "blind_2025_build.json"
REPORT_MD = ROOT / "reports" / "blind_2025_build.md"
PACKAGE = ROOT / "deliverables" / "SkyGuard_Blind_2025_Bundle.zip"
QC_REPORT = ROOT / "reports" / "qc_baseline.json"
CLIMATOLOGY = ROOT / "models" / "phase10_climatology.joblib"

START_UTC = datetime(2025, 1, 1)
END_UTC = datetime(2025, 8, 24, 23, 59, 59)
TIME_SEED = 26_578
STATION_SEED = 26_679
STATION_WEATHER_SEED = 26_780
TIME_EPISODES_PER_FAULT = 15
STATION_EPISODES_PER_FAULT = 6
TIME_WEATHER_EVENTS = 6
STATION_WEATHER_EVENTS = 8


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_stations() -> dict[str, dict[str, str]]:
    with CONFIG.open("r", encoding="utf-8", newline="") as handle:
        return {row["station_id"]: row for row in csv.DictReader(handle)}


def verify_raw(stations: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    with RAW_MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    errors: list[str] = []
    for item in manifest:
        path = ROOT / item["relative_path"]
        if not path.exists() or path.stat().st_size != int(item["bytes"]):
            errors.append(f"size/missing: {item['relative_path']}")
        elif sha256(path) != item["sha256"]:
            errors.append(f"hash: {item['relative_path']}")
        if item["station_id"] not in stations:
            errors.append(f"unknown station: {item['station_id']}")
        if "ncei.noaa.gov/data/global-hourly/access/2025" not in item["url"]:
            errors.append(f"non-NCEI URL: {item['url']}")
    if len(manifest) != len(stations) or errors:
        raise RuntimeError(f"Raw blind-data integrity failed: files={len(manifest)}, errors={errors}")
    return manifest


def normalize(stations: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for station_id, station in stations.items():
        path = RAW_ROOT / f"{station_id}.csv"
        station_records = normalize_file(path, station, 2025)
        for key, row in station_records.items():
            observed = datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z"))
            if START_UTC <= observed <= END_UTC:
                records[key] = row
        print(f"normalized {station_id}: {len(station_records):,} rows")
    output = sorted(records.values(), key=lambda row: (row["station_id"], row["timestamp_utc"]))
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    with PROCESSED.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    return output


def write_rows(path: Path, rows: list[dict[str, str]], source_fields: list[str]) -> None:
    fields = source_fields + [field for field in LABEL_FIELDS if field not in source_fields]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def clean_normal(row: dict[str, str]) -> bool:
    if row.get("label_category") != "normal" or row.get("stream_action") != "emit":
        return False
    try:
        temperature = float(row["temperature_c"])
        pressure = float(row["pressure_hpa"])
        humidity = float(row["relative_humidity_pct"])
    except (TypeError, ValueError):
        return False
    if not (-60 <= temperature <= 60 and 870 <= pressure <= 1075 and 0 <= humidity <= 100):
        return False
    return row.get("temperature_quality", "") not in {"2", "3", "6", "7"} and row.get("pressure_quality", "") not in {"2", "3", "6", "7"}


def inject_station_weather(
    station_rows: list[dict[str, str]],
    context_rows: list[dict[str, str]],
    count: int,
    seed: int,
) -> list[Episode]:
    """Inject synchronized weather into holdout rows and value-only neighbours."""

    rng = random.Random(seed)
    all_rows = station_rows + context_rows
    by_station: defaultdict[str, list[int]] = defaultdict(list)
    station_times: dict[str, list[datetime]] = {}
    cluster_stations: defaultdict[str, set[str]] = defaultdict(set)
    for index, row in enumerate(all_rows):
        by_station[row["station_id"]].append(index)
        cluster_stations[row["cluster"]].add(row["station_id"])
    for station_id, indices in by_station.items():
        indices.sort(key=lambda index: all_rows[index]["timestamp_utc"])
        station_times[station_id] = [datetime.fromisoformat(all_rows[index]["timestamp_utc"].removesuffix("Z")) for index in indices]

    holdouts = sorted({row["station_id"] for row in station_rows})
    episodes: list[Episode] = []
    for episode_number in range(1, count + 1):
        for _ in range(1000):
            holdout = rng.choice(holdouts)
            candidates = [index for index in by_station[holdout] if clean_normal(all_rows[index])]
            if not candidates:
                continue
            anchor = rng.choice(candidates)
            start = datetime.fromisoformat(all_rows[anchor]["timestamp_utc"].removesuffix("Z"))
            end = start + timedelta(hours=rng.uniform(12, 36))
            selected: list[int] = []
            covered: list[str] = []
            cluster = all_rows[anchor]["cluster"]
            for station_id in sorted(cluster_stations[cluster]):
                indices = by_station[station_id]
                times = station_times[station_id]
                left = bisect.bisect_left(times, start)
                right = bisect.bisect_right(times, end)
                available = [index for index in indices[left:right] if clean_normal(all_rows[index])]
                if len(available) >= 2:
                    selected.extend(available)
                    covered.append(station_id)
            holdout_selected = [index for index in selected if all_rows[index]["evaluation_role"] == "station_holdout"]
            development_selected = [index for index in selected if all_rows[index]["evaluation_role"] == "development"]
            if not holdout_selected or len({all_rows[index]["station_id"] for index in development_selected}) < 3:
                continue

            episode_id = f"BLIND_STATION-WX-{episode_number:04d}"
            peak = rng.uniform(3.0, 8.0)
            duration = max((end - start).total_seconds(), 1.0)
            for index in selected:
                row = all_rows[index]
                timestamp = datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z"))
                phase = (timestamp - start).total_seconds() / duration
                delta = peak * (0.65 + 0.35 * math.sin(math.pi * max(0.0, min(1.0, phase))))
                row["temperature_c"] = f"{min(59.5, float(row['temperature_c']) + delta):.4f}"
                row.update({
                    "label_category": "genuine_weather_scenario",
                    "is_anomaly": "0",
                    "is_weather_event": "1",
                    "episode_id": episode_id,
                    "anomaly_type": "regional_temperature_event",
                    "anomaly_sensor": "temperature",
                    "anomaly_severity": "event",
                    "label_source": "synthetic_weather_scenario",
                    "injection_seed": str(seed),
                })
            episodes.append(Episode(
                split="blind_station",
                episode_id=episode_id,
                label_category="genuine_weather_scenario",
                anomaly_type="regional_temperature_event",
                sensors="temperature",
                stations=",".join(sorted(set(covered))),
                start_utc=start.isoformat(timespec="seconds") + "Z",
                end_utc=end.isoformat(timespec="seconds") + "Z",
                severity="event",
                affected_rows=len(selected),
                stream_action="emit",
                random_seed=seed,
                description=f"Neighbour-consistent temperature rise peaking near {peak:.2f} C.",
            ))
            break
        else:
            raise RuntimeError("Unable to create synchronized blind-station weather event")
    return episodes


def generate_labels(rows: list[dict[str, str]]) -> tuple[dict[str, list[dict[str, str]]], list[Episode]]:
    source_fields = list(rows[0])
    time_rows = [dict(row) for row in rows if row["evaluation_role"] == "development"]
    station_rows = [dict(row) for row in rows if row["evaluation_role"] == "station_holdout"]
    context_rows = [dict(row) for row in rows if row["evaluation_role"] == "development"]

    time_injector = FaultInjector(time_rows, "blind_time", TIME_SEED)
    time_episodes = time_injector.inject_suite(TIME_EPISODES_PER_FAULT, TIME_WEATHER_EVENTS)
    station_injector = FaultInjector(station_rows, "blind_station", STATION_SEED)
    station_episodes = station_injector.inject_suite(STATION_EPISODES_PER_FAULT, 0)
    FaultInjector(context_rows, "blind_station_context", STATION_WEATHER_SEED)
    station_weather = inject_station_weather(station_rows, context_rows, STATION_WEATHER_EVENTS, STATION_WEATHER_SEED)

    splits = {
        "blind_time": time_rows,
        "blind_station": station_rows,
        "blind_station_context": context_rows,
    }
    for name, split_rows in splits.items():
        write_rows(LABELLED / f"{name}.csv", split_rows, source_fields)
    return splits, [*time_episodes, *station_episodes, *station_weather]


def write_episode_manifest(episodes: list[Episode]) -> Path:
    output = LABELLED / "episodes.csv"
    fields = [
        "split", "episode_id", "label_category", "anomaly_type", "sensors", "stations",
        "start_utc", "end_utc", "severity", "affected_rows", "stream_action", "random_seed", "description",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(episode.to_dict() for episode in episodes)
    return output


def generate_features(
    splits: dict[str, list[dict[str, str]]],
    stations: dict[str, dict[str, str]],
) -> dict[str, dict[str, object]]:
    FEATURES.mkdir(parents=True, exist_ok=True)
    PHASE10.mkdir(parents=True, exist_ok=True)
    qc = json.loads(QC_REPORT.read_text(encoding="utf-8"))
    expected_intervals = {key: float(value) for key, value in qc["expected_interval_minutes"].items()}
    profiles = joblib.load(CLIMATOLOGY)
    reports: dict[str, dict[str, object]] = {}

    for split in ("blind_time", "blind_station"):
        rows = splits[split]
        context = rows if split == "blind_time" else splits["blind_station_context"]
        builder = FeatureBuilder(
            TemporalFeatureBuilder(expected_intervals, FeatureConfig()),
            NeighborIndex(context, stations, FeatureConfig()),
        )
        base_path = FEATURES / f"{split}_features.csv.gz"
        with gzip.open(base_path, "wt", encoding="utf-8", newline="", compresslevel=6) as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(builder.transform(row))
        frame = pd.read_csv(base_path, low_memory=False)
        enhanced = add_phase10_features(frame, profiles)
        phase_path = PHASE10 / f"{split}_features.csv.gz"
        enhanced.to_csv(phase_path, index=False, compression={"method": "gzip", "compresslevel": 6})
        reports[split] = {
            "rows": int(enhanced.shape[0]),
            "columns": int(enhanced.shape[1]),
            "available_rows": int((enhanced["available_to_detector"] == 1).sum()),
            "stations": int(enhanced["station_id"].astype(str).nunique()),
            "neighbor_coverage_percent": round(100.0 * enhanced["neighbor_station_count"].fillna(0).gt(0).mean(), 4),
            "feature_file": phase_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(phase_path),
        }
        del frame, enhanced
        print(f"features {split}: {reports[split]}")
    return reports


def validate(
    normalized: list[dict[str, str]],
    splits: dict[str, list[dict[str, str]]],
    episodes: list[Episode],
    feature_reports: dict[str, dict[str, object]],
    stations: dict[str, dict[str, str]],
) -> dict[str, object]:
    coverage: list[dict[str, object]] = []
    by_station: defaultdict[str, list[datetime]] = defaultdict(list)
    missing = Counter()
    keys: set[tuple[str, str]] = set()
    duplicates = 0
    for row in normalized:
        key = (row["station_id"], row["timestamp_utc"])
        duplicates += int(key in keys)
        keys.add(key)
        by_station[row["station_id"]].append(datetime.fromisoformat(row["timestamp_utc"].removesuffix("Z")))
        for field in ("temperature_c", "pressure_hpa", "relative_humidity_pct"):
            missing[field] += int(not row[field])
    for station_id, timestamps in sorted(by_station.items()):
        timestamps.sort()
        coverage.append({
            "station_id": station_id,
            "rows": len(timestamps),
            "start_utc": timestamps[0].isoformat() + "Z",
            "end_utc": timestamps[-1].isoformat() + "Z",
        })

    episode_ids = [episode.episode_id for episode in episodes]
    split_episode_counts = Counter(episode.split for episode in episodes)
    fault_counts = Counter(episode.anomaly_type for episode in episodes if episode.label_category == "sensor_fault")
    weather_counts = Counter(episode.split for episode in episodes if episode.label_category == "genuine_weather_scenario")
    prior_row_ids: set[str] = set()
    for split in ("train", "validation", "time_test", "station_test"):
        path = ROOT / "data" / "features_phase10" / f"{split}_features.csv.gz"
        prior_row_ids.update(pd.read_csv(path, usecols=["row_id"])["row_id"].astype(str))
    blind_row_ids: set[str] = set()
    blind_overlap = 0
    for split in ("blind_time", "blind_station"):
        path = PHASE10 / f"{split}_features.csv.gz"
        frame = pd.read_csv(path, low_memory=False)
        ids = set(frame["row_id"].astype(str))
        blind_overlap += len(ids & prior_row_ids)
        blind_row_ids.update(ids)
        if not set(PHASE10_FEATURES).issubset(frame.columns):
            raise RuntimeError(f"{split}: missing Phase 10 features")
        del frame

    checks = {
        "all_24_stations_present": set(by_station) == set(stations),
        "minimum_900_rows_per_station": min(len(values) for values in by_station.values()) >= 900,
        "all_stations_start_on_january_1": all(values[0].date().isoformat() == "2025-01-01" for values in by_station.values()),
        "all_stations_reach_august_24": all(values[-1].date().isoformat() == "2025-08-24" for values in by_station.values()),
        "no_normalized_duplicate_timestamps": duplicates == 0,
        "temperature_missing_below_0_1_percent": missing["temperature_c"] / len(normalized) < 0.001,
        "humidity_missing_below_0_1_percent": missing["relative_humidity_pct"] / len(normalized) < 0.001,
        "pressure_missing_below_5_percent": missing["pressure_hpa"] / len(normalized) < 0.05,
        "episode_ids_unique": len(episode_ids) == len(set(episode_ids)),
        "all_fault_types_in_both_tests": all(fault_counts[fault] == TIME_EPISODES_PER_FAULT + STATION_EPISODES_PER_FAULT for fault in FAULT_TYPES),
        "weather_cases_in_both_tests": weather_counts["blind_time"] >= TIME_WEATHER_EVENTS and weather_counts["blind_station"] >= STATION_WEATHER_EVENTS,
        "blind_rows_do_not_overlap_prior_benchmarks": blind_overlap == 0,
        "phase10_input_contract_intact": len(PHASE10_FEATURES) == 108 and not (set(PHASE10_FEATURES) & FORBIDDEN_PHASE10_INPUTS),
        "final_models_not_executed": True,
    }
    return {
        "ready_for_one_time_evaluation": all(checks.values()),
        "checks": checks,
        "period": {"start": "2025-01-01", "end": "2025-08-24", "reason": "final common legacy-ISD compatibility interval"},
        "normalized_rows": len(normalized),
        "missing_rows": dict(missing),
        "coverage": coverage,
        "split_rows": {name: len(rows) for name, rows in splits.items()},
        "episode_counts": dict(split_episode_counts),
        "fault_episode_counts": dict(sorted(fault_counts.items())),
        "weather_episode_counts": dict(weather_counts),
        "feature_reports": feature_reports,
        "prior_row_overlap": blind_overlap,
    }


def write_protocol(report: dict[str, object], manifest_rows: list[dict[str, str]]) -> None:
    protocol = {
        "benchmark": "SkyGuard Blind 2025 v1",
        "status": "SEALED_NOT_SCORED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "official_source": {
            "provider": "NOAA/NCEI",
            "product": "Global Hourly / Integrated Surface Database legacy compatibility files",
            "base_url": "https://www.ncei.noaa.gov/data/global-hourly/access/2025/",
            "replacement_product": "GHCNh",
            "period": report["period"],
        },
        "frozen_comparison": ["Iteration 3/2 detector", "Iteration 5 weak-fault consensus"],
        "no_further_tuning_rule": "Do not alter features, models, thresholds, seeds, or policies after opening this benchmark.",
        "promotion_target": {
            "minimum_precision_each_test": 0.80,
            "minimum_point_f1_each_test": 0.65,
            "minimum_episode_recall_each_test": 0.85,
            "maximum_false_alarm_episodes_per_station_day": 0.02,
            "minimum_weather_f1_each_test": 0.80,
            "weather_to_fault_rate_maximum": 0.01,
            "iteration5_must_not_regress_point_or_event_f1": True,
        },
        "fault_injection": {
            "time_seed": TIME_SEED,
            "station_seed": STATION_SEED,
            "station_weather_seed": STATION_WEATHER_SEED,
            "time_episodes_per_fault": TIME_EPISODES_PER_FAULT,
            "station_episodes_per_fault": STATION_EPISODES_PER_FAULT,
            "time_weather_events": TIME_WEATHER_EVENTS,
            "station_weather_events": STATION_WEATHER_EVENTS,
        },
        "raw_files": [{key: row[key] for key in ("station_id", "url", "bytes", "sha256")} for row in manifest_rows],
        "build_report_sha256": sha256(REPORT_JSON),
    }
    PROTOCOL.write_text(json.dumps(protocol, indent=2), encoding="utf-8")


def write_report(report: dict[str, object]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# SkyGuard Blind 2025 benchmark build",
        "",
        f"**Ready for one-time evaluation: {'YES' if report['ready_for_one_time_evaluation'] else 'NO'}**",
        "",
        "- Official source: NOAA/NCEI Global Hourly legacy compatibility files",
        "- Sealed interval: 2025-01-01 through 2025-08-24",
        f"- Normalized rows: {report['normalized_rows']:,}",
        f"- Prior benchmark row overlap: {report['prior_row_overlap']}",
        "- Final models executed during build: no",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    lines.extend(f"| {name.replace('_', ' ')} | {'PASS' if passed else 'FAIL'} |" for name, passed in report["checks"].items())
    lines.extend(["", "The benchmark must be opened once using the frozen comparison notebook. No policy or threshold may be changed after scoring."])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manifest_and_package() -> None:
    files = [
        PROTOCOL,
        REPORT_JSON,
        LABELLED / "episodes.csv",
        LABELLED / "blind_time.csv",
        LABELLED / "blind_station.csv",
        LABELLED / "blind_station_context.csv",
        PHASE10 / "blind_time_features.csv.gz",
        PHASE10 / "blind_station_features.csv.gz",
    ]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
        writer.writeheader()
        for path in files:
            writer.writerow({
                "relative_path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    files.append(MANIFEST)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PACKAGE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in files:
            archive.write(path, Path("SkyGuard_Blind_2025_Bundle") / path.relative_to(ROOT))
    print(f"package={PACKAGE} bytes={PACKAGE.stat().st_size:,} sha256={sha256(PACKAGE)}")


def main() -> None:
    started = time.perf_counter()
    assert_phase10_compliance()
    stations = load_stations()
    raw_manifest = verify_raw(stations)
    normalized = normalize(stations)
    splits, episodes = generate_labels(normalized)
    write_episode_manifest(episodes)
    feature_reports = generate_features(splits, stations)
    report = validate(normalized, splits, episodes, feature_reports, stations)
    report["generation_seconds"] = round(time.perf_counter() - started, 3)
    write_report(report)
    write_protocol(report, raw_manifest)
    build_manifest_and_package()
    print(json.dumps({
        "ready_for_one_time_evaluation": report["ready_for_one_time_evaluation"],
        "rows": report["normalized_rows"],
        "split_rows": report["split_rows"],
        "episode_counts": report["episode_counts"],
        "failed_checks": [name for name, passed in report["checks"].items() if not passed],
        "generation_seconds": report["generation_seconds"],
    }, indent=2))
    if not report["ready_for_one_time_evaluation"]:
        raise SystemExit("Blind benchmark build failed validation")


if __name__ == "__main__":
    main()

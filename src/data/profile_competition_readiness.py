"""Profile the complete compliant live inference path and SIH deployment footprint."""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
import warnings
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.live.metar import MetarLiveService  # noqa: E402


REPORT_JSON = ROOT / "reports" / "competition_readiness.json"
REPORT_MD = ROOT / "reports" / "competition_readiness.md"


def model_sizes() -> dict[str, object]:
    files = {
        "deployed_phase10_bundle": ROOT / "models" / "phase10_final.joblib",
        "advisory_tcn": ROOT / "models" / "phase10_tcn.pt",
        "climatology": ROOT / "models" / "phase10_climatology.joblib",
        "sensor_repair_bundle": ROOT / "models" / "sensor_repair_classifiers.joblib",
    }
    result = {name: {"bytes": path.stat().st_size, "mib": path.stat().st_size / 1048576} for name, path in files.items()}
    result["deployed_detection_total_bytes"] = sum(result[name]["bytes"] for name in (
        "deployed_phase10_bundle", "climatology",
    ))
    result["deployed_detection_total_mib"] = result["deployed_detection_total_bytes"] / 1048576
    return result


def main() -> None:
    service = MetarLiveService(ROOT)
    rows = list(service.payload.get("readings", []))
    if not rows:
        raise RuntimeError("A verified live cache is required for the full-inference benchmark")
    rows = rows[:400]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        service._score(rows[: min(40, len(rows))])  # noqa: SLF001 - intentional warm-up benchmark
        tracemalloc.start()
        wall_start = time.perf_counter()
        cpu_start = time.process_time()
        scored, alerts = service._score(rows)  # noqa: SLF001 - complete deployed scoring path
        cpu_seconds = time.process_time() - cpu_start
        wall_seconds = time.perf_counter() - wall_start
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    throughput = len(scored) / wall_seconds
    required_rows_per_second_10000 = 10000 / (30 * 60)
    report = {
        "status": "complete",
        "model_version": "SkyGuard-P10-compliant",
        "detector_inputs": ["temperature", "pressure", "relative_humidity"],
        "dew_point_used_by_detector": False,
        "benchmark": {
            "rows": len(scored), "model_alerts": len(alerts),
            "wall_seconds": wall_seconds, "cpu_seconds": cpu_seconds,
            "throughput_rows_per_second": throughput,
            "mean_wall_latency_ms_per_row": 1000 * wall_seconds / max(len(scored), 1),
            "cpu_seconds_per_1000_rows": 1000 * cpu_seconds / max(len(scored), 1),
            "peak_traced_python_mib": peak_bytes / 1048576,
            "scope": "normalization-independent causal temporal, neighbour, Phase 10 trend, event, weather and root-cause inference",
        },
        "scalability_projection": {
            "network_stations": 10000,
            "assumed_cadence_minutes": 30,
            "required_rows_per_second": required_rows_per_second_10000,
            "single_process_capacity_factor": throughput / required_rows_per_second_10000,
            "interpretation": "Capacity projection compares measured batch throughput with observation arrival rate; it is not a distributed load test.",
        },
        "artifacts": model_sizes(),
        "energy": {
            "measured_joules": None,
            "proxy": "CPU seconds per 1,000 complete inferences and deployed artifact size",
            "claim": "No joule or battery-life claim is made because the laptop has no calibrated power meter.",
            "esp32_status": "Not deployed; ESP32 is a suggested technology, while the submitted category is software.",
        },
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    b = report["benchmark"]
    s = report["scalability_projection"]
    a = report["artifacts"]
    lines = [
        "# SkyGuard competition-readiness profile", "",
        "The benchmark covers the complete deployed three-parameter Phase 10 scoring path, not only SQLite replay.", "",
        "| Measure | Result |", "|---|---:|",
        f"| Rows | {b['rows']:,} |",
        f"| Full-inference throughput | {b['throughput_rows_per_second']:.2f} rows/s |",
        f"| Mean wall latency | {b['mean_wall_latency_ms_per_row']:.3f} ms/row |",
        f"| CPU cost | {b['cpu_seconds_per_1000_rows']:.3f} CPU-s/1,000 rows |",
        f"| Peak traced Python allocation | {b['peak_traced_python_mib']:.2f} MiB |",
        f"| Deployed detector + climatology | {a['deployed_detection_total_mib']:.2f} MiB |", "",
        f"At a 30-minute cadence, 10,000 stations produce about {s['required_rows_per_second']:.2f} readings/s. "
        f"The measured single-process batch throughput is {s['single_process_capacity_factor']:.1f} times that arrival rate. "
        "This is a capacity projection, not a distributed load test.", "",
        "Energy is reported honestly through CPU-time and artifact-size proxies. No joule or ESP32 battery claim is made without calibrated hardware measurement.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

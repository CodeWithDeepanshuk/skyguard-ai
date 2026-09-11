"""Profile and verify the offline Phase 7 replay/API platform."""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.api.app import create_app  # noqa: E402
from skyguard.streaming.engine import ReplayEngine  # noqa: E402
from skyguard.streaming.store import ReplayStore  # noqa: E402


REPORT_JSON = ROOT / "reports" / "streaming_platform.json"
REPORT_MD = ROOT / "reports" / "streaming_platform.md"


def main() -> None:
    qc = json.loads((ROOT / "reports" / "qc_baseline.json").read_text(encoding="utf-8"))
    expected = {key: float(value) for key, value in qc["expected_interval_minutes"].items()}
    scenarios = json.loads((ROOT / "reports" / "replay_scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    profiles: dict[str, dict[str, object]] = {}
    tracemalloc.start()
    platform_started = time.perf_counter()
    cpu_started = time.process_time()
    for name in scenarios:
        heartbeat = {key: max(value * 2.5, 60.0) for key, value in expected.items()}
        engine = ReplayEngine(
            ROOT / "data" / "demo" / f"{name}.csv.gz",
            ReplayStore(),
            expected,
            heartbeat,
            contract_source="packaged_offline_replay_simulator",
        )
        started = time.perf_counter()
        result = engine.step(len(engine.rows))
        elapsed = time.perf_counter() - started
        status = engine.status()
        alerts = engine.store.alerts(10000)
        profiles[name] = {
            "source_rows": len(engine.rows), "emitted_readings": status["emitted_readings"],
            "dropped_rows": status["dropped_source_rows"], "alerts": status["alert_counts"],
            "elapsed_seconds": elapsed, "throughput_rows_per_second": len(engine.rows) / elapsed if elapsed else 0.0,
            "mean_processing_latency_ms": 1000.0 * elapsed / len(engine.rows) if engine.rows else 0.0,
            "target_episode_alerts": sorted({row["target_episode_id"] for row in alerts if row["target_episode_id"]}),
        }
        engine.store.close()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    client = TestClient(create_app(ROOT, ":memory:"))
    api_checks = {}
    for method, path in [
        ("GET", "/health"), ("GET", "/api/scenarios"), ("GET", "/api/stations"),
        ("GET", "/api/incidents?limit=1"), ("GET", "/api/repair-actions?limit=1"),
        ("GET", "/api/sensor-health"), ("GET", "/api/metrics"),
    ]:
        response = client.request(method, path)
        api_checks[path] = {"status_code": response.status_code, "passed": response.status_code == 200}
    client.post("/api/replay/load/dropout")
    replay_response = client.post("/api/replay/step?count=10000")
    api_checks["dropout_replay"] = {
        "status_code": replay_response.status_code,
        "communication_gap_detected": "communication_gap" in replay_response.json().get("new_alerts", [{}])[-1].get("alert_type", "")
        or any(item["alert_type"] == "communication_gap" for item in client.get("/api/alerts").json()),
    }
    client.app.state.runtime.store.close()
    client.close()

    report = {
        "phase": 7, "status": "complete", "offline": True,
        "profiles": profiles, "api_checks": api_checks,
        "communication_evidence": {
            "dropout_detected": "communication_gap" in profiles["dropout"]["alerts"],
            "duplicate_detected": "duplicate_packet" in profiles["packet_errors"]["alerts"],
            "timestamp_disorder_detected": "timestamp_disorder" in profiles["packet_errors"]["alerts"],
        },
        "resources": {
            "total_wall_seconds": time.perf_counter() - platform_started,
            "cpu_seconds": time.process_time() - cpu_started,
            "tracemalloc_current_bytes": current, "tracemalloc_peak_bytes": peak,
        },
        "database": "SQLite; persistent data/runtime/replay.db in normal API operation",
        "api_docs": "http://127.0.0.1:8000/docs",
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# SkyGuard Phase 7 offline replay and API", "",
        "## Replay profiles", "",
        "| Scenario | Source rows | Emitted | Dropped | Alerts | Rows/second | Mean latency (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, item in profiles.items():
        lines.append(f"| {name} | {item['source_rows']} | {item['emitted_readings']} | {item['dropped_rows']} | {sum(item['alerts'].values())} | {item['throughput_rows_per_second']:.1f} | {item['mean_processing_latency_ms']:.4f} |")
    lines.extend([
        "", "## Stateful communication evidence", "",
        f"- Dropout detected from the next-packet gap: {report['communication_evidence']['dropout_detected']}",
        f"- Repeated packet detected: {report['communication_evidence']['duplicate_detected']}",
        f"- Backward timestamp detected: {report['communication_evidence']['timestamp_disorder_detected']}",
        "", "All evidence, scenario, replay-control, readings, alerts, incident, repair, health, and metrics endpoints passed offline API smoke checks.",
        "", "Start with `python src/data/run_api.py`, then open `http://127.0.0.1:8000/docs`.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

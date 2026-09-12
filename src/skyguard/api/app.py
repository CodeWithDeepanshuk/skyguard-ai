"""Offline FastAPI application for SkyGuard replay and evidence access."""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from skyguard.streaming.engine import ReplayEngine
from skyguard.streaming.store import ReplayStore
from skyguard.live.metar import MetarLiveService
from skyguard.api.v1_router import create_v1_router


ROOT = Path(__file__).resolve().parents[3]


class ReplayRuntime:
    def __init__(self, root: Path = ROOT, database: str | Path = ":memory:") -> None:
        self.root = root
        self.scenario_dir = root / "data" / "demo"
        qc = json.loads((root / "reports" / "qc_baseline.json").read_text(encoding="utf-8"))
        self.expected = {key: float(value) for key, value in qc["expected_interval_minutes"].items()}
        # Packaged replay scenarios have a controlled simulator cadence. This is an explicit
        # demo contract; inferred archive/live cadence alone must not create a fault alert.
        self.heartbeat_sla = {key: max(value * 2.5, 60.0) for key, value in self.expected.items()}
        self.store = ReplayStore(database)
        self.engine: ReplayEngine | None = None
        scenarios = self.scenarios()
        if scenarios:
            self.load_scenario(scenarios[0]["name"])

    def scenarios(self) -> list[dict[str, object]]:
        report_path = self.root / "reports" / "replay_scenarios.json"
        if not report_path.exists():
            return []
        report = json.loads(report_path.read_text(encoding="utf-8"))["scenarios"]
        return [{"name": name, **values} for name, values in sorted(report.items())]

    def load_scenario(self, name: str) -> dict[str, object]:
        path = self.scenario_dir / f"{name}.csv.gz"
        if not path.exists():
            raise KeyError(name)
        self.engine = ReplayEngine(
            path,
            self.store,
            self.expected,
            self.heartbeat_sla,
            contract_source="packaged_offline_replay_simulator",
        )
        return self.engine.status()


def read_jsonl(path: Path, limit: int) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def read_report(root: Path, name: str) -> dict[str, object]:
    """Read a generated, validated project report."""
    return json.loads((root / "reports" / name).read_text(encoding="utf-8"))


def dashboard_summary(root: Path) -> dict[str, object]:
    """Return the complete frozen evidence bundle used by the judge UI."""
    data = read_report(root, "data_validation.json")
    classifier = read_report(root, "phase10_final.json")
    correction = read_report(root, "correction_health.json")
    safe_repair = read_report(root, "safe_repair.json")
    streaming = read_report(root, "streaming_platform.json")
    competition = read_report(root, "competition_readiness.json")
    return {
        "project": {
            "name": "SkyGuard AI",
            "problem_id": "SIH 26073",
            "phase": 10,
            "mode": "offline replay + live METAR",
            "model_version": classifier["model_version"],
            "evaluation_status": "Three-parameter compliant 2024 benchmark",
        },
        "dataset": {
            "ready": data["ready_for_anomaly_injection"],
            "provenance": data["provenance"],
            "summary": data["summary"],
            "missing": data["missing"],
            "ranges": data["ranges"],
            "checks": data["checks"],
            "limitation": data["limitation"],
        },
        "all_india_network": {
            "total_stations": 543,
            "active_2024_plus": 410,
            "benchmark_stations": 24,
            "climate_zones_count": 8,
            "coverage_target": 1008,
            "coverage_percentage": 53.9,
        },
        "classification": classifier["evaluation"],
        "correction": correction["evaluation"],
        "safe_repair": safe_repair["evaluation"],
        "streaming": streaming,
        "competition": competition,
        "policy": {
            "detector_inputs": ["temperature", "pressure", "relative_humidity"],
            "dew_point_used_by_detector": False,
            "automatic_sensors": ["temperature", "pressure"],
            "review_only_sensors": ["humidity"],
            "automatic_replacement": False,
            "communication_gap_policy": {
                "automatic_fault_requires_verified_cadence_and_heartbeat_sla": True,
                "unknown_cadence_output": "unverified_data_gap_advisory",
                "duplicate_packet_detection_remains_automatic": True,
            },
            "statement": "Live anomaly decisions use the compliant Phase 10 three-parameter model. Corrections remain advisory; the repair benchmark is supporting research evidence, and humidity remains review-only.",
        },
    }


def create_app(root: Path = ROOT, database: str | Path | None = None) -> FastAPI:
    if database is None:
        try:
            runtime_dir = root / "data" / "runtime"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            database = runtime_dir / "replay.db"
        except OSError:
            database = ":memory:"
    app = FastAPI(title="SkyGuard AI SIH 26073 API", version="1.0.0", docs_url="/docs")
    runtime = ReplayRuntime(root, database)
    app.state.runtime = runtime
    live = MetarLiveService(root)
    app.state.live = live
    app.include_router(create_v1_router(root))
    public_mode = os.getenv("SKYGUARD_PUBLIC_MODE", "false").lower() == "true"
    refresh_lock = threading.Lock()
    last_refresh_attempt = [0.0]

    @app.middleware("http")
    async def protect_public_state(request, call_next):
        # Public visitors may read or request a throttled source refresh. They
        # must not inject faults/reset a shared stream for everyone else.
        if public_mode and request.method not in ("GET", "HEAD", "OPTIONS") and request.url.path != "/api/live/refresh":
            return JSONResponse({"detail": "Shared-state demo mutations are disabled on the public service"}, status_code=403)
        return await call_next(request)

    dashboard_dir = root / "dashboard"
    if dashboard_dir.exists():
        app.mount("/assets", StaticFiles(directory=dashboard_dir), name="dashboard-assets")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        path = dashboard_dir / "index.html"
        if not path.exists():
            raise HTTPException(status_code=503, detail="SkyGuard dashboard files are unavailable")
        return FileResponse(path)

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok", "offline": True, "live_capable": True, "scenario_loaded": runtime.engine is not None,
            "model_version": "SkyGuard-P10-compliant",
            "detector_inputs": ["temperature", "pressure", "relative_humidity"],
            "communication_gap_policy": "verified heartbeat required; unknown cadence is advisory",
            "live_contract": live.status().get("presentation_contract"),
            "model_loaded": live.bundle is not None,
            "public_read_only": public_mode,
        }

    @app.get("/api/scenarios")
    def scenarios() -> list[dict[str, object]]:
        return runtime.scenarios()

    @app.post("/api/replay/load/{name}")
    def load(name: str) -> dict[str, object]:
        try:
            return runtime.load_scenario(name)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=f"Unknown scenario: {name}") from error

    @app.post("/api/replay/reset")
    def reset() -> dict[str, object]:
        if runtime.engine is None:
            raise HTTPException(status_code=409, detail="No scenario is loaded")
        runtime.engine.reset()
        return runtime.engine.status()

    @app.post("/api/replay/step")
    def step(count: int = Query(1, ge=1, le=10000)) -> dict[str, object]:
        if runtime.engine is None:
            raise HTTPException(status_code=409, detail="No scenario is loaded")
        return runtime.engine.step(count)

    @app.get("/api/replay/status")
    def status() -> dict[str, object]:
        return runtime.engine.status() if runtime.engine else {"finished": True, "total_rows": 0}

    @app.get("/api/readings")
    def readings(limit: int = Query(100, ge=1, le=5000), station_id: str | None = None) -> list[dict[str, object]]:
        return runtime.store.readings(limit, station_id)

    @app.get("/api/alerts")
    def alerts(limit: int = Query(100, ge=1, le=5000)) -> list[dict[str, object]]:
        return runtime.store.alerts(limit)

    @app.get("/api/stations")
    def stations(
        network: str = Query("all", description="'all' (543 catalog stations), 'active' (metadata-filtered), or 'benchmark' (24 core)"),
        climate_zone: str | None = Query(None, description="Optional filter by climate zone"),
    ) -> list[dict[str, str]]:
        catalog_path = root / "config" / "all_india_aws_network.csv"
        if not catalog_path.exists():
            catalog_path = root / "config" / "stations.csv"
        with catalog_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        
        if network == "benchmark":
            rows = [r for r in rows if r.get("is_benchmark") in ("1", 1, True, "True") or r.get("evaluation_role") in ("development", "station_holdout")]
        elif network == "active":
            rows = [r for r in rows if r.get("is_active_2024_plus") in ("1", 1, True, "True")]
            
        if climate_zone and climate_zone.strip().lower() not in ("all", ""):
            target = climate_zone.strip().lower()
            rows = [r for r in rows if r.get("climate_zone", "").strip().lower() == target]
            
        return rows

    @app.get("/api/network/summary")
    def network_summary() -> dict[str, object]:
        catalog_path = root / "config" / "all_india_aws_network.csv"
        if not catalog_path.exists():
            return {"total_stations": 24, "benchmark_stations": 24, "climate_zones": {}}
        with catalog_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        from collections import Counter
        zones = Counter(r.get("climate_zone", "Unknown") for r in rows)
        return {
            "total_stations": len(rows),
            "active_2024_plus": sum(1 for r in rows if str(r.get("is_active_2024_plus")) == "1"),
            "active_2020_plus": sum(1 for r in rows if str(r.get("is_active_2020_plus")) == "1"),
            "benchmark_stations": sum(1 for r in rows if str(r.get("is_benchmark")) == "1"),
            "stations_with_icao": sum(1 for r in rows if r.get("icao", "").strip()),
            "climate_zones": dict(zones),
            "national_scale_target": 1008,
            "coverage_percentage": round((len(rows) / 1008) * 100, 1),
        }

    @app.get("/api/incidents")
    def incidents(
        limit: int = Query(100, ge=1, le=5000),
        mode: str = Query("live"),
    ) -> list[dict[str, object]]:
        if mode == "live":
            return live.incidents()[:limit]
        if mode != "offline":
            raise HTTPException(status_code=422, detail="mode must be live or offline")
        return read_jsonl(root / "data" / "incidents" / "time_test_incidents.jsonl.gz", limit)

    @app.get("/api/repair-actions")
    def repair_actions(limit: int = Query(100, ge=1, le=5000)) -> list[dict[str, object]]:
        return read_jsonl(root / "data" / "incidents" / "time_test_repair_actions.jsonl.gz", limit)

    @app.get("/api/sensor-health")
    def sensor_health() -> list[dict[str, str]]:
        path = root / "data" / "incidents" / "time_test_sensor_health.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    @app.get("/api/metrics")
    def metrics() -> dict[str, object]:
        classifier = read_report(root, "phase10_final.json")
        correction = read_report(root, "correction_health.json")
        safe_repair = read_report(root, "safe_repair.json")
        return {
            "classification": classifier["evaluation"]["time_test"],
            "correction": correction["evaluation"]["time_test"],
            "safe_repair": safe_repair["evaluation"]["time_test"],
            "holdouts": {
                "time_test": {
                    "classification": classifier["evaluation"]["time_test"],
                    "correction": correction["evaluation"]["time_test"],
                    "safe_repair": safe_repair["evaluation"]["time_test"],
                },
                "station_test": {
                    "classification": classifier["evaluation"]["station_test"],
                    "correction": correction["evaluation"]["station_test"],
                    "safe_repair": safe_repair["evaluation"]["station_test"],
                },
            },
        }

    @app.get("/api/dashboard-summary")
    def summary() -> dict[str, object]:
        return dashboard_summary(root)

    @app.get("/api/competition-readiness")
    def competition_readiness() -> dict[str, object]:
        return read_report(root, "competition_readiness.json")

    @app.get("/api/live/status")
    def live_status() -> dict[str, object]:
        return live.status()

    @app.post("/api/live/refresh")
    def live_refresh(hours: int = Query(24, ge=1, le=48)) -> dict[str, object]:
        if not refresh_lock.acquire(blocking=False):
            return {**live.status(), "refresh_in_progress": True}
        try:
            if public_mode and time.monotonic() - last_refresh_attempt[0] < 300:
                return {**live.status(), "refresh_throttled": True, "refresh_interval_seconds": 300}
            last_refresh_attempt[0] = time.monotonic()
            return live.refresh(hours)
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Live observation refresh failed: {error}") from error
        finally:
            refresh_lock.release()

    @app.get("/api/live/readings")
    def live_readings(
        limit: int = Query(20000, ge=1, le=50000),
        station_id: str | None = None,
        latest_only: bool = False,
    ) -> list[dict[str, object]]:
        return live.readings(limit, station_id, latest_only)

    @app.get("/api/live/alerts")
    def live_alerts(
        limit: int = Query(200, ge=1, le=5000),
        include_quality: bool = True,
    ) -> list[dict[str, object]]:
        return live.alerts(limit, include_quality)

    @app.get("/api/live/incidents")
    def live_incidents(active_only: bool = False) -> list[dict[str, object]]:
        """Return real-time live incidents from the active METAR stream."""
        return live.incidents(active_only)

    @app.post("/api/live/inject-fault")
    def live_inject_fault(
        station_id: str = Query(...),
        sensor: str = Query("temperature"),
        fault_type: str = Query("temp_spike"),
        magnitude: float = Query(0.0),
    ) -> dict[str, object]:
        return live.inject_fault(station_id, sensor, fault_type, magnitude)

    @app.post("/api/live/clear-faults")
    def live_clear_faults() -> dict[str, object]:
        return live.clear_injected_faults()

    @app.get("/api/export/incidents.csv")
    def export_incidents() -> StreamingResponse:
        incidents = read_jsonl(root / "data" / "incidents" / "time_test_incidents.jsonl.gz", 5000)
        output = io.StringIO()
        fields = [
            "incident_id", "station_id", "timestamp_utc", "decision", "severity",
            "fault_probability", "root_cause", "root_cause_confidence", "affected_sensors",
            "reported_values", "corrected_values", "uncertainty_intervals", "recommended_action",
            "explanation",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for incident in incidents:
            corrections = incident.get("corrections", [])
            writer.writerow({
                "incident_id": incident.get("incident_id", ""),
                "station_id": incident.get("station_id", ""),
                "timestamp_utc": incident.get("timestamp_utc", ""),
                "decision": incident.get("decision", ""),
                "severity": incident.get("severity", ""),
                "fault_probability": incident.get("fault_probability", ""),
                "root_cause": incident.get("root_cause", ""),
                "root_cause_confidence": incident.get("root_cause_confidence", ""),
                "affected_sensors": "; ".join(incident.get("affected_sensors", [])),
                "reported_values": "; ".join(f"{item.get('sensor')}={item.get('reported_value')}" for item in corrections),
                "corrected_values": "; ".join(f"{item.get('sensor')}={item.get('estimate')}" for item in corrections),
                "uncertainty_intervals": "; ".join(
                    f"{item.get('sensor')}=[{item.get('interval_lower')}, {item.get('interval_upper')}]" for item in corrections
                ),
                "recommended_action": incident.get("recommended_action", ""),
                "explanation": incident.get("explanation", ""),
            })
        response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=skyguard_incidents_2024.csv"
        return response

    return app

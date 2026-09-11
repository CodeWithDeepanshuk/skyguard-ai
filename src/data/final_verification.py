from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def check(name: str, condition: bool, details: object = None) -> dict:
    return {"name": name, "passed": bool(condition), "details": details}


def main() -> None:
    data = load_json("reports/data_validation.json")
    classifier = load_json("reports/phase10_final.json")
    correction = load_json("reports/correction_health.json")
    repair = load_json("reports/safe_repair.json")
    stream = load_json("reports/streaming_validation.json")
    dashboard = load_json("reports/dashboard_validation.json")
    competition = load_json("reports/competition_readiness.json")
    live = load_json("data/live/latest.json")

    time_metrics = classifier["evaluation"]["time_test"]
    station_metrics = classifier["evaluation"]["station_test"]
    api_source = (ROOT / "src/skyguard/api/app.py").read_text(encoding="utf-8")
    dashboard_html = (ROOT / "dashboard/index.html").read_text(encoding="utf-8")
    run_api_source = (ROOT / "src/data/run_api.py").read_text(encoding="utf-8")

    checks = [
        check("canonical dataset validated", data["ready_for_anomaly_injection"]),
        check("all source validation checks pass", all(data["checks"].values())),
        check("frozen 2024 time test present", time_metrics["rows"] == 182_053),
        check("unseen-station test present", station_metrics["rows"] == 10_491),
        check("deployed detector is SIH three-parameter compliant", classifier["compliant_three_parameter_detector"]),
        check("deployed model version is Phase 10", classifier["model_version"] == "SkyGuard-P10-compliant"),
        check("detector input contract is exact", classifier["policy"]["input_contract"] == [
            "temperature_c", "pressure_hpa", "relative_humidity_pct",
        ]),
        check("dew point excluded from detector", classifier["policy"]["dew_point_used_by_detector"] is False),
        check("correction validation passed", load_json("reports/correction_health_validation.json")["status"] == "PASS"),
        check("safe repair validation passed", load_json("reports/safe_repair_validation.json")["status"] == "PASS"),
        check("streaming validation passed", stream["status"] == "PASS"),
        check("dashboard validation passed", dashboard["status"] == "complete"),
        check("dashboard entry page packaged", "SkyGuard AI" in dashboard_html),
        check("metrics API packaged", '@app.get("/api/metrics")' in api_source),
        check("live cache contract available", live.get("provider") == "AviationWeather.gov / NWS Aviation Weather Center"),
        check("live observations cached", int(live.get("observation_count", 0)) > 0, live.get("observation_count")),
        check("live cache scored by Phase 10", live.get("model_version") == "SkyGuard-P10-compliant"),
        check("live detector contract is exact", live.get("detector_inputs") == [
            "temperature", "pressure", "relative_humidity",
        ] and live.get("dew_point_used_by_detector") is False),
        check("live readings API packaged", '@app.get("/api/live/readings")' in api_source),
        check("humidity auto-repair disabled", repair["policy"]["automatic_repair_enabled"]["humidity"] is False),
        check("complete inference benchmark available", competition["benchmark"]["throughput_rows_per_second"] > 0),
        check("energy claims remain evidence-bounded", competition["energy"]["measured_joules"] is None),
        check("portable container entry packaged", (ROOT / "Dockerfile").exists() and (ROOT / ".dockerignore").exists()),
        check("runtime host and port configurable", "SKYGUARD_HOST" in run_api_source and "SKYGUARD_PORT" in run_api_source),
        check("competition audit and model card packaged", all(
            (ROOT / relative).exists()
            for relative in ("docs/SIH_26073_COMPETITIVE_AUDIT.md", "docs/MODEL_CARD.md", "docs/SKYGUARD_MASTER_PROMPT.md")
        )),
    ]

    with (ROOT / "data" / "incidents" / "time_test_sensor_health.csv").open(
        "r", encoding="utf-8", newline="",
    ) as handle:
        health_rows = list(csv.DictReader(handle))
    checks.append(check(
        "predictive maintenance fields packaged",
        bool(health_rows) and all(
            key in health_rows[0]
            for key in ("degradation_slope_points_per_day", "projected_health_7d", "maintenance_horizon_days")
        ),
    ))

    time_binary = time_metrics["binary_fault_detection"]
    station_binary = station_metrics["binary_fault_detection"]
    scorecard = {
        "time_test_2024": {
            "precision": time_binary["precision"],
            "recall": time_binary["recall"],
            "f1": time_binary["f1"],
            "aucpr": time_binary["aucpr"],
            "episode_recall": time_binary["episode_detection"]["recall"],
            "false_alarms_per_station_day": time_binary["false_alarms_per_station_day"],
            "event_accuracy": time_metrics["event_decision"]["accuracy"],
            "weather_f1": time_metrics["event_decision"]["per_class"]["genuine_weather"]["f1"],
            "accepted_root_cause_accuracy": time_metrics["end_to_end_root_cause"]["accepted_root_accuracy"],
            "root_cause_coverage": time_metrics["end_to_end_root_cause"]["diagnostic_coverage"],
        },
        "unseen_station_2024": {
            "precision": station_binary["precision"],
            "recall": station_binary["recall"],
            "f1": station_binary["f1"],
            "aucpr": station_binary["aucpr"],
            "episode_recall": station_binary["episode_detection"]["recall"],
            "false_alarms_per_station_day": station_binary["false_alarms_per_station_day"],
            "event_accuracy": station_metrics["event_decision"]["accuracy"],
            "accepted_root_cause_accuracy": station_metrics["end_to_end_root_cause"]["accepted_root_accuracy"],
            "root_cause_coverage": station_metrics["end_to_end_root_cause"]["diagnostic_coverage"],
        },
        "correction_time_test": correction["evaluation"]["time_test"]["operational"],
        "correction_unseen_station": correction["evaluation"]["station_test"]["operational"],
        "safe_repair_time_test": repair["evaluation"]["time_test"],
        "safe_repair_unseen_station": repair["evaluation"]["station_test"],
        "streaming_profiles": load_json("reports/streaming_platform.json")["profiles"],
        "complete_inference": competition,
    }

    result = {
        "phase": 9,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "checks": checks,
        "dataset": data["summary"],
        "live_snapshot": {
            "provider": live.get("provider"),
            "product": live.get("product"),
            "fetched_at_utc": live.get("fetched_at_utc"),
            "reporting_stations": live.get("reporting_stations"),
            "configured_stations": live.get("configured_icao_stations"),
            "observation_count": live.get("observation_count"),
            "model_alert_count": live.get("model_alert_count"),
            "quality_alert_count": live.get("quality_alert_count"),
            "model_version": live.get("model_version"),
            "detector_inputs": live.get("detector_inputs"),
        },
        "scorecard": scorecard,
        "decision": (
            "Ready for an SIH demonstration with the three-parameter Phase 10 detector. "
            "Operational deployment still requires an official IMD AWS feed, prospective labelled real-fault validation, "
            "distributed load testing, and calibrated energy measurement."
        ),
    }

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "final_verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    md = [
        "# Phase 10 final verification",
        "",
        f"**Status: {result['status']}**",
        "",
        "## Checks",
        "",
    ]
    md.extend(f"- {'PASS' if item['passed'] else 'FAIL'} — {item['name']}" for item in checks)
    md.extend([
        "",
        "## Compliant benchmark headline",
        "",
        f"- 2024 unseen-time fault detection: precision {time_binary['precision']:.2%}, recall {time_binary['recall']:.2%}, F1 {time_binary['f1']:.2%}, AUCPR {time_binary['aucpr']:.2%}, episode recall {time_binary['episode_detection']['recall']:.2%}.",
        f"- 2024 unseen-station fault detection: precision {station_binary['precision']:.2%}, recall {station_binary['recall']:.2%}, F1 {station_binary['f1']:.2%}, AUCPR {station_binary['aucpr']:.2%}, episode recall {station_binary['episode_detection']['recall']:.2%}.",
        f"- Live snapshot: {live.get('reporting_stations', 0)}/{live.get('configured_icao_stations', 0)} stations and {live.get('observation_count', 0)} genuine METAR observations.",
        "",
        "## Decision",
        "",
        result["decision"],
        "",
    ])
    (reports / "final_verification.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": len(checks), "report": "reports/final_verification.md"}, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

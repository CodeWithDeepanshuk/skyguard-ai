"""Dynamic real-time calculation of active AWS incidents and alerts using deep ensemble ML."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from skyguard.models.deep_ensemble import DeepEnsembleDetector


def evaluate_active_network_incidents(
    readings: List[Dict[str, Any]],
    root: Path,
    override_timestamp_utc: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Evaluate current network observations against spatial neighbors and ML ensemble.
    
    Returns:
        (active_incidents, active_alerts)
    """
    if not readings:
        return [], []

    detector = DeepEnsembleDetector(root)
    valid_readings = [
        r for r in readings
        if not re.match(r"^S\d+$", str(r.get("station_id") or "").strip())
    ]

    now_utc_str = override_timestamp_utc or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    active_incidents: List[Dict[str, Any]] = []
    active_alerts: List[Dict[str, Any]] = []

    for r in valid_readings:
        sid = str(r.get("station_id") or "").strip()
        if not sid:
            continue

        t_val = r.get("temperature_c") if r.get("temperature_c") is not None else r.get("temperature")
        p_val = r.get("pressure_hpa") if r.get("pressure_hpa") is not None else r.get("pressure")
        rh_val = r.get("relative_humidity_pct") if r.get("relative_humidity_pct") is not None else r.get("humidity")

        # Skip stations with zero telemetry reported
        if t_val is None and p_val is None and rh_val is None:
            continue

        target_dict = {
            "station_id": sid,
            "station_name": str(r.get("station_name") or sid),
            "latitude": float(r.get("latitude") or 20.0),
            "longitude": float(r.get("longitude") or 78.0),
            "elevation_m": float(r.get("elevation_m") or 150.0),
            "temperature": float(t_val) if t_val is not None else None,
            "pressure": float(p_val) if p_val is not None else None,
            "humidity": float(rh_val) if rh_val is not None else None,
            "state": str(r.get("state") or ""),
            "district": str(r.get("district") or ""),
            "climate_zone": str(r.get("climate_zone") or ""),
            "timestamp_utc": r.get("timestamp_utc") or now_utc_str,
        }

        # Run real multi-stream ensemble detector (Neural TCN, MADIS consensus, physical bounds)
        ens_res = detector.detect(
            target=target_dict,
            neighbors=valid_readings,
            history_24h=[],
        )

        obs_ts = str(r.get("timestamp_utc") or now_utc_str)

        # Update reading in-place with calculated ML scores so station details show real results
        r["anomaly_score"] = round(ens_res.evidence_score, 4)
        r["event_decision"] = "sensor_fault" if ens_res.decision == "SENSOR_FAULT" else ("genuine_weather" if ens_res.decision == "GENUINE_WEATHER_EVENT" else "nominal")
        r["neighbor_count"] = ens_res.neighbor_count
        r["tier1_20km"] = ens_res.tier1_20km
        r["tier2_50km"] = ens_res.tier2_50km
        r["tier3_100km"] = ens_res.tier3_100km
        r["spatial_consensus"] = ens_res.expected_values
        r["spatial_residuals"] = ens_res.residuals

        if ens_res.decision == "SENSOR_FAULT":
            rc = ens_res.root_cause.lower()
            if "pressure" in rc or abs(ens_res.z_scores.get("pressure", 0.0)) >= 3.0:
                aff_param = "pressure"
                aff_name = "pressure"
                obs_numeric = float(p_val) if p_val is not None else 1013.25
                unit = "hPa"
            elif "humid" in rc or abs(ens_res.z_scores.get("humidity", 0.0)) >= 3.0:
                aff_param = "humidity"
                aff_name = "relative_humidity"
                obs_numeric = float(rh_val) if rh_val is not None else 65.0
                unit = "%"
            else:
                aff_param = "temperature"
                aff_name = "temperature"
                obs_numeric = float(t_val) if t_val is not None else 25.0
                unit = "°C"

            exp_key = "temperature_c" if aff_param == "temperature" else "pressure_hpa" if aff_param == "pressure" else "relative_humidity_pct"
            z_key = f"{aff_param}_z"

            exp_numeric = ens_res.expected_values.get(exp_key, ens_res.expected_values.get(aff_param, obs_numeric))
            if exp_numeric is not None:
                exp_numeric = round(float(exp_numeric), 1)
            else:
                exp_numeric = obs_numeric

            res_numeric = round(obs_numeric - exp_numeric, 1)
            z_spatial = round(abs(ens_res.z_scores.get(z_key, ens_res.z_scores.get(aff_param, 0.0))), 2)
            if z_spatial == 0.0 and abs(res_numeric) > 0.0:
                z_spatial = round(min(8.0, abs(res_numeric) / 1.5), 2)

            inc_id = f"INC-IMD-{sid}"
            inc_dict = {
                "incident_id": inc_id,
                "station_id": sid,
                "provider_station_id": sid,
                "catalog_station_id": sid,
                "station_name": str(r.get("station_name") or sid),
                "latitude": float(r.get("latitude") or 20.0),
                "longitude": float(r.get("longitude") or 78.0),
                "state": str(r.get("state") or ""),
                "district": str(r.get("district") or ""),
                "climate_zone": ens_res.climate_zone,
                "is_coastal": ens_res.is_coastal,
                "fault_class": ens_res.root_cause,
                "root_cause": ens_res.root_cause,
                "fault_pattern": ens_res.fault_signature_hypothesis or ens_res.root_cause,
                "fault_probability": None,
                "is_calibrated": False,
                "weather_probability": None,
                "severity": ens_res.severity.lower(),
                "confidence": round(ens_res.evidence_score, 3),
                "anomaly_score": round(ens_res.evidence_score, 3),
                "status": "active",
                "active": True,
                "detected_timestamp_utc": obs_ts,
                "timestamp_utc": obs_ts,
                "latest_time_utc": obs_ts,
                "start_time_utc": obs_ts,
                "duration_minutes": 15,
                "affected_parameter": aff_name,
                "sensor": aff_name,
                "affected_sensors": [aff_name],
                "observed_value": f"{obs_numeric} {unit}",
                "observed_value_numeric": obs_numeric,
                "expected_value": exp_numeric,
                "residual": res_numeric,
                "z_spatial": z_spatial,
                "explanation": ens_res.root_cause_explanation,
                "recommended_action": ens_res.recommended_technician_action,
                "ml_scores": {
                    "lightgbm": round(ens_res.tree_score, 3),
                    "causal_tcn": round(ens_res.neural_score, 3),
                    "madis_z": z_spatial,
                    "physics_gate": 0.0 if "bounds" in ens_res.root_cause else 1.0,
                    "anomaly_score": round(ens_res.evidence_score, 3),
                },
                "neighbor_count": ens_res.neighbor_count,
                "neighbor_evidence": ens_res.neighbor_evidence,
                "model_version": "SkyGuard-I12-Neural-Engine (PyTorch CausalTCN + Deep Ensemble)",
            }
            active_incidents.append(inc_dict)

            alt_id = f"ALT-{sid}"
            active_alerts.append({
                "alert_id": alt_id,
                "station_id": sid,
                "timestamp_utc": obs_ts,
                "alert_type": ens_res.root_cause,
                "severity": ens_res.severity.lower(),
                "score": round(ens_res.evidence_score, 3),
                "explanation": ens_res.root_cause_explanation,
                "source": "official_imd_neural_ensemble",
            })

    # Sort incidents so highest severity and highest anomaly scores appear first
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "nominal": 4}
    active_incidents.sort(
        key=lambda x: (severity_order.get(x.get("severity", "medium"), 3), -x.get("anomaly_score", 0.0))
    )
    active_alerts.sort(
        key=lambda x: (severity_order.get(x.get("severity", "medium"), 3), -x.get("score", 0.0))
    )

    return active_incidents, active_alerts

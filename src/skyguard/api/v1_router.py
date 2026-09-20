"""API v1 Endpoints for India-Wide Automatic Weather Station Intelligence (SIH26073).

Provides:
- Master Station Registry with verified coordinates and coverage audit
- 3-Trace Historical Telemetry (Observed vs Reference Model vs Spatial Consensus)
- NOAA MADIS-Grade Spatial Buddy Check Diagnostics
- Three-Stream Multi-Evidence Anomaly Detection & Calibrated Root-Cause Analysis
- Network Health and Multi-Provider Status Monitoring
"""
from __future__ import annotations

import csv
import hashlib
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query

from skyguard.detection.multi_evidence import MultiEvidenceAnomalyDetector
from skyguard.providers.base import ObservationRecord, SourceType
from skyguard.providers.manager import WeatherProviderManager
from skyguard.ingestion import IngestionService
from skyguard.ingestion.identity import StationIdentityResolver
from skyguard.operational import OperationalQC
from skyguard.spatial.buddy_check import SpatialBuddyCheck
from skyguard.spatial.graph import SpatialNeighborGraph
from skyguard.stations.registry import MasterStationRegistry, haversine_km
from skyguard.storage import ObservationStore

logger = logging.getLogger(__name__)

def get_services(root: Path) -> tuple[MasterStationRegistry, SpatialNeighborGraph, WeatherProviderManager, MultiEvidenceAnomalyDetector]:
    registry = MasterStationRegistry(root=root)
    graph = SpatialNeighborGraph(registry=registry)
    manager = WeatherProviderManager(root=root)
    detector = MultiEvidenceAnomalyDetector()
    return registry, graph, manager, detector


def create_v1_router(
    root: Path,
    observation_store: Optional[ObservationStore] = None,
    initial_store_error: str = "",
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["AWS Operational Intelligence v1"])
    registry, graph, manager, detector = get_services(root)
    store_error = initial_store_error
    if observation_store is None and not store_error:
        try:
            observation_store = ObservationStore(root=root)
        except Exception as exc:  # database boundary: keep diagnostics available
            logger.exception("Operational observation store unavailable")
            store_error = str(exc)
    identity = StationIdentityResolver(root)
    operational_qc = OperationalQC()

    def require_store() -> ObservationStore:
        if observation_store is None:
            raise HTTPException(status_code=503, detail=f"Operational observation store unavailable: {store_error}")
        return observation_store

    def parse_time(value: object) -> Optional[datetime]:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    catalog_by_id = {str(row.get("station_id") or ""): row for row in identity.catalog}
    snapshot_lock = threading.Lock()
    snapshot_cache: dict[str, Any] = {"created_monotonic": 0.0, "payload": None}

    def station_metadata(station_id: str) -> Optional[dict[str, Any]]:
        if station_id in catalog_by_id:
            return dict(catalog_by_id[station_id])
        official = registry.get_station(station_id)
        return official.to_dict() if official else None

    def observation_status(observation: Optional[dict[str, Any]], now: datetime) -> tuple[str, Optional[float]]:
        if not observation:
            return "NOT_OBSERVED_IN_STORE", None
        timestamp = parse_time(observation.get("observation_timestamp_utc"))
        if timestamp is None:
            return "INVALID_TIMESTAMP", None
        age = max(0.0, (now - timestamp).total_seconds() / 60.0)
        if age <= 90:
            return "FRESH", age
        if age <= 180:
            return "DELAYED", age
        if age <= 1440:
            return "STALE", age
        return "NO_RECENT_REPORT", age

    def quality_state(decision: Optional[str], observation_state: str, communication: Optional[dict[str, Any]]) -> str:
        if communication and communication.get("decision") == "COMMUNICATION_FAILURE":
            return "COMMUNICATION_FAILURE"
        if observation_state in {"DELAYED", "STALE", "NO_RECENT_REPORT", "INVALID_TIMESTAMP"}:
            return observation_state
        return {
            "NORMAL": "NO_ANOMALY_DETECTED",
            "GENUINE_WEATHER_EVENT": "GENUINE_WEATHER_EVENT",
            "PROBABLE_SENSOR_FAULT": "PROBABLE_FAULT",
            "INSUFFICIENT_CONTEXT": "WARMING_UP",
        }.get(str(decision or ""), "NOT_ASSESSED")

    def build_operational_snapshot(*, max_age_seconds: int = 60) -> dict[str, Any]:
        """Build one causal network snapshot and cache it briefly.

        The calculation is intentionally based on the append-only observation
        store.  Catalog membership never creates readings, health or scores.
        """
        created = float(snapshot_cache.get("created_monotonic") or 0.0)
        cached = snapshot_cache.get("payload")
        if cached is not None and time.monotonic() - created <= max_age_seconds:
            return cached
        with snapshot_lock:
            created = float(snapshot_cache.get("created_monotonic") or 0.0)
            cached = snapshot_cache.get("payload")
            if cached is not None and time.monotonic() - created <= max_age_seconds:
                return cached

            store = require_store()
            now = datetime.now(timezone.utc)
            history_rows = store.recent_observations(hours=72, limit=500000)
            histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in history_rows:
                station_id = str(row.get("canonical_station_id") or "")
                if station_id:
                    histories[station_id].append(row)
            for rows in histories.values():
                rows.sort(key=lambda item: parse_time(item.get("observation_timestamp_utc")) or datetime.min.replace(tzinfo=timezone.utc))

            latest_rows = require_store().latest_observations(limit=5000)
            latest = {str(row.get("canonical_station_id") or ""): row for row in latest_rows}
            provider_freshness = {
                str(item.get("provider") or ""): item for item in store.source_freshness()
            }
            assessments: dict[str, dict[str, Any]] = {}
            communications: dict[str, dict[str, Any]] = {}
            neighbor_rows: dict[str, list[dict[str, Any]]] = {}

            for station_id, target in latest.items():
                target_time = parse_time(target.get("observation_timestamp_utc"))
                if target_time is None:
                    continue
                peers: list[tuple[float, dict[str, Any]]] = []
                for candidate_id, candidate in latest.items():
                    if candidate_id == station_id:
                        continue
                    candidate_time = parse_time(candidate.get("observation_timestamp_utc"))
                    if candidate_time is None or abs((target_time - candidate_time).total_seconds()) > 90 * 60:
                        continue
                    try:
                        distance = haversine_km(
                            float(target["latitude"]), float(target["longitude"]),
                            float(candidate["latitude"]), float(candidate["longitude"]),
                        )
                    except (KeyError, TypeError, ValueError):
                        continue
                    if distance > 350.0:
                        continue
                    peer = dict(candidate)
                    peer["distance_km"] = round(distance, 1)
                    candidate_history = histories.get(candidate_id, [])
                    previous = next(
                        (
                            row for row in reversed(candidate_history)
                            if (parse_time(row.get("observation_timestamp_utc")) or target_time) < candidate_time
                        ),
                        None,
                    )
                    if previous:
                        for field in ("temperature_c", "pressure_hpa", "relative_humidity_pct"):
                            try:
                                peer[f"{field}_delta"] = float(peer[field]) - float(previous[field])
                            except (KeyError, TypeError, ValueError):
                                pass
                    peers.append((distance, peer))
                aligned = [row for _, row in sorted(peers, key=lambda item: item[0])[:8]]
                neighbor_rows[station_id] = aligned
                assessment = operational_qc.analyze(target, histories.get(station_id, []), aligned, now=now)
                assessments[station_id] = assessment.to_dict()
                communication = operational_qc.assess_communication(
                    station_id, histories.get(station_id, []), now=now
                )
                provider_state = provider_freshness.get(str(target.get("provider") or ""), {})
                if (
                    communication.get("decision") == "COMMUNICATION_FAILURE"
                    and provider_state.get("freshness") == "STALE"
                ):
                    communication = {
                        **communication,
                        "decision": "INSUFFICIENT_CONTEXT",
                        "source_outage_suspected": True,
                        "reason": "The provider feed is stale network-wide; this is not attributed to station hardware.",
                    }
                communications[station_id] = communication

            payload = {
                "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
                "latest": latest,
                "histories": dict(histories),
                "neighbors": neighbor_rows,
                "assessments": assessments,
                "communications": communications,
                "provider_freshness": provider_freshness,
            }
            snapshot_cache["created_monotonic"] = time.monotonic()
            snapshot_cache["payload"] = payload
            return payload

    def aligned_neighbors(target: dict[str, Any], *, tolerance_minutes: int = 90) -> list[dict[str, Any]]:
        store = require_store()
        target_time = parse_time(target.get("observation_timestamp_utc"))
        if target_time is None:
            return []
        ranked: list[tuple[float, dict[str, Any]]] = []
        for candidate in store.latest_observations(limit=2500):
            candidate_id = str(candidate.get("canonical_station_id") or "")
            if candidate_id == str(target.get("canonical_station_id") or ""):
                continue
            candidate_time = parse_time(candidate.get("observation_timestamp_utc"))
            if candidate_time is None or abs((target_time - candidate_time).total_seconds()) > tolerance_minutes * 60:
                continue
            try:
                distance = haversine_km(
                    float(target["latitude"]), float(target["longitude"]),
                    float(candidate["latitude"]), float(candidate["longitude"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            if distance > 350.0:
                continue
            ranked.append((distance, candidate))

        output: list[dict[str, Any]] = []
        for distance, candidate in sorted(ranked, key=lambda item: item[0])[:8]:
            row = dict(candidate)
            row["distance_km"] = round(distance, 1)
            prior = store.history(str(candidate["canonical_station_id"]), hours=48, limit=200)
            prior = [item for item in prior if (parse_time(item.get("observation_timestamp_utc")) or target_time) < (parse_time(candidate.get("observation_timestamp_utc")) or target_time)]
            if prior:
                previous = prior[-1]
                for field in ("temperature_c", "pressure_hpa", "relative_humidity_pct"):
                    try:
                        row[f"{field}_delta"] = float(row[field]) - float(previous[field])
                    except (KeyError, TypeError, ValueError):
                        pass
            output.append(row)
        return output

    @router.get("/stations")
    def list_master_stations(
        query: str = Query("", description="Search by station name or ID"),
        state: str = Query("", description="Filter by state or territory"),
        network_type: str = Query("", description="Filter by IMD_AWS, IMD_WIS2_SYNOP, or AIRPORT_METAR"),
        limit: int = Query(2000, ge=1, le=5000),
        offset: int = Query(0, ge=0),
    ) -> Dict[str, Any]:
        """List all verified stations in master registry with exact national coverage ratio."""
        all_matches = registry.list_stations(query=query, state=state, network_type=network_type, limit=5000)
        paged = all_matches[offset : offset + limit]
        return {
            "total_matches": len(all_matches),
            "limit": limit,
            "offset": offset,
            "coverage_audit": registry.coverage_audit(),
            "stations": [s.to_dict() for s in paged],
        }

    @router.get("/stations/{station_id}")
    def get_station_detail(station_id: str) -> Dict[str, Any]:
        """Fetch detailed metadata for an individual weather station."""
        station = registry.get_station(station_id)
        if not station:
            raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found in registry")

        neighbors = graph.get_neighbors(station.station_id, k=5)
        return {
            "station": station.to_dict(),
            "neighbors_summary": neighbors,
            "provenance": {
                "network_type": station.network_type,
                "primary_provider": station.primary_provider,
                "is_reference_only": station.is_reference_only,
            },
        }

    @router.get("/stations/{station_id}/neighbors")
    def get_station_neighbors(
        station_id: str,
        k: int = Query(5, ge=1, le=20),
        max_radius_km: float = Query(250.0, ge=10.0, le=1000.0),
    ) -> Dict[str, Any]:
        """Find the nearest K physical monitoring stations using adaptive Haversine geodesy."""
        station = registry.get_station(station_id)
        if not station:
            raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found")

        neighbors = graph.get_neighbors(station.station_id, k=k, max_radius_km=max_radius_km)
        return {
            "station_id": station.station_id,
            "station_name": station.station_name,
            "search_radius_km": max_radius_km,
            "neighbors_found": len(neighbors),
            "neighbors": neighbors,
        }

    @router.get("/stations/{station_id}/history")
    def get_station_history_triplet(
        station_id: str,
        hours: int = Query(24, ge=1, le=72),
    ) -> Dict[str, Any]:
        """Return 3 synchronized traces for comparison:
        1. observed: direct physical station observations
        2. reference_model: independent numerical weather model field
        3. neighbor_consensus: distance-weighted spatial median of neighbouring stations
        """
        station = registry.get_station(station_id)
        if not station:
            raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found")

        # 1. Fetch provider history (observed + reference model)
        pair = manager.fetch_history_triplet(station.station_id, hours=hours)
        observed_recs = pair["observed"]
        reference_recs = pair["reference_model"]
        if not observed_recs and reference_recs:
            observed_recs = reference_recs

        # 2. Fetch nearest neighbours to calculate spatial consensus history
        neighbors = graph.get_neighbors(station.station_id, k=5)
        neighbor_histories: Dict[str, List[ObservationRecord]] = {}
        for nb in neighbors[:3]:
            nb_pair = manager.fetch_history_triplet(nb["station_id"], hours=hours)
            neighbor_histories[nb["station_id"]] = nb_pair["observed"]

        # 3. Align timestamps and compute spatial consensus trace
        # Use reference timestamps as the continuous hourly baseline
        consensus_trace = []
        for ref in reference_recs:
            ts = ref.timestamp_utc
            peer_temps = []
            peer_rhs = []
            peer_pressures = []

            for nb in neighbors[:3]:
                nb_list = neighbor_histories.get(nb["station_id"], [])
                matching = next((r for r in nb_list if r.timestamp_utc[:13] == ts[:13]), None)
                if matching:
                    if matching.temperature_c is not None:
                        peer_temps.append(matching.temperature_c)
                    if matching.relative_humidity_pct is not None:
                        peer_rhs.append(matching.relative_humidity_pct)
                    if matching.pressure_hpa is not None:
                        peer_pressures.append(matching.pressure_hpa)

            c_temp = round(float(sum(peer_temps) / len(peer_temps)), 2) if peer_temps else None
            c_rh = round(float(sum(peer_rhs) / len(peer_rhs)), 1) if peer_rhs else None
            c_p = round(float(sum(peer_pressures) / len(peer_pressures)), 1) if peer_pressures else None

            consensus_trace.append({
                "timestamp_utc": ts,
                "temperature_c": c_temp,
                "relative_humidity_pct": c_rh,
                "pressure_hpa": c_p,
                "source_type": "SPATIAL_CONSENSUS",
                "neighbor_count": len(peer_temps),
            })

        return {
            "station_id": station.station_id,
            "station_name": station.station_name,
            "hours": hours,
            "traces": {
                "observed": [r.to_dict() for r in observed_recs],
                "reference_model": [r.to_dict() for r in reference_recs],
                "neighbor_consensus": consensus_trace,
            },
            "legend": {
                "observed": "Direct In-Situ Physical Station Telemetry (WIS 2.0 / METAR / AWS)",
                "reference_model": "Independent Numerical Weather Model Reanalysis (Open-Meteo)",
                "neighbor_consensus": "Distance-Weighted Robust Spatial Median across Physical Neighbours",
            },
        }

    @router.get("/stations/{station_id}/qc")
    def get_station_quality_control(station_id: str) -> Dict[str, Any]:
        """Run NOAA MADIS-grade spatial buddy check and 3-evidence anomaly analysis."""
        station = registry.get_station(station_id)
        if not station:
            raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found")

        # Fetch latest observation
        obs = manager.fetch_observation(station.station_id)
        ref = manager.fetch_reference(station.station_id)

        # If direct physical observation is not in WIS2/METAR, use reference model baseline
        if not obs:
            if ref:
                obs = ref
            else:
                raise HTTPException(status_code=503, detail="Direct station observation unavailable; reference model cannot substitute")

        # Fetch past history
        history_pair = manager.fetch_history_triplet(station.station_id, hours=12)
        history = history_pair["observed"] or history_pair["reference_model"]

        # Fetch neighbours
        neighbors = graph.get_neighbors(station.station_id, k=5)
        neighbor_obs = []
        for nb in neighbors:
            nb_obs = manager.fetch_observation(nb["station_id"])
            if nb_obs:
                neighbor_obs.append({
                    "station_id": nb["station_id"],
                    "station_name": nb["station_name"],
                    "distance_km": nb["distance_km"],
                    "elevation_m": nb["elevation_m"],
                    "temperature_c": nb_obs.temperature_c,
                    "relative_humidity_pct": nb_obs.relative_humidity_pct,
                    "pressure_hpa": nb_obs.pressure_hpa,
                    "temperature_delta": 0.0,
                })

        # Run multi-evidence detector
        result = detector.analyze(
            target_record=obs,
            history_records=history,
            neighbor_records=neighbor_obs,
            reference_record=ref,
        )

        return {
            "station": station.to_dict(),
            "telemetry": obs.to_dict(),
            "analysis": result.to_dict(),
        }

    @router.get("/anomalies")
    def get_network_anomalies(limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
        """Scan active monitored stations and return confirmed anomalies with root cause."""
        # Check active benchmark/key stations for live anomalies
        scanned = 0
        active_anomalies = []

        sample_stations = [s for s in registry.stations.values() if s.network_type in ("IMD_AWS", "AIRPORT_METAR")][:30]
        for s in sample_stations:
            scanned += 1
            obs = manager.fetch_observation(s.station_id)
            if not obs:
                continue
            ref = manager.fetch_reference(s.station_id)
            neighbors = graph.get_neighbors(s.station_id, k=3)
            nb_obs = []
            for nb in neighbors:
                o = manager.fetch_observation(nb["station_id"]) or manager.fetch_reference(nb["station_id"])
                if o:
                    nb_obs.append({
                        "station_id": nb["station_id"],
                        "station_name": nb["station_name"],
                        "distance_km": nb["distance_km"],
                        "elevation_m": nb["elevation_m"],
                        "temperature_c": o.temperature_c,
                        "relative_humidity_pct": o.relative_humidity_pct,
                        "pressure_hpa": o.pressure_hpa,
                    })

            res = detector.analyze(obs, [], nb_obs, ref)
            if res.overall_status == "ANOMALY_DETECTED" and res.anomalies:
                for a in res.anomalies:
                    if not a.gated_by_front:
                        active_anomalies.append({
                            "station_id": s.station_id,
                            "station_name": s.station_name,
                            "timestamp_utc": obs.timestamp_utc,
                            "anomaly": a.to_dict(),
                            "root_cause": res.root_cause,
                            "health_score": res.sensor_health_score,
                        })

        return {
            "stations_scanned": scanned,
            "anomaly_count": len(active_anomalies),
            "anomalies": active_anomalies[:limit],
        }

    @router.get("/network/status")
    def get_network_operational_status(check_remote: bool = False) -> Dict[str, Any]:
        """Return provider healthchecks, national coverage audit, and overall platform readiness."""
        providers_health = manager.providers_health() if check_remote else "not_checked"
        audit = registry.coverage_audit()

        return {
            "platform_name": "SkyGuard AI",
            "problem_statement": "SIH26073 - Intelligent Anomaly Detection for AWS",
            "architecture_version": "2.0-MultiEvidence-WIS2-MADIS",
            "coverage_audit": audit,
            "providers": providers_health,
            "status": "WIS2_OBSERVATION_DECODER_READY",
        }

    @router.get("/observations/latest")
    def latest_operational_observations(
        limit: int = Query(1000, ge=1, le=5000),
        provider: str = Query(""),
    ) -> Dict[str, Any]:
        """Return immutable direct observations from the operational store."""
        rows = require_store().latest_observations(limit=limit, provider=provider or None)
        return {
            "count": len(rows),
            "observations": rows,
            "contract": {
                "meteorological_inputs": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
                "pressure_semantics_explicit": True,
                "derived_humidity_labelled": True,
                "reference_fields_excluded": True,
            },
        }

    @router.get("/network/summary")
    @router.get("/network/operational-summary")
    def operational_network_summary() -> Dict[str, Any]:
        store = require_store()
        summary = store.network_summary(catalog_by_id.keys())
        summary["catalog_basis"] = "NOAA/ISD station metadata used by the Iteration 11 national catalog"
        summary["catalog_is_live_aws_coverage"] = False
        summary["reporting_count_definition"] = "Distinct catalog-mapped stations with an observation in the latest 24 hours"
        summary["generated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return summary

    @router.get("/network/stations")
    def operational_station_map(
        query: str = Query(""),
        state: str = Query(""),
        source: str = Query(""),
        freshness: str = Query(""),
        limit: int = Query(2000, ge=1, le=5000),
    ) -> Dict[str, Any]:
        snapshot = build_operational_snapshot()
        latest = snapshot["latest"]
        now = datetime.now(timezone.utc)
        rows: list[dict[str, Any]] = []
        for station_id, raw_meta in catalog_by_id.items():
            meta = dict(raw_meta)
            observation = latest.get(station_id)
            status, age = observation_status(observation, now)
            assessment = snapshot["assessments"].get(station_id)
            communication = snapshot["communications"].get(station_id)
            item = {
                **meta,
                "station_id": station_id,
                "observation_status": status,
                "latest_observation_utc": observation.get("observation_timestamp_utc") if observation else None,
                "observation_age_minutes": round(age, 1) if age is not None else None,
                "latest_provider": observation.get("provider") if observation else None,
                "provider_station_id": observation.get("provider_station_id") if observation else None,
                "wigos_id": observation.get("wigos_id") if observation else None,
                "icao_code": observation.get("icao_code") if observation else None,
                "temperature_c": observation.get("temperature_c") if observation else None,
                "pressure_hpa": observation.get("pressure_hpa") if observation else None,
                "relative_humidity_pct": observation.get("relative_humidity_pct") if observation else None,
                "pressure_type": observation.get("pressure_type") if observation else None,
                "humidity_observation_type": observation.get("humidity_observation_type") if observation else None,
                "source_quality_flags": observation.get("source_quality_flags", []) if observation else [],
                "assessment_decision": assessment.get("decision") if assessment else None,
                "assessment_severity": assessment.get("severity") if assessment else None,
                "anomaly_score": assessment.get("anomaly_score") if assessment else None,
                "score_label": assessment.get("score_label") if assessment else None,
                "root_cause": assessment.get("root_cause") if assessment else None,
                "neighbor_support": assessment.get("neighbor_support") if assessment else None,
                "communication": communication,
                "health_status": quality_state(
                    assessment.get("decision") if assessment else None, status, communication
                ),
            }
            q = query.strip().lower()
            if q and q not in str(item.get("station_name") or "").lower() and q not in station_id.lower():
                continue
            if state and state.lower() not in str(item.get("state") or item.get("climate_zone") or "").lower():
                continue
            if source and source.upper() != str(item.get("latest_provider") or "").upper():
                continue
            if freshness and freshness.upper() != status:
                continue
            rows.append(item)
        return {
            "catalog_stations": len(catalog_by_id),
            "matched_stations": len(rows),
            "stations": rows[:limit],
            "generated_at_utc": snapshot["generated_at_utc"],
            "status_note": "Values and QC states exist only for received observations; catalog membership never creates readings or health.",
            "score_contract": "Operational QC exposes an uncalibrated anomaly evidence score, not a fault probability.",
        }

    @router.get("/operational/stations/{station_id}")
    def operational_station_detail(
        station_id: str,
        hours: int = Query(24, ge=1, le=24 * 30),
    ) -> Dict[str, Any]:
        store = require_store()
        metadata = station_metadata(station_id)
        if metadata is None:
            raise HTTPException(status_code=404, detail=f"Station '{station_id}' is not in the catalog")
        history = store.history(station_id, hours=hours, limit=10000)
        latest = history[-1] if history else None
        if latest is None:
            return {
                "metadata": metadata,
                "latest": None,
                "history": [],
                "neighbors": [],
                "assessment": None,
                "communication": operational_qc.assess_communication(station_id, []),
                "message": "No physical observation for this station exists in the operational store.",
            }
        snapshot = build_operational_snapshot()
        neighbors = snapshot["neighbors"].get(station_id) or aligned_neighbors(latest)
        cached_assessment = snapshot["assessments"].get(station_id)
        assessment = cached_assessment or operational_qc.analyze(latest, history, neighbors).to_dict()
        communication_history = store.history(station_id, hours=max(hours, 48), limit=10000)
        return {
            "metadata": metadata,
            "latest": latest,
            "history": history,
            "neighbors": neighbors,
            "assessment": assessment,
            "communication": snapshot["communications"].get(station_id) or operational_qc.assess_communication(station_id, communication_history),
            "history_is_causal": True,
            "source_observation_immutable": True,
        }

    @router.get("/operational/incidents")
    def operational_incidents(limit: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
        """Return evidence-backed active incidents from the stored observation snapshot.

        Weak statistical evidence remains ``SUSPECTED``.  Only an explicit
        physical-range violation is promoted immediately to ``CONFIRMED``.
        """
        snapshot = build_operational_snapshot()
        incidents: list[dict[str, Any]] = []
        for station_id, assessment in snapshot["assessments"].items():
            communication = snapshot["communications"].get(station_id, {})
            target = snapshot["latest"].get(station_id, {})
            decision = assessment.get("decision")
            is_communication = communication.get("decision") == "COMMUNICATION_FAILURE"
            if decision != "PROBABLE_SENSOR_FAULT" and not is_communication:
                continue
            metadata = station_metadata(station_id) or {}
            evidence = assessment.get("evidence") or []
            hard = any(item.get("code") == "PHYSICAL_RANGE_VIOLATION" for item in evidence)
            detected = str(target.get("observation_timestamp_utc") or snapshot["generated_at_utc"])
            fingerprint = f"{station_id}|{detected}|{'COMMUNICATION_FAILURE' if is_communication else decision}"
            incident_id = "SG-" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:12].upper()
            incidents.append({
                "incident_id": incident_id,
                "station_id": station_id,
                "station_name": metadata.get("station_name") or target.get("station_name") or station_id,
                "latitude": target.get("latitude") if target.get("latitude") is not None else metadata.get("latitude"),
                "longitude": target.get("longitude") if target.get("longitude") is not None else metadata.get("longitude"),
                "state": metadata.get("state") or metadata.get("climate_zone"),
                "decision": "COMMUNICATION_FAILURE" if is_communication else decision,
                "incident_state": "CONFIRMED" if hard else "SUSPECTED",
                "severity": (
                    "MEDIUM" if is_communication
                    else "CRITICAL" if hard
                    else assessment.get("severity") if assessment.get("severity") in {"HIGH", "MEDIUM", "LOW"}
                    else "HIGH"
                ),
                "anomaly_score": None if is_communication else assessment.get("anomaly_score"),
                "score_label": None if is_communication else assessment.get("score_label"),
                "calibrated_probability_available": False,
                "root_cause": "communication gap" if is_communication else assessment.get("root_cause"),
                "affected_sensors": ["communication"] if is_communication else assessment.get("affected_sensors", []),
                "detected_timestamp_utc": detected,
                "evidence": [communication] if is_communication else evidence,
                "neighbor_support": assessment.get("neighbor_support", {}),
                "recommendation": (
                    "Inspect the reporting path and station heartbeat; do not diagnose sensor hardware from silence alone."
                    if is_communication else assessment.get("recommendation")
                ),
                "corrections": assessment.get("corrections", []),
                "source_provider": target.get("provider"),
                "source_observation_key": target.get("observation_key"),
                "source_observation_immutable": True,
            })
        incidents.sort(
            key=lambda item: (item["incident_state"] == "CONFIRMED", item.get("anomaly_score") or 0.0),
            reverse=True,
        )
        return {
            "count": len(incidents),
            "incidents": incidents[:limit],
            "generated_at_utc": snapshot["generated_at_utc"],
            "contract": "SUSPECTED is evidence for operator review; it is not a verified hardware diagnosis.",
        }

    @router.get("/ingestion/health")
    def ingestion_health() -> Dict[str, Any]:
        health = require_store().ingestion_health()
        health["store_error"] = store_error or None
        return health

    @router.get("/sources/freshness")
    def source_freshness() -> Dict[str, Any]:
        store = require_store()
        freshness = store.source_freshness()
        observed = {str(row.get("provider")): row for row in freshness}
        providers = []
        for provider, access in (
            ("OPEN_METEO_LIVE", "active_live_weather_api"),
            ("IMD_AWS", "configured" if manager.imd_api.configured else "credentials_not_configured"),
            ("IMD_WIS2", "public_official_fallback"),
            ("METAR", "airport_observation_fallback"),
        ):
            providers.append({
                "provider": provider,
                "access": access,
                "freshness": observed.get(provider),
            })
        return {
            "providers": providers,
            "source_events": store.source_events(limit=50),
            "reference_model_is_station_observation": False,
        }

    @router.get("/provenance")
    def data_provenance() -> Dict[str, Any]:
        return {
            "priority": ["OPEN_METEO_LIVE", "IMD_AWS", "IMD_WIS2", "METAR", "REFERENCE_MODEL"],
            "sources": {
                "OPEN_METEO_LIVE": {
                    "role": "active physical weather observation stream (Option A - 1,008 AWS)",
                    "configured": True,
                    "endpoint": "https://api.open-meteo.com/v1/forecast",
                },
                "IMD_AWS": {
                    "role": "primary physical AWS/ARG observations",
                    "configured": manager.imd_api.configured,
                    "endpoint": manager.imd_api.endpoint,
                },
                "IMD_WIS2": {
                    "role": "official public SYNOP observation fallback",
                    "endpoint": "https://wis2box.imd.gov.in/oapi",
                },
                "METAR": {
                    "role": "limited airport observation fallback",
                    "relative_humidity": "derived from reported temperature and dew point",
                    "pressure": "ALTIMETER_QNH",
                },
                "REFERENCE_MODEL": {
                    "role": "regional weather context only",
                    "persisted_as_station_observation": False,
                },
            },
            "scientific_contract": {
                "model_meteorological_inputs": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
                "pressure_types_never_silently_mixed": True,
                "raw_values_overwritten": False,
                "uncalibrated_scores_labelled_as_probability": False,
            },
            "storage": require_store().durability,
        }

    @router.post("/ingestion/run")
    def run_ingestion(
        providers: str = Query("IMD_API,WIS2,METAR"),
        authorization: Optional[str] = Header(None),
    ) -> Dict[str, Any]:
        expected = os.getenv("SKYGUARD_INGESTION_TOKEN", "").strip()
        if not expected:
            raise HTTPException(status_code=503, detail="SKYGUARD_INGESTION_TOKEN is not configured")
        supplied = (authorization or "").removeprefix("Bearer ").strip()
        if supplied != expected:
            raise HTTPException(status_code=401, detail="Invalid ingestion token")
        service = IngestionService(require_store(), root=root)
        requested = [item.strip() for item in providers.split(",") if item.strip()]
        return service.run_once(requested)

    return router

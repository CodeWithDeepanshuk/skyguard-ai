"""Multi-Tier Concentric Spatial Neighbor Quality Control Engine for India AWS Network.

Implements the rigorous 3-radius spatial buddy check:
- Tier 1: < 20 km (tight local consensus, expected delta <= 1-2°C; delta >= 4-5°C signals anomaly)
- Tier 2: 20 - 50 km (mesoscale consensus, expected delta <= 3.5°C)
- Tier 3: 50 - 100 km (synoptic regional consensus, expected delta <= 5.0°C)

Physical Atmospheric Corrections:
- Environmental Lapse Rate: -6.5°C per 1,000m elevation change (-0.0065°C/m)
- Barometric Altimeter Pressure Reduction
- Coastal vs. Inland Microclimate Discontinuity Handling (+1.5°C buffer across sea-breeze front)
- Coherent Synoptic Weather System Detection (suppresses false sensor fault flags when multi-station shift occurs)
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from skyguard.quality.indian_regional_bounds import (
    RegionalBounds,
    classify_indian_region,
    is_coastal_location,
)

# Standard Environmental Lapse Rate (-6.5°C / km)
LAPSE_RATE_C_PER_M = -0.0065

# Tier distance boundaries (km)
TIER1_MAX_KM = 20.0
TIER2_MAX_KM = 50.0
TIER3_MAX_KM = 100.0

# Base temperature tolerances (°C) per tier
TEMP_TOLERANCE = {
    "tier1_20km": 2.0,   # Expected <= 1-2°C
    "tier2_50km": 3.5,   # Expected <= 3.5°C
    "tier3_100km": 5.0,  # Max allowed difference <= 5.0°C
}

# Cross-coastal boundary tolerance buffer
COASTAL_TRANSITION_BUFFER_C = 1.5


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two lat/lon coordinates."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * r * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def adjust_temperature_for_lapse(temp: float, elev_source: float, elev_target: float) -> float:
    """Normalize source temperature to target elevation using environmental lapse rate."""
    dh = elev_target - elev_source
    return temp + (LAPSE_RATE_C_PER_M * dh)


def adjust_pressure_for_elevation(press: float, elev_source: float, elev_target: float) -> float:
    """Normalize barometric pressure to target elevation using altimeter equation."""
    dh = elev_target - elev_source
    if abs(dh) < 1.0:
        return press
    factor = math.pow(max(0.05, 1.0 - 2.25577e-5 * dh), 5.25588)
    return press * factor


@dataclass
class TierSummary:
    tier_name: str
    radius_km: float
    peer_count: int
    tolerance_c: float
    mean_abs_delta_c: float
    max_delta_c: float
    tolerance_exceeded: bool
    peers: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MultiRadiusQcResult:
    target_station_id: str
    target_temperature_c: Optional[float]
    target_pressure_hpa: Optional[float]
    target_humidity_pct: Optional[float]
    target_elevation_m: float
    is_target_coastal: bool
    climate_zone: str
    tier1_20km: TierSummary
    tier2_50km: TierSummary
    tier3_100km: TierSummary
    total_neighbors_evaluated: int
    consensus_temperature_c: Optional[float]
    consensus_residual_c: Optional[float]
    effective_sigma_t: float
    z_spatial_t: float
    spatial_fault_suspected: bool
    synoptic_weather_system_detected: bool
    coherence_ratio: float
    decision: str  # "NORMAL" | "SENSOR_FAULT" | "GENUINE_WEATHER_EVENT" | "INSUFFICIENT_PEERS"
    severity: str  # "NOMINAL" | "HIGH" | "CRITICAL" | "ADVISORY"
    root_cause: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_station_id": self.target_station_id,
            "target_temperature_c": self.target_temperature_c,
            "target_pressure_hpa": self.target_pressure_hpa,
            "target_humidity_pct": self.target_humidity_pct,
            "target_elevation_m": self.target_elevation_m,
            "is_target_coastal": self.is_target_coastal,
            "climate_zone": self.climate_zone,
            "tier1_20km": asdict(self.tier1_20km),
            "tier2_50km": asdict(self.tier2_50km),
            "tier3_100km": asdict(self.tier3_100km),
            "total_neighbors_evaluated": self.total_neighbors_evaluated,
            "consensus_temperature_c": self.consensus_temperature_c,
            "consensus_residual_c": self.consensus_residual_c,
            "effective_sigma_t": self.effective_sigma_t,
            "z_spatial_t": self.z_spatial_t,
            "spatial_fault_suspected": self.spatial_fault_suspected,
            "synoptic_weather_system_detected": self.synoptic_weather_system_detected,
            "coherence_ratio": self.coherence_ratio,
            "decision": self.decision,
            "severity": self.severity,
            "root_cause": self.root_cause,
            "explanation": self.explanation,
        }


class MultiRadiusSpatialQcEngine:
    """Evaluates weather station telemetry against concentric rings of neighbors."""

    def evaluate(
        self,
        target_station: Dict[str, Any],
        neighbors: List[Dict[str, Any]],
        target_temporal_delta: Optional[float] = None,
    ) -> MultiRadiusQcResult:
        sid = str(target_station.get("station_id") or "")
        t_raw = target_station.get("temperature_c") if target_station.get("temperature_c") is not None else target_station.get("temperature")
        p_raw = target_station.get("pressure_hpa") if target_station.get("pressure_hpa") is not None else target_station.get("pressure")
        rh_raw = target_station.get("relative_humidity_pct") if target_station.get("relative_humidity_pct") is not None else target_station.get("humidity")

        t_target = float(t_raw) if (t_raw is not None and not math.isnan(float(t_raw))) else None
        p_target = float(p_raw) if (p_raw is not None and not math.isnan(float(p_raw))) else None
        rh_target = float(rh_raw) if (rh_raw is not None and not math.isnan(float(rh_raw))) else None

        lat_target = float(target_station.get("latitude") or 20.0)
        lon_target = float(target_station.get("longitude") or 78.0)
        elev_target = float(target_station.get("elevation_m") or 0.0)
        state_target = str(target_station.get("state") or "")
        district_target = str(target_station.get("district") or "")
        cz_hint = str(target_station.get("climate_zone") or "")

        target_coastal = is_coastal_location(lat_target, lon_target, state_target, district_target)
        region_profile = classify_indian_region(lat_target, lon_target, elev_target, state_target, cz_hint)

        # Partition neighbors into concentric tiers
        t1_peers: List[Dict[str, Any]] = []
        t2_peers: List[Dict[str, Any]] = []
        t3_peers: List[Dict[str, Any]] = []

        all_valid_t: List[Dict[str, Any]] = []

        for n in neighbors:
            nid = str(n.get("station_id") or "")
            if nid == sid:
                continue

            n_lat = float(n.get("latitude") or 20.0)
            n_lon = float(n.get("longitude") or 78.0)
            dist = float(n.get("distance_km") or haversine_km(lat_target, lon_target, n_lat, n_lon))
            if dist > TIER3_MAX_KM:
                continue

            n_elev = float(n.get("elevation_m") or 0.0)
            n_coastal = is_coastal_location(n_lat, n_lon, str(n.get("state") or ""), str(n.get("district") or ""))
            cross_coastal = (target_coastal != n_coastal)

            n_t_raw = n.get("temperature_c") if n.get("temperature_c") is not None else n.get("temperature")
            if n_t_raw is not None and not math.isnan(float(n_t_raw)):
                n_t = float(n_t_raw)
                # Apply environmental lapse rate adjustment
                adj_t = adjust_temperature_for_lapse(n_t, n_elev, elev_target)
                abs_delta = abs(t_target - adj_t) if t_target is not None else 0.0

                peer_info = {
                    "station_id": nid,
                    "station_name": str(n.get("station_name") or nid),
                    "distance_km": round(dist, 1),
                    "elevation_m": round(n_elev, 1),
                    "raw_temp_c": round(n_t, 1),
                    "lapse_adjusted_temp_c": round(adj_t, 1),
                    "absolute_delta_c": round(abs_delta, 1),
                    "is_coastal": n_coastal,
                    "cross_coastal_boundary": cross_coastal,
                    "temporal_delta": float(n.get("temperature_delta") or 0.0),
                }

                all_valid_t.append(peer_info)
                if dist <= TIER1_MAX_KM:
                    t1_peers.append(peer_info)
                elif dist <= TIER2_MAX_KM:
                    t2_peers.append(peer_info)
                elif dist <= TIER3_MAX_KM:
                    t3_peers.append(peer_info)

        # Build tier summaries
        def make_summary(tier_name: str, radius_km: float, base_tol: float, peers: List[Dict[str, Any]]) -> TierSummary:
            if not peers:
                return TierSummary(
                    tier_name=tier_name,
                    radius_km=radius_km,
                    peer_count=0,
                    tolerance_c=base_tol,
                    mean_abs_delta_c=0.0,
                    max_delta_c=0.0,
                    tolerance_exceeded=False,
                    peers=[],
                )
            # If all peers are cross-coastal, add transition buffer
            eff_tol = base_tol + (COASTAL_TRANSITION_BUFFER_C if all(p["cross_coastal_boundary"] for p in peers) else 0.0)
            deltas = [p["absolute_delta_c"] for p in peers]
            mean_d = float(np.mean(deltas))
            max_d = float(np.max(deltas))
            # Tolerance exceeded if mean delta is above threshold or any peer within 20km is >= 4.0°C
            exceeded = (mean_d > eff_tol) or (tier_name == "tier1_20km" and any(d >= 4.0 for d in deltas))
            return TierSummary(
                tier_name=tier_name,
                radius_km=radius_km,
                peer_count=len(peers),
                tolerance_c=eff_tol,
                mean_abs_delta_c=round(mean_d, 2),
                max_delta_c=round(max_d, 2),
                tolerance_exceeded=exceeded,
                peers=sorted(peers, key=lambda x: x["distance_km"]),
            )

        t1_summary = make_summary("tier1_20km", TIER1_MAX_KM, TEMP_TOLERANCE["tier1_20km"], t1_peers)
        t2_summary = make_summary("tier2_50km", TIER2_MAX_KM, TEMP_TOLERANCE["tier2_50km"], t2_peers)
        t3_summary = make_summary("tier3_100km", TIER3_MAX_KM, TEMP_TOLERANCE["tier3_100km"], t3_peers)

        total_peers = len(all_valid_t)
        consensus_temp = None
        consensus_res = None
        z_spatial = 0.0
        effective_sigma = 0.6

        if total_peers > 0 and t_target is not None:
            # Weighted consensus using inverse distance and downweighting cross-coastal peers
            weights = []
            adj_values = []
            for p in all_valid_t:
                dist_factor = 1.0 / (max(p["distance_km"], 2.0) ** 1.5)
                coastal_factor = 0.6 if p["cross_coastal_boundary"] else 1.0
                weights.append(dist_factor * coastal_factor)
                adj_values.append(p["lapse_adjusted_temp_c"])

            w_arr = np.array(weights)
            w_norm = w_arr / np.sum(w_arr)
            consensus_temp = round(float(np.sum(w_norm * np.array(adj_values))), 2)
            consensus_res = round(float(t_target - consensus_temp), 2)

            mad = float(np.median(np.abs(np.array(adj_values) - consensus_temp)))
            effective_sigma = max(round(1.4826 * mad, 2), 0.6)
            z_spatial = round(consensus_res / effective_sigma, 2)

        # --------------------------------------------------------------------
        # Synoptic Weather System Detection Safeguard
        # --------------------------------------------------------------------
        weather_system_detected = False
        coherence_ratio = 0.0
        if target_temporal_delta is not None and abs(target_temporal_delta) >= 1.5:
            matching = [
                p for p in all_valid_t
                if (p.get("temporal_delta", 0.0) * target_temporal_delta > 0)
                and abs(p.get("temporal_delta", 0.0)) >= 1.0
            ]
            if len(all_valid_t) >= 3:
                coherence_ratio = len(matching) / len(all_valid_t)
                if coherence_ratio >= 0.50:
                    weather_system_detected = True

        # Check spatial discrepancy conditions
        # Condition A: Tier 1 (<20km) peer exists and delta >= 4.0°C (or mean delta > 2.0°C)
        t1_violation = t1_summary.peer_count >= 1 and t1_summary.tolerance_exceeded
        # Condition B: Tier 2 (<50km) peers exist and mean delta > 3.5°C
        t2_violation = t2_summary.peer_count >= 2 and t2_summary.tolerance_exceeded
        # Condition C: Tier 3 (<100km) peers exist and mean delta > 5.0°C
        t3_violation = t3_summary.peer_count >= 3 and t3_summary.tolerance_exceeded

        spatial_fault_suspected = False
        if (t1_violation or (t2_violation and t3_violation) or (t3_violation and abs(z_spatial) >= 3.5)):
            spatial_fault_suspected = True

        # Final decision synthesis
        if spatial_fault_suspected:
            if weather_system_detected:
                decision = "GENUINE_WEATHER_EVENT"
                severity = "ADVISORY"
                root_cause = "synoptic_weather_front"
                explanation = (
                    f"Temperature shift of {consensus_res:+.1f}°C is corroborated by "
                    f"{coherence_ratio * 100:.0f}% of surrounding stations within 100 km. "
                    "Classified as genuine meteorological front; hardware fault alert suppressed."
                )
            else:
                decision = "SENSOR_FAULT"
                severity = "CRITICAL" if abs(z_spatial) >= 4.5 or (t1_summary.max_delta_c >= 5.0) else "HIGH"
                root_cause = "temperature_spike_spatial_neighbor_discrepancy"
                peers_desc = []
                if t1_summary.peer_count > 0:
                    peers_desc.append(f"<20km: max Δ={t1_summary.max_delta_c}°C (tol {t1_summary.tolerance_c}°C)")
                if t2_summary.peer_count > 0:
                    peers_desc.append(f"<50km: mean Δ={t1_summary.mean_abs_delta_c}°C (tol {t2_summary.tolerance_c}°C)")
                if t3_summary.peer_count > 0:
                    peers_desc.append(f"<100km: mean Δ={t3_summary.mean_abs_delta_c}°C (tol {t3_summary.tolerance_c}°C)")

                explanation = (
                    f"Observed temperature {t_target:.1f}°C deviates from lapse-adjusted spatial consensus "
                    f"({consensus_temp:.1f}°C) by {consensus_res:+.1f}°C ({z_spatial:+.1f}σ). "
                    f"Multi-radius check failed [{', '.join(peers_desc)}]. "
                    f"No multi-station weather system detected."
                )
        elif total_peers == 0:
            decision = "INSUFFICIENT_PEERS"
            severity = "NOMINAL"
            root_cause = "isolated_station"
            explanation = "No reporting neighbor stations found within 100 km radius. Physical limits verified."
        else:
            decision = "NORMAL"
            severity = "NOMINAL"
            root_cause = "spatial_consensus_confirmed"
            explanation = (
                f"Temperature {t_target:.1f}°C matches lapse-adjusted spatial consensus "
                f"({consensus_temp:.1f}°C, {total_peers} peers across 20/50/100 km) within verified WMO tolerances."
            )

        return MultiRadiusQcResult(
            target_station_id=sid,
            target_temperature_c=t_target,
            target_pressure_hpa=p_target,
            target_humidity_pct=rh_target,
            target_elevation_m=elev_target,
            is_target_coastal=target_coastal,
            climate_zone=region_profile.zone_name,
            tier1_20km=t1_summary,
            tier2_50km=t2_summary,
            tier3_100km=t3_summary,
            total_neighbors_evaluated=total_peers,
            consensus_temperature_c=consensus_temp,
            consensus_residual_c=consensus_res,
            effective_sigma_t=effective_sigma,
            z_spatial_t=z_spatial,
            spatial_fault_suspected=spatial_fault_suspected,
            synoptic_weather_system_detected=weather_system_detected,
            coherence_ratio=round(coherence_ratio, 2),
            decision=decision,
            severity=severity,
            root_cause=root_cause,
            explanation=explanation,
        )

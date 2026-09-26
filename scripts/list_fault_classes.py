#!/usr/bin/env python3
"""Fault Class Taxonomy and Signature Verifier for SkyGuard AI.

Catalogs the full taxonomy of detectable sensor anomalies, diagnostic root causes,
and genuine weather event discrimination signatures supported by SkyGuard AI.

Produces:
- artifacts/fault_classes.json
- artifacts/fault_classes.md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

FAULT_TAXONOMY: List[Dict[str, Any]] = [
    {
        "class_id": "FC-01",
        "signature_name": "Physical Possibility Limit Violation",
        "affected_parameters": ["Temperature", "Pressure", "Relative Humidity"],
        "detection_mechanism": "Deterministic Regional Bounds Envelope (8 Indian Climate Zones)",
        "diagnostic_label": "temperature_physical_bounds_violation / pressure_physical_bounds_violation / humidity_physical_bounds_violation",
        "severity": "CRITICAL",
        "evidence_stream": "Stream 1 / Stream 5 (Physical Possibility)",
        "scientific_basis": "IMD Pune historical extremes and thermodynamic limits (WMO-No. 8).",
        "technician_action": "Inspect transducer integrity, wiring short-circuits, and ADC voltage reference.",
    },
    {
        "class_id": "FC-02",
        "signature_name": "Sensor Flatline / Stuck Reading",
        "affected_parameters": ["Temperature", "Relative Humidity"],
        "detection_mechanism": "Consecutive Variance & Frozen Digit Detector (>= 5 consecutive identical readings)",
        "diagnostic_label": "stuck_sensor_flatline",
        "severity": "CRITICAL",
        "evidence_stream": "Stream 3 (Temporal & Drift Indicators)",
        "scientific_basis": "Natural diurnal atmospheric variation precludes constant temperature/humidity readings over multi-hour intervals.",
        "technician_action": "Check transducer communication bus, logger analog input channel, and data logger firmware freeze.",
    },
    {
        "class_id": "FC-03",
        "signature_name": "Persistent Calibration Drift / Bias",
        "affected_parameters": ["Temperature", "Pressure"],
        "detection_mechanism": "Causal CUSUM & Monotonic Linear Drift State Machine (cumulative drift > 2.5 sigma)",
        "diagnostic_label": "calibration_drift_bias",
        "severity": "HIGH",
        "evidence_stream": "Stream 3 / Stream 4 (Drift State Machine & Ensemble)",
        "scientific_basis": "Aging sensor elements (e.g. platinum RTD resistance shift or capacitive polymer degradation) cause slow monotonic bias.",
        "technician_action": "Perform field calibration comparison using travelling standard (e.g. Vaisala PTB330 barometer or certified reference thermometer).",
    },
    {
        "class_id": "FC-04",
        "signature_name": "Tier 1 Micro-Scale Spatial Divergence (<20 km)",
        "affected_parameters": ["Air Temperature"],
        "detection_mechanism": "Concentric KD-Tree Buddy Check (tolerance: 2.0°C; anomaly flag: >= 4.0°C delta)",
        "diagnostic_label": "temperature_spatial_outlier",
        "severity": "CRITICAL",
        "evidence_stream": "Stream 2 / Stream 5 (Spatial Lapse-Rate Consensus)",
        "scientific_basis": "Homogeneous microclimates within 20 km under identical synoptic conditions cannot sustain large thermal gradients without topographical cause.",
        "technician_action": "Inspect solar radiation shield cleanliness, aspiration fan functionality, and local heat source obstructions.",
    },
    {
        "class_id": "FC-05",
        "signature_name": "Tier 2 Meso-Scale Spatial Divergence (20-50 km)",
        "affected_parameters": ["Air Temperature"],
        "detection_mechanism": "Elevation Lapse-Rate Adjusted Buddy Check (tolerance: 3.5°C with -6.5°C/km ELR)",
        "diagnostic_label": "temperature_mesoscale_divergence",
        "severity": "HIGH",
        "evidence_stream": "Stream 2 / Stream 5 (Spatial Consensus)",
        "scientific_basis": "Mesoscale terrain-adjusted consensus accounts for elevation differences via environmental lapse rate.",
        "technician_action": "Verify station elevation metadata in master catalog; inspect sensor calibration offset.",
    },
    {
        "class_id": "FC-06",
        "signature_name": "Barometric Pressure Drift / Offset",
        "affected_parameters": ["Barometric Pressure"],
        "detection_mechanism": "Altimeter-Reduced Hydrostatic Peer Consensus (residual > 4.5 sigma, > 12 hPa)",
        "diagnostic_label": "barometric_pressure_drift",
        "severity": "HIGH",
        "evidence_stream": "Stream 2 / Stream 4 (Altimeter Reduction & Ensemble)",
        "scientific_basis": "Atmospheric pressure is regionally coherent; hydrostatic reduction to MSLP enables strict buddy checking across large distances.",
        "technician_action": "Check barometer port vent tube for water accumulation, insect blockage, or pressure transducer offset.",
    },
    {
        "class_id": "FC-07",
        "signature_name": "Relative Humidity Saturation / Degradation",
        "affected_parameters": ["Relative Humidity"],
        "detection_mechanism": "Spatial Consensus & Saturation Envelope Check (residual > 4.8 sigma, > 25% RH difference)",
        "diagnostic_label": "relative_humidity_saturation",
        "severity": "MEDIUM",
        "evidence_stream": "Stream 2 / Stream 5 (Spatial Consensus)",
        "scientific_basis": "Capacitive hygrometers frequently fail by saturating at 100% or reading near 0% due to polymer contamination.",
        "technician_action": "Inspect capacitive humidity sensor filter cap for dust/chemical contamination; replace sensor element if contaminated.",
    },
    {
        "class_id": "FC-08",
        "signature_name": "Transient Spike / Burst Anomaly",
        "affected_parameters": ["Temperature", "Pressure", "Relative Humidity"],
        "detection_mechanism": "Temporal Step-Rate & Reconstruction Error (isolated single-sample deviation returning to baseline)",
        "diagnostic_label": "transient_spike_burst",
        "severity": "MEDIUM",
        "evidence_stream": "Stream 1 (Neural Autoencoder Reconstruction)",
        "scientific_basis": "Electrical EMI spikes, lightning induction, or telemetry bit-flips cause transient non-physical spikes.",
        "technician_action": "Inspect electrical grounding, cable shielding, and surge protection modules.",
    },
    {
        "class_id": "GW-01",
        "signature_name": "Coherent Synoptic Weather Event (Non-Fault)",
        "affected_parameters": ["Temperature", "Pressure", "Wind"],
        "detection_mechanism": "Synoptic Front Coherence Discriminator (>= 50% neighbor stations shift with >= 3.0°C step drop)",
        "diagnostic_label": "synoptic_weather_front",
        "severity": "ADVISORY (GENUINE_WEATHER_EVENT)",
        "evidence_stream": "Stream 5 (Synoptic Weather Coherence Engine)",
        "scientific_basis": "Thunderstorm gust fronts, squalls, or cold fronts cause rapid multi-station temperature drops that naive QC misclassifies as sensor faults.",
        "technician_action": "Zero maintenance required. Suppress sensor fault alerts and log as genuine atmospheric event.",
    },
]


def main() -> None:
    print("=" * 70)
    print("SKYGUARD AI - FAULT CLASS TAXONOMY & SIGNATURE VERIFIER")
    print("=" * 70)

    print(f"Total Detectable Fault Signatures: {len(FAULT_TAXONOMY)}")
    for fc in FAULT_TAXONOMY:
        print(f"  [{fc['class_id']}] {fc['signature_name']} -> {fc['severity']} ({fc['evidence_stream']})")

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_classes": len(FAULT_TAXONOMY),
        "sensor_fault_classes_count": sum(1 for c in FAULT_TAXONOMY if "FC" in c["class_id"]),
        "weather_event_classes_count": sum(1 for c in FAULT_TAXONOMY if "GW" in c["class_id"]),
        "taxonomy": FAULT_TAXONOMY,
    }

    # Save JSON artifact
    json_path = ARTIFACTS_DIR / "fault_classes.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote JSON artifact to: {json_path}")

    # Save Markdown artifact
    md_path = ARTIFACTS_DIR / "fault_classes.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# SkyGuard AI: Detectable Fault Classes & Diagnostic Signatures\n\n")
        f.write(f"**Audit Timestamp**: `{report['timestamp_utc']}`  \n")
        f.write(f"**Total Registered Signatures**: **{report['total_classes']} classes** ({report['sensor_fault_classes_count']} sensor faults, {report['weather_event_classes_count']} genuine weather front discriminator)  \n\n")

        f.write("## Master Fault Classification Matrix\n\n")
        f.write("| ID | Signature Name | Parameters | Mechanism | Severity | Evidence Stream | Recommended Technician Action |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for c in FAULT_TAXONOMY:
            f.write(f"| **{c['class_id']}** | {c['signature_name']} | {', '.join(c['affected_parameters'])} | {c['detection_mechanism']} | `{c['severity']}` | {c['evidence_stream']} | {c['technician_action']} |\n")

        f.write("\n## Scientific Reframing Statement\n\n")
        f.write("> [!NOTE]\n")
        f.write("> In compliance with scientific integrity principles, SkyGuard AI presents these outputs as **Fault Signature Hypotheses** backed by empirical sensor residuals, rather than definitive certified hardware failure declarations. Physical inspection and field verification remain the responsibility of qualified meteorological maintenance technicians.\n\n")
        f.write("---\n*Generated by `scripts/list_fault_classes.py`.*\n")

    print(f"Wrote Markdown artifact to: {md_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()

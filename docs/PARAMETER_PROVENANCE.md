# SkyGuard AI: Parameter Provenance & Claim Registry

**SIH Problem Statement**: 26073 (Automated Quality Control and Fault Detection for Automated Weather Stations)  
**System Architecture**: Centralized, Versioned Configuration Architecture  
**Document Version**: 1.2.0  
**Last Audited**: 2026-09-26  

---

## 1. Executive Summary & Architectural Integrity

In production meteorology and mission-critical automated weather station (AWS) quality control, credibility demands total scientific defensibility and auditability. Sweeping promotional statements such as *"Zero Hardcoded Numbers"* or claiming unverified field hardware replacements undermine technical rigor before meteorological juries.

SkyGuard AI enforces a **Centralized, Versioned Configuration Architecture**. Every physical boundary, spatial radius, tolerance threshold, and ensemble fusion weight is maintained in human-readable, machine-validatable YAML files located in [`config/`](../config/).

Every parameter in SkyGuard AI belongs to one of four strictly audited categories:
1. **Category A: Scientific Domain Limits & Physical Constants**: Derived from fundamental atmospheric thermodynamics, WMO standards, and certified IMD Pune historical records.
2. **Category B: Configurable Engineering Assumptions**: Operational policy choices, concentric spatial radii, and maintenance tolerances grounded in meteorological literature.
3. **Category C: Model-Derived Parameters**: Weights, tree structures, and calibration coefficients learned through machine learning optimization.
4. **Category D: Runtime-Derived Empirical Metrics**: Measured execution times, operational latencies, and empirical false alarm rates evaluated against real and holdout datasets.

---

## 2. Parameter Classification Taxonomy

```
+-----------------------------------------------------------------------------------+
|                           SKYGUARD AI PARAMETER TAXONOMY                          |
+-----------------------------------------------------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
+-------v-----------------------+                                   +-------v-----------------------+
|  Deterministic & Physical     |                                   |  Statistical & Empirical      |
+-------+-----------------------+                                   +-------+-----------------------+
        |                                                                   |
   +----+--------------------+                                         +----+--------------------+
   |                         |                                         |                         |
+--v-------------------+ +---v------------------+                +-----v--------------+ +--------v-------------+
|    CATEGORY A        | |    CATEGORY B        |                |    CATEGORY C      | |     CATEGORY D       |
| Scientific Constants | | Configurable Policy  |                | Learned ML Weights | | Measured Run Metrics |
| & Regional Boundaries| | & QC Ring Tolerances |                | & Tree Splits      | | & Evaluated Rates    |
+----------------------+ +----------------------+                +--------------------+ +----------------------+
```

### Category A: Scientific Domain Limits & Physical Constants
- **Definition**: Universal physical constants and certified climatological boundaries that cannot be altered by software configuration without violating the laws of physics or certified climatological history.
- **Governing Standard**: WMO-No. 8 (*Guide to Instruments and Methods of Observation*), WMO-No. 544, IMD National Data Centre (NDC) Pune Climate Normals.
- **Mutability**: Immutable constants; zone boundaries update only upon official IMD national extreme certification.

### Category B: Configurable Engineering Assumptions & Policy
- **Definition**: Meteorological thresholds, concentric buddy-check radii, and sensor health penalty scales configured by AWS network administrators to match network density and operational maintenance policies.
- **Governing Standard**: Centralized in [`config/spatial_qc.yaml`](../config/spatial_qc.yaml), [`config/model_fusion.yaml`](../config/model_fusion.yaml), and [`config/health.yaml`](../config/health.yaml).
- **Mutability**: Version-controlled, configurable with full parameter audit trails.

### Category C: Model-Derived Parameters
- **Definition**: Continuous weights and decision rules optimized during offline training on GPU/CPU compute platforms and serialized into versioned model artifacts.
- **Governing Standard**: Model card specifications in `models/phase10_final.joblib` and `models/spatio_temporal_neural_engine.pt`.
- **Mutability**: Fixed once artifact hash is certified in `manifest.json`.

### Category D: Runtime-Derived Empirical Metrics
- **Definition**: Metrics measured empirically during runtime execution against real observation records and holdout splits.
- **Governing Standard**: Validated through reproducible benchmark scripts (`scripts/benchmark_inference.py`, `scripts/evaluate_false_alarm_rate.py`).
- **Mutability**: Dynamically reported per execution platform and evaluated dataset slice.

---

## 3. Master Parameter Registry

The following table catalogs the core operational parameters of SkyGuard AI, establishing exact provenance, rationale, and configuration references:

| Parameter Identifier | Configuration Location | Default Value | Unit | Category | Scientific / Engineering Grounding | Validation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lapse_rate_c_per_m` | `config/spatial_qc.yaml` | `-0.0065` | $^\circ\text{C}/\text{m}$ | **A** | ICAO Standard Atmosphere Environmental Lapse Rate (ELR) in the troposphere ($-6.5^\circ\text{C}/\text{km}$). | **VERIFIED (Physical)** |
| `altimeter_exponent` | Code derivation | `5.25588` | dimensionless | **A** | Standard barometric altimeter formula exponent $\frac{g \cdot M}{R \cdot L}$ for hydrostatic elevation reduction. | **VERIFIED (Physical)** |
| `z1_temp_min_c` | `config/regional_qc.yaml` | `-35.0` | $^\circ\text{C}$ | **A** | IMD Dras / Leh historical records (official low: $-45.0^\circ\text{C}$ with $-35.0^\circ\text{C}$ AWS operational envelope). | **VERIFIED (IMD)** |
| `z2_temp_max_c` | `config/regional_qc.yaml` | `52.0` | $^\circ\text{C}$ | **A** | IMD Phalodi (2016 record: $51.0^\circ\text{C}$) and Churu summer extremes ($52.0^\circ\text{C}$ envelope). | **VERIFIED (IMD)** |
| `z6_pressure_min_hpa`| `config/regional_qc.yaml` | `915.0` | $\text{hPa}$ | **A** | IMD Bay of Bengal Super Cyclone lowest recorded central pressures (1999 Odisha Super Cyclone: $912\text{ hPa}$). | **VERIFIED (IMD)** |
| `tier1_radius_km` | `config/spatial_qc.yaml` | `20.0` | $\text{km}$ | **B** | Micro-alpha/meso-gamma spatial correlation radius for local buddy checking. | **CONFIGURABLE** |
| `tier1_temp_tol_c` | `config/spatial_qc.yaml` | `2.0` | $^\circ\text{C}$ | **B** | WMO adjacent station maximum expected discrepancy within homogeneous microclimates. | **CONFIGURABLE** |
| `tier2_radius_km` | `config/spatial_qc.yaml` | `50.0` | $\text{km}$ | **B** | Meso-beta spatial correlation radius for regional terrain consistency. | **CONFIGURABLE** |
| `tier2_temp_tol_c` | `config/spatial_qc.yaml` | `3.5` | $^\circ\text{C}$ | **B** | Mesoscale elevation-adjusted variance limit across neighboring valleys and plains. | **CONFIGURABLE** |
| `tier3_radius_km` | `config/spatial_qc.yaml` | `100.0` | $\text{km}$ | **B** | Synoptic-scale bounding radius for all-India AWS sparse network coverage. | **CONFIGURABLE** |
| `tier3_temp_tol_c` | `config/spatial_qc.yaml` | `5.0` | $^\circ\text{C}$ | **B** | Synoptic-scale maximum allowable divergence before flagging anomaly. | **CONFIGURABLE** |
| `coastal_buffer_c` | `config/spatial_qc.yaml` | `1.5` | $^\circ\text{C}$ | **B** | Marine boundary layer sea-breeze thermal discontinuity compensation. | **CONFIGURABLE** |
| `cross_coastal_weight`| `config/spatial_qc.yaml`| `0.60` | ratio | **B** | Downweights peer stations located across the coastal boundary to prevent false divergence. | **CONFIGURABLE** |
| `synoptic_coherence` | `config/spatial_qc.yaml` | `0.50` | ratio | **B** | Minimum fraction of neighbor stations showing directional shift during cold fronts/thunderstorms. | **CONFIGURABLE** |
| `w_neural` | `config/model_fusion.yaml` | `0.40` | weight | **B** | Ensemble weight assigned to autoencoder reconstruction loss stream. | **CONFIGURABLE** |
| `w_drift` | `config/model_fusion.yaml` | `0.35` | weight | **B** | Ensemble weight assigned to non-linear CUSUM and flatline temporal indicators. | **CONFIGURABLE** |
| `w_spatial` | `config/model_fusion.yaml` | `0.25` | weight | **B** | Ensemble weight assigned to multi-radius lapse-rate peer consensus score. | **CONFIGURABLE** |
| `op_threshold` | `config/model_fusion.yaml` | `0.6845` | score | **B / C** | Calibrated operational anomaly threshold balancing false alarm rate and recall. | **CONFIGURABLE** |
| `health_nominal_cutoff`| `config/health.yaml` | `85.0` | index | **B** | Maintenance SLA policy: Stations scoring $\ge 85$ require routine inspection only. | **CONFIGURABLE** |
| `health_critical_cutoff`| `config/health.yaml`| `60.0` | index | **B** | Maintenance SLA policy: Stations scoring $< 60$ trigger technician work-order dispatch. | **CONFIGURABLE** |
| `rolling_window_days` | `config/health.yaml` | `7` | days | **B** | WMO rolling performance window smoothing diurnal cycles while tracking sensor drift. | **CONFIGURABLE** |
| `drift_penalty_sigma` | `config/health.yaml` | `12.0` | pts/$\sigma$ | **B** | Proactive penalty deducted from health index per standard deviation of persistent bias. | **CONFIGURABLE** |
| `lgbm_trees` | `models/phase10_final.joblib` | `100` | trees | **C** | Gradient boosted decision trees learned over 108 engineered features. | **MODEL-DERIVED** |
| `calibrated_probs` | `models/phase10_final.joblib` | Sigmoid fits | prob | **C** | Platt scaling calibration mapping raw classifier margin to posterior probability $P(\text{Fault}\mid x)$. | **MODEL-DERIVED** |
| `inference_latency_cpu`| Runtime benchmark | `2.56` | ms (med) | **D** | Measured local CPU algorithmic inference execution time per station-observation. | **RUNTIME-DERIVED** |
| `far_station_day` | Real holdout audit | `0.0125` | alerts/day | **D** | Empirically evaluated false alarm rate across 578,448 historical NOAA ISD observations. | **RUNTIME-DERIVED** |

---

## 4. Scientific Reframing: Fault Signature Hypotheses

### Operational Separation of Concerns
Automated machine learning software running on server infrastructure **cannot independently inspect physical transducers, wiring harnesses, or terminal blocks in the field**. 

Therefore, SkyGuard AI adopts a scientifically honest operational framing:

| Old / Naive Claim | Scientifically Defensible Framing | Operational Next Step |
| :--- | :--- | :--- |
| *"Confirmed Hardware Failure: Faulty PT100 RTD sensor element."* | **"Fault Signature Hypothesis: High-Confidence Temperature Sensor Drift / Anomaly."** | Directs maintenance dispatch to inspect PT100 wiring, radiation shield cleanliness, and logger terminal blocks. |
| *"Sensor element burned out; replace with spare unit."* | **"Transducer Open-Circuit / Flatline Signature Detected."** | Recommends field technician check transducer continuity, sensor connector seating, and reference voltage. |
| *"Barometer broken; hardware replacement required."* | **"Persistent Barometric Offset Against Regional Altimeter Consensus."** | Recommends field calibration check against calibrated travelling reference barometer (Vaisala PTB330). |
| *"100% Guaranteed Root Cause Discovery."* | **"Bayesian / Rule-Guided Diagnostic Isolation with Probabilistic Confidence."** | Provides explainable feature attributions and peer neighbor residuals to assist meteorologists in triage. |

---

## 5. Verification & Audit Trail Summary

- Every configuration parameter is loaded via [`src/skyguard/config.py`](../src/skyguard/config.py).
- Fallback defaults are hard-pinned to certified values so that the software fails safely if configuration files are temporarily unavailable.
- Parameter alterations are tracked through git commit history and version tags, ensuring 100% reproducibility before hackathon juries and scientific reviewers.

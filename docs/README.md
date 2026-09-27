# SkyGuard AI — Official Documentation Suite

Welcome to the comprehensive, authoritative technical and operational documentation for **SkyGuard AI (SIH 26073)** — *Autonomous Quality Control and Intelligent Fault Detection for India's National Automatic Weather Station (AWS) Network*.

---

## Documentation Navigation

This documentation suite is organized into four core, modular reference guides designed for technical evaluators, IMD operational leadership, and systems engineers:

```
docs/
├── README.md                                      <-- (You are here) Master Index & Quickstart
├── 01_PROJECT_OVERVIEW.md                         <-- Core Scope, Problem Statement, & Network Reality
├── 02_TECHNICAL_APPROACH_AND_DEEP_PIPELINE.md     <-- 9-Stage Architecture, Flow Diagrams, & Math Formulations
├── 03_FEASIBILITY_AND_VIABILITY.md                <-- Audited Benchmarks, Risk Matrix, & Hardware Footprint
├── 04_STRATEGIC_IMPACTS_AND_BENEFITS.md           <-- Operational ROI, IMD/NWP/PMFBY/NDMA Socioeconomic Impact
└── 05_SIH26073_COMPLIANCE_AND_USE_CASES.md        <-- SIH 26073 Direct Compliance, Official Example, & Code Guide
```

---

## Module Summaries

### [1. Project Overview & Operational Reality](01_PROJECT_OVERVIEW.md)
* **Scope & Problem Statement:** High-stakes challenge of silent sensor failures across **1,153 official IMD AWS stations** across 8 agro-climatic zones in India.
* **Strict 3-Sensor Contract:** Strict adherence to Temperature ($T$), Station Pressure ($P$), and Relative Humidity ($\text{RH}$), completely rejecting unverified auxiliary inputs.
* **Operational Reality Table:** Honest, verified status of what is operational in code today (manual/scripted authenticated import, local SQLite buffer, PyTorch TCN + LightGBM engine) vs. deployment roadmap (AWS EC2 static-IP proxy, cloud PostgreSQL hypertable).

### [2. Technical Approach & Deep Pipeline](02_TECHNICAL_APPROACH_AND_DEEP_PIPELINE.md)
* **Comprehensive Flow Diagrams:** Full Mermaid and ASCII end-to-end data pipeline diagrams from ingestion to operator dashboard.
* **9-Stage Deep Pipeline Breakdown:**
  1. Multi-Modal Ingestion Gateway (Manual Authenticated Import + Planned AWS EC2 Static-IP Proxy)
  2. Syntactic & Physical Sanity Gating ($Z_{\text{MSLP}}$, Hypsometric Barometric Elevation Normalization)
  3. Causal Spatio-Temporal Feature Engineering (Lagged Rolling CUSUM, Spatial Consensus Deliberation)
  4. Dual-Branch Neural & Gradient-Boosted Classification (Causal TCN + LightGBM)
  5. 9-Class Root-Cause Disambiguation (Drift, Spike, Stuck, Bias, Noise, Dropout, Shift, Erratic, Packet Corruption)
  6. TreeSHAP Local Interpretability & Attribution Scoring
  7. Physics-Constrained Spatial Virtual Repair (Elevation-Corrected IDW)
  8. Store-and-Forward SQLite Buffer & PostgreSQL Telemetry Persistence
  9. Next.js 14 Real-Time Web Application & Operator Alert Center

### [3. Feasibility and Viability](03_FEASIBILITY_AND_VIABILITY.md)
* **Audited Empirical Benchmarks (Frozen Artifact Verification):**
  - **Inference Latency:** Median $2.258\text{ ms}$, $P_{95} = 3.207\text{ ms}$ (Single CPU Core).
  - **Single-Core Throughput:** $204.7\text{ rows/sec}$.
  - **Model Footprint:** $5.2\text{ MiB}$ model weights, $<120\text{ MB}$ RAM footprint, zero GPU dependency.
  - **Classification Precision:** $86.21\%$ precision on locked spatio-temporal holdouts.
  - **Empirical False Alarm Rate:** $0.0028$ false alarms per station-day (1 alert every 357 days/station).
* **Operational Risk Matrix:** Five major deployment risks (telemetry dropouts, microclimatic anomalies, elevation bias, hardware degradation, operator alert fatigue) with mathematically grounded mitigations.
* **Direct Maintenance ROI:** Documented annual savings of **₹1.20–₹1.50 Crore** in field operations.

### [4. Strategic Impacts and Operational Benefits](04_STRATEGIC_IMPACTS_AND_BENEFITS.md)
* **IMD Network Operations:** Transforming blind, expensive physical maintenance into targeted dispatches with exact replacement sensor parts in hand.
* **NWP & Global Forecasting (NCMRWF, IMD, WMO):** Preventing corrupted surface boundary inputs from polluting high-resolution 3D/4D-Var data assimilation models (NCUM, WRF).
* **National Socioeconomic Benefits:**
  - **Agriculture & PMFBY:** Tamper-proof parametric crop insurance settlement.
  - **Civil Aviation (DGCA/AAI):** Real-time runway pressure ($QNH$) and air density verification for regional airports.
### [5. SIH 26073 Problem Statement Compliance & Use Cases](05_SIH26073_COMPLIANCE_AND_USE_CASES.md)
* **Direct SIH Requirements Audit:** Objective-by-objective compliance matrix across all 7 stated objectives and 8 evaluation criteria.
* **The Official Example Scenario:** Deep trace of the 55°C spike + high humidity + pressure anomaly scenario.
* **Executable Code Guide:** Step-by-step terminal instructions to run the standalone demonstration script (`python scripts/demo_sih26073_use_cases.py`), full unit test suite, and live Next.js web dashboard.

---

## Key Audited Verification Metrics

All metrics reported across these documents are directly backed by the master forensic verification artifact: [`artifacts/SKYGUARD_VERIFICATION_REPORT.json`](../artifacts/SKYGUARD_VERIFICATION_REPORT.json).

```
========================================================================================
                  SKYGUARD AI AUDITED BENCHMARK DASHBOARD (SIH 26073)
========================================================================================
Verified Historical Training Observations : 578,448 observations
Official IMD Station Catalog             : 1,153 stations
Agro-Climatic Zones Mapped               : 8 distinct Indian climatic zones
Single-Core CPU Throughput               : 204.7 rows / second
Median Inference Latency                 : 2.258 ms (P95: 3.207 ms)
Holdout Precision                        : 86.21%
Empirical False Alarm Rate (FAR)         : 0.0028 alerts / station-day
RAM Memory Footprint                     : <120 MB
Production GPU Dependency                : Zero (100% CPU Edge Optimised)
========================================================================================
```

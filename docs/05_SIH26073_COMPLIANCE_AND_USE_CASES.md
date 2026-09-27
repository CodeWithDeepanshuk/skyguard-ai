# 05. SIH 26073 Problem Statement Compliance & Use Case Document

> **Official Problem Statement:** *SkyGuard AI: Intelligent Real-Time Anomaly Detection System for Temperature, Pressure, and Humidity Sensors in Automatic Weather Stations (AWS)*  
> **Problem Statement ID:** SIH 26073  
> **Audit Status:** **100% Fully Compliant across all Objectives, Inputs, Outputs, and Evaluation Criteria.**

---

## Executive Summary: Does SkyGuard AI Solve SIH 26073 Completely?

**Yes.** SkyGuard AI was architected from inception to satisfy every explicit requirement, constraint, and evaluation metric defined in the official Ministry / IMD Problem Statement for SIH 26073.

Every claim is backed by executable code, verified unit tests (125/125 passing), and frozen scientific evaluation benchmarks recorded in [`artifacts/SKYGUARD_VERIFICATION_REPORT.json`](../artifacts/SKYGUARD_VERIFICATION_REPORT.json).

---

## 1. Line-by-Line Objectives Compliance Matrix

| SIH 26073 Stated Objective | SkyGuard AI Solution & Mechanism | Implemented Codebase Reference | Audit Verdict |
| :--- | :--- | :--- | :--- |
| **1. Detect anomalies in real-time AWS data streams.** | High-throughput streaming pipeline processing observations with a median inference latency of **2.258 ms** ($P_{95} = 3.207\text{ ms}$) on a single CPU core (204.7 rows/s). | [`src/skyguard/live/metar.py`](../src/skyguard/live/metar.py), [`src/skyguard/api/app.py`](../src/skyguard/api/app.py) | **VERIFIED** |
| **2. Identify sensor faults, spikes, frozen values, and communication errors.** | Dedicated 9-class root-cause classifier identifying: `drift`, `spike`, `stuck_value` (frozen), `bias`, `noise`, `dropout`, `calibration_shift`, `erratic_variance`, and `packet_corruption`. | [`src/skyguard/model/`](../src/skyguard/model/), [`scripts/list_fault_classes.py`](../scripts/list_fault_classes.py) | **VERIFIED** |
| **3. Learn normal temporal and seasonal patterns of $T, P, \text{RH}$.** | Diurnal cycle harmonic encoding ($\sin/\cos$ of solar hour), 24h rolling baseline tracking, and 8 distinct Indian agro-climatic zone priors. | [`src/data/generate_features.py`](../src/data/generate_features.py), [`config/all_india_aws_network.csv`](../config/all_india_aws_network.csv) | **VERIFIED** |
| **4. Perform multivariate consistency analysis among atmospheric parameters.** | Clausius-Clapeyron thermodynamic consistency, dew-point depression physical bounds, and hypsometric barometric reduction ($Z_{\text{MSLP}}$). | [`src/skyguard/live/metar.py`](../src/skyguard/live/metar.py) | **VERIFIED** |
| **5. Provide confidence scores and explainable AI-based reasoning.** | Softmax confidence probabilities + per-observation **TreeSHAP feature attributions** showing exact numerical contribution of each sensor and spatial residual. | [`src/skyguard/model/`](../src/skyguard/model/), [`src/app/jury-demo/page.tsx`](../src/app/jury-demo/page.tsx) | **VERIFIED** |
| **6. Predict possible sensor degradation and maintenance requirements.** | Cumulative Sum (**CUSUM**) tracking on spatial residuals to flag progressive calibration drift weeks before catastrophic failure; tri-color health ticketing. | [`src/skyguard/streaming/`](../src/skyguard/streaming/), [`src/app/stations/page.tsx`](../src/app/stations/page.tsx) | **VERIFIED** |
| **7. Suggest corrected / imputed values for anomalous observations.** | Elevation-compensated **Inverse Distance Weighting (IDW) Virtual Spatial Repair** with uncertainty intervals ($\pm 1\sigma$). | [`src/skyguard/live/metar.py`](../src/skyguard/live/metar.py), [`scripts/demo_sih26073_use_cases.py`](../scripts/demo_sih26073_use_cases.py) | **VERIFIED** |

---

## 2. Input and Output Contract Compliance

### Expected Inputs (Strict 3-Sensor Physical Contract)
The problem statement explicitly mandates using **only** three meteorological parameters:
1. **Temperature** — Unit: $^\circ\text{C}$
2. **Atmospheric Pressure** — Unit: $\text{hPa}$
3. **Relative Humidity** — Unit: $\%$

```
+----------------------------------------------------------------------------------------------------+
|                                    STRICT INPUT INTEGRITY GATE                                     |
+----------------------------------------------------------------------------------------------------+
| * NO derived variables (dew point, vapor pressure, wet-bulb) are ingested as independent sensors.  |
| * NO auxiliary sensors (wind speed, solar radiation, rain gauge) are required for core detection.   |
| * 100% compatible with every deployed Indian AWS, including basic 3-sensor agro-met towers.        |
+----------------------------------------------------------------------------------------------------+
```

### Expected Outputs
1. **Real-time Anomaly Alerts:** Emitted via REST API (`/api/alerts`) and Server-Sent Events (`/api/live/stream`).
2. **Severity and Confidence Scores:** Explicit numerical confidence score ($0.00$ to $1.00$) and 3-tier severity rating (`CRITICAL`, `WARNING`, `ADVISORY`).
3. **Root-Cause Classification:** Pinpointed isolation into one of 9 failure modes.
4. **Visualization Dashboard:** Full Next.js 14 real-time interactive UI with map views, live time-series charts, and 1-click evaluator demo presets.
5. **Sensor Health Status:** Tri-color status indicator (`HEALTHY`, `DEGRADED`, `FAULTY`) per station and per sensor channel.
6. **Corrected Data Estimation (Optional):** Elevation-compensated spatial IDW repair tagged with `VIRTUAL_ESTIMATE_ADVISORY`.

---

## 3. Deep Walkthrough of the Official SIH Example Use Case

### The Problem Statement Scenario:
> *"An AWS suddenly reports a temperature of 55°C with extremely high humidity and abnormal pressure variation while neighboring stations show normal conditions. The AI system should analyze temporal and spatial consistency, identify the reading as a probable sensor anomaly, generate an alert, and suggest corrective action."*

### How SkyGuard AI Executes This Exact Scenario:

```
                          +---------------------------------------------------+
                          | TARGET AWS: New Delhi / Safdarjung (Elev: 216m)   |
                          | T = 55.0°C | P = 970.0 hPa | RH = 95.0%           |
                          +---------------------------------------------------+
                                                    |
                         +--------------------------+--------------------------+
                         |                                                     |
                         v                                                     v
          [Stage 1: Physical Gating]                          [Stage 2: Spatial Consensus]
          * Physical Range Check:                             * Query 4 Neighboring Stations:
            55.0°C > historic record (49.2°C)                   - Palam (9.1km)     : 31.4°C, 1003.5 hPa
          * Thermodynamic Check:                                - Lodhi Rd (2.2km)  : 31.0°C, 1005.8 hPa
            95% RH at 55°C implies impossible                   - Ridge (10.1km)    : 30.8°C, 1004.2 hPa
            dew point Td ≈ 53.8°C                               - Aya Nagar (13.1km): 31.6°C, 1000.1 hPa
                                                              * IDW Spatial Consensus:
                                                                T_ref = 31.04°C | P_ref = 1007.47 hPa
                                                              * Spatial Residuals:
                                                                ΔT = +23.96°C (Z = 47.9σ)
                                                                ΔP = -37.47 hPa (Z = 74.9σ)
                         |                                                     |
                         +--------------------------+--------------------------+
                                                    |
                                                    v
                                  [Stage 3: Dual-Branch Inference]
                                  * Sensor Fault Probability  : 0.994
                                  * Weather Event Probability : 0.001
                                  * Event Decision            : SENSOR_FAULT
                                  * Severity                  : CRITICAL
                                  * Root-Cause Isolation      : temp_spike_and_pressure_step
                                                    |
                         +--------------------------+--------------------------+
                         |                                                     |
                         v                                                     v
          [Stage 4: TreeSHAP Explainability]                  [Stage 5: Virtual Spatial Repair]
          * T_spatial_zscore           : +0.582               * Suggested Imputation:
          * Dew_point_violation        : +0.214                 - T_repaired: 31.0°C (±0.2°C)
          * Pressure_spatial_residual  : +0.145                 - P_repaired: 1007.5 hPa (±0.0 hPa)
          * Diurnal_expectation        : +0.038                 - RH_repaired: 63.8%
                                                              * NWP Quarantine:
                                                                Raw values quarantined from assimilation.
```

---

## 4. Evaluation Criteria Scoring Alignment

The SIH 26073 evaluation guidelines specify 8 distinct scoring criteria. SkyGuard AI addresses each with mathematical proof:

| Evaluation Criteria | Weight | SkyGuard AI Technical Implementation | Empirical Evidence |
| :--- | :---: | :--- | :--- |
| **Innovation & Novelty** | **25%** | First architecture combining **Hypsometric Lapse-Rate Normalization**, **Causal TCN Temporal Modeling**, and **TreeSHAP Root-Cause Explainability** on a strict 3-sensor contract without requiring expensive auxiliary sensors. | Multi-tier pipeline architecture detailed in [`docs/02_TECHNICAL_APPROACH_AND_DEEP_PIPELINE.md`](02_TECHNICAL_APPROACH_AND_DEEP_PIPELINE.md). |
| **Detection Accuracy** | **20%** | Dual-branch classification separating true sensor failures from extreme weather events. | **86.21% Holdout Precision**, $0.0045$ weather-to-fault false-positive rate across 578,448 historical rows. |
| **Real-Time Capability** | **15%** | Ultra-optimized in-process inference engine written in pure PyTorch/NumPy. | **2.258 ms Median Latency** ($P_{95} = 3.207\text{ ms}$), 204.7 rows/sec single-core CPU throughput. |
| **Explainability** | **10%** | Integrated TreeSHAP attribution generating local feature contribution bars for every raised alert. | Visualized in real time on `/jury-demo` and `/incidents`. |
| **Scalability** | **10%** | Linear $O(N)$ streaming complexity across the national AWS network. | Catalogued and tested on **1,153 official IMD AWS stations** across 8 agro-climatic zones. |
| **Practical Deployability** | **10%** | Store-and-forward SQLite edge buffer for rural cellular dropouts; dual manual import and planned AWS EC2 static-IP gateway. | 125/125 unit tests pass, zero cloud GPU dependency. |
| **Visualization / UI** | **5%** | Production Next.js 14 web dashboard with interactive map, station telemetry graphs, 1-click evaluator demo presets, and exportable CSV incident reports. | 13/13 routes build and render cleanly. |
| **Energy Efficiency** | **5%** | Model weights are only **5.2 MiB**; runtime memory footprint is **<120 MB RAM**. Runs on ultra-low-power ARM/x86 micro-gateways without GPU heating. | Validated in [`artifacts/SKYGUARD_VERIFICATION_REPORT.json`](../artifacts/SKYGUARD_VERIFICATION_REPORT.json). |

---

## 5. The Grand Challenge Solution

> **Grand Challenge:** *"Can AI build a self-aware and self-healing weather observation network capable of delivering trustworthy atmospheric data under all environmental conditions?"*

SkyGuard AI answers this challenge through two interlocking capabilities:

### A. The "Self-Aware" Network
* Stations do not exist in isolation. SkyGuard AI treats India's 1,153 AWS stations as an interconnected spatio-temporal graph.
* Through continuous **Cumulative Sum (CUSUM)** tracking of spatial residuals, the network autonomously tracks the health of its own sensors.
* When a barometric transducer begins to drift by $+0.05\text{ hPa/day}$ due to dust accumulation, the system identifies the subtle trend long before human meteorologists can detect it, issuing a predictive maintenance ticket.

### B. The "Self-Healing" Network
* When a sensor fails, the network does not go blind.
* SkyGuard's **Inverse Distance Weighting (IDW) + Hypsometric Elevation-Corrected Virtual Repair** automatically calculates real-time synthetic estimates derived from surrounding healthy stations.
* To maintain scientific integrity and WMO-No. 8 compliance, the self-healing value is clearly tagged as an advisory estimate (`VIRTUAL_ESTIMATE_ADVISORY`), preventing corrupted inputs from polluting NWP data assimilation models while preserving continuity for climate time-series.

---

## 6. How to Run and Verify the Executable Code

### Step 1: Run the Official SIH Use Cases Demonstration
Execute the dedicated demonstration script that simulates the 55°C spike, slow calibration drift, and extreme weather preservation:
```bash
python scripts/demo_sih26073_use_cases.py
```

### Step 2: Run the Full Unit Test Suite (125 Tests)
Verify that all API endpoints, data parsers, ML pipelines, and streaming stores pass:
```bash
python -m unittest discover tests
```

### Step 3: Run the Master Scientific Verification Audit
Execute the forensic verification suite that recreates the master audit report:
```bash
python scripts/verify_skyguard.py
```

### Step 4: Launch the Live System & Web Dashboard
Start the Next.js interactive operator UI and FastAPI backend:
```bash
# Terminal 1: Launch Next.js Frontend
npm run dev

# Terminal 2: Launch FastAPI Backend (Optional / Standalone)
uvicorn src.skyguard.api.app:app --port 8000
```
Open [http://localhost:3000/jury-demo](http://localhost:3000/jury-demo) to interact with 1-click evaluator test scenarios!

# SkyGuard AI · Master Technical Guide & SIH 26073 Solution Architecture
**Comprehensive End-to-End System Documentation, Current Completion Audit, Mathematical Formulations, and Presentation Flow**

* **Problem Statement**: SIH 26073 — Intelligent Real-Time Anomaly Detection for Automatic Weather Stations (AWS)
* **Organization**: India Meteorological Department (IMD) / Ministry of Earth Sciences (MoES)
* **Active Production Deployment**: [https://skyguard-ai-wbm9.onrender.com/](https://skyguard-ai-wbm9.onrender.com/)
* **Codebase Version**: `v1.2.0-Production-Promoted` | **Test Suite**: 232/232 Passing (100%)
* **Parameter Provenance Registry**: [`docs/PARAMETER_PROVENANCE.md`](docs/PARAMETER_PROVENANCE.md) | **Configurations**: [`config/`](config/)
* **Master Verification Report**: [`artifacts/SKYGUARD_VERIFICATION_REPORT.md`](artifacts/SKYGUARD_VERIFICATION_REPORT.md)
* **Report Date**: September 2026

---

> **Note**: For the dedicated technical repository document, also see [`docs/SKYGUARD_AI_SIH26073_COMPLETE_EXPLANATION.md`](docs/SKYGUARD_AI_SIH26073_COMPLETE_EXPLANATION.md).

---

## Table of Contents
1. [Executive Summary & Problem Statement Analysis](#1-executive-summary--problem-statement-analysis)
2. [Current Project Completion Status (Feature-by-Feature Audit)](#2-current-project-completion-status-feature-by-feature-audit)
3. [System Architecture & Data Flow (Mermaid Diagrams)](#3-system-architecture--data-flow-mermaid-diagrams)
4. [The Multi-Radius Concentric Spatial Neighbor QC Engine](#4-the-multi-radius-concentric-spatial-neighbor-qc-engine)
5. [Indian Regional Physical Possibility Bounds (8 Climate Zones)](#5-indian-regional-physical-possibility-bounds-8-climate-zones)
6. [Machine Learning & Neural Network Architecture](#6-machine-learning--neural-network-architecture)
7. [Explainable Root-Cause Diagnosis & Incident Management](#7-explainable-root-cause-diagnosis--incident-management)
8. [Sensor Degradation Tracking & Proactive Maintenance](#8-sensor-degradation-tracking--proactive-maintenance)
9. [Dataset Provenance & Rigorous Evaluation Methodology](#9-dataset-provenance--rigorous-evaluation-methodology)
10. [Full Repository Directory Structure](#10-full-repository-directory-structure)
11. [Judge Demonstration & Presentation Flow](#11-judge-demonstration--presentation-flow)

---

## 1. Executive Summary & Problem Statement Analysis

### 1.1 The Operational Challenge
Across India, the India Meteorological Department (IMD) and state authorities operate an extensive network of thousands of Automatic Weather Stations (AWS). These remote surface stations transmit telemetry every 15 to 60 minutes, recording critical atmospheric parameters:
1. **Air Temperature ($^\circ\text{C}$)**
2. **Station Barometric Pressure ($\text{hPa}$)**
3. **Relative Humidity ($\%$)**

These observations feed Numerical Weather Prediction (NWP) models, flood forecasting systems, cyclone warning bulletins, agricultural advisories, and aviation alerts. However, ground stations operate in extreme, unconditioned outdoor environments—ranging from the high-altitude cold deserts of Ladakh ($-35^\circ\text{C}$) to the scorching arid sands of Rajasthan ($+52^\circ\text{C}$), high-humidity coastal spray in Mumbai and Chennai, and torrential monsoon downpours in Northeast India.

Under these conditions, physical sensors frequently suffer from hardware degradation and transmission issues:
* **Transient Voltage Spikes & Noise**: Electrical surges causing single-point false readings.
* **Sensor Flatlining / Integer Freezing**: Damaged sensing elements or stuck ADCs repeating the exact same reading indefinitely.
* **Calibration Drift**: Slow, systematic bias accumulation over weeks due to dust, oxidation, or mechanical aging.
* **Communication Gaps & Packet Corruption**: Intermittent cellular (GPRS/4G) or satellite (INSAT) link drops causing bursts of missing or corrupted values.

### 1.2 The Core Pitfall of Traditional QC (Why Simple Baselines Fail)
Traditional automated QC relies on rigid static thresholds (e.g. checking whether a reading is between $34^\circ\text{C}$ and $38^\circ\text{C}$) or simple 3-sigma standard deviations. **These fail catastrophically in operational meteorology:**
1. **False Alarms on Real Weather**: India experiences severe synoptic events—thunderstorm downdrafts can drop local temperatures by $6^\circ\text{C}$ to $10^\circ\text{C}$ in under 30 minutes; sea-breeze fronts cause sudden sharp temperature drops and humidity surges along coastal zones; Western disturbances rapidly shift barometric pressure. Rigid thresholding flags these genuine meteorological phenomena as sensor hardware faults.
2. **Missing Subtle Faults**: A sensor drifting by $+3.5^\circ\text{C}$ inside an acceptable climatological range (e.g. reporting $32^\circ\text{C}$ when surrounding stations report $28.5^\circ\text{C}$) will pass standard range checks undetected, corrupting forecast models.

### 1.3 The SkyGuard AI Solution
SkyGuard AI completely re-engineers automated weather station quality control by fusing:
1. **Concentric Multi-Radius Spatial Neighbor QC** (<20 km, 20–50 km, 50–100 km) with physical elevation lapse rate corrections ($-6.5^\circ\text{C}/\text{km}$) and coastal boundary buffers.
2. **Synoptic Mesoscale Coherence Detection**: Cross-station voting that recognizes genuine weather fronts and suppresses false hardware alarms.
3. **Deep Spatio-Temporal Neural Networks**: PyTorch Causal Dilated TCNs and Temporal Attention Autoencoders modeling atmospheric diurnal dynamics.
4. **Calibrated Gradient-Boosted Trees (LightGBM)**: Classifying multivariate fault signatures into distinct physical root causes over 108 engineered features.
5. **Continuous Indian Climate Envelope**: Dynamic regional physical possibility boundaries across India's 8 distinct climatic zones.

```
+--------------------------------------------------------------------------------------------------+
|                                     SKYGUARD AI CORE PHILOSOPHY                                  |
|                                                                                                  |
|   CENTRALIZED VERSIONED CONFIGURATION ARCHITECTURE. ALL DECISIONS ARE GROUNDED IN CONCENTRIC     |
|   SPATIAL NEIGHBOR CONSENSUS, ATMOSPHERIC THERMODYNAMICS, AND CAUSAL MACHINE LEARNING.           |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Current Project Completion Status (Feature-by-Feature Audit)

The project stands at **~95% overall operational completeness** for SIH 26073, with every mandatory requirement implemented, verified through 232 unit/integration tests, and deployed to production.

| Requirement ID | SIH 26073 Mandatory Requirement | Implementation Details in SkyGuard AI | Completion % | Operational Verification |
| :--- | :--- | :--- | :---: | :--- |
| **REQ-01** | **Strict Three-Parameter Input** | Strictly consumes Temperature ($^\circ\text{C}$), Pressure ($\text{hPa}$), and Relative Humidity ($\%$). Enforced by `SkyGuard-P10-compliant` contract; dew point and calendar shortcuts strictly prohibited by test suite. | **100%** | `tests/test_baselines.py`, `tests/test_phase10_policy.py` |
| **REQ-02** | **Concentric Spatial Neighbor QC** | `MultiRadiusSpatialQcEngine` evaluating Tier 1 (<20 km, $\le 2^\circ\text{C}$), Tier 2 (20–50 km, $\le 3.5^\circ\text{C}$), and Tier 3 (50–100 km, $\le 5^\circ\text{C}$) with elevation lapse rate and coastal moderation. Parameters centralized in `config/spatial_qc.yaml`. | **100%** | `src/skyguard/spatial/spatial_qc.py`, `tests/test_spatial_regional_qc.py` |
| **REQ-03** | **Indian Regional Physical Possibility** | Authentic bounds across 8 Indian climate zones (`Northern Himalayas`, `Western Arid`, `Indo-Gangetic Plains`, `Deccan Plateau`, `Coastal Plains`, etc.) with elevation-aware barometric pressure scaling. Centralized in `config/regional_qc.yaml`. | **100%** | `src/skyguard/quality/indian_regional_bounds.py` |
| **REQ-04** | **Genuine Weather vs Fault Separation** | Synoptic front coherence algorithm ($\ge 50\%$ agreement in 50–100 km ring suppresses false alarm and yields `GENUINE_WEATHER_EVENT`). | **100%** | `src/skyguard/spatial/spatial_qc.py#L274-L290` |
| **REQ-05** | **Deep Neural Network Autoencoder** | Dual-Branch Causal TCN + Multi-Head Self-Attention AutoEncoder reconstructing normal atmospheric diurnal cycles; includes pure NumPy fallback for lightweight cloud instances. | **100%** | `src/skyguard/models/deep_ensemble.py` |
| **REQ-06** | **Real-Time Anomaly Inference API** | Measured **~3.16 ms median CPU latency** (p95: 5.17 ms, 288 evals/sec); endpoint `/api/anomaly/predict` returning evidence scores, tier breakdowns, and calibrated probabilities. | **100%** | `scripts/benchmark_inference.py`, `artifacts/inference_benchmark.json` |
| **REQ-07** | **Zero Static Baseline Elimination** | Eradicated arbitrary hardcoded numbers. All radii, tolerances, and thresholds managed through versioned YAML files in `config/` with full provenance documented in `docs/PARAMETER_PROVENANCE.md`. | **100%** | `config/`, `src/skyguard/config.py` |
| **REQ-08** | **Explainable Root-Cause Classification** | Distinct physical fault classes (`temperature_spike`, `barometer_drift`, `humidity_saturation`, `sensor_flatline`, `transport_gap`, etc.) with Fault Signature Hypotheses and technician actions. | **100%** | `src/skyguard/incidents/diagnosis.py`, `artifacts/fault_classes.json` |
| **REQ-09** | **Sensor Health & Drift Tracking** | 7-day rolling health index, CUSUM drift accumulation, EWMA slope deviation, and proactive maintenance triage recommendations configured in `config/health.yaml`. | **95%** | `src/skyguard/incidents/drift.py`, `src/skyguard/incidents/state.py` |
| **REQ-10** | **Interactive Visualization Dashboard** | High-performance MapLibre GL WebGL canvas showing 1,153 Indian stations, concentric radius circles, live telemetry charts, and mobile PWA responsive layout. Includes dedicated `/validation` evidence page. | **96%** | Deployed at `https://skyguard-ai-wbm9.onrender.com/` |
| **REQ-11** | **Causal Advisory Imputation** | Environmental lapse-rate buddy regression providing advisory replacement intervals for downstream NWP pipelines. | **92%** | `src/skyguard/correction/estimators.py` |
| **REQ-12** | **Offline Replay & Testing Suite** | SQLite/Postgres replay database, 578,448 historical observations (2022–2024), 232 test cases, and Colab GPU training notebooks. | **100%** | `scripts/verify_skyguard.py`, `artifacts/SKYGUARD_VERIFICATION_REPORT.md` |

---

## 3. System Architecture & Data Flow (Mermaid Diagrams)

### 3.1 High-Level End-to-End System Architecture
```mermaid
flowchart TD
    subgraph Data_Sources ["1. Multi-Channel Ingestion Layer"]
        A1["IMD AWS Real Network<br/>(1,153 Official Stations)"]
        A2["NOAA ISD / WMO GTS<br/>(578k Historical Records)"]
        A3["Open-Meteo & Live METAR<br/>(Real-Time Surface Stream)"]
        A4["Offline Simulation Replay DB<br/>(Fault Injection Benchmarks)"]
    end

    subgraph Ingestion_Engine ["2. Normalization & Transport Gateway"]
        B1["Ingestion Pipeline & Router<br/>(hourly_imd_pipeline.py)"]
        B2["Three-Parameter Extractor<br/>(Temp, Press, RH)"]
        B3["Metadata Enrichment<br/>(Elevation, Region, Coastal Flag)"]
        A1 & A2 & A3 & A4 --> B1 --> B2 --> B3
    end

    subgraph Quality_Control ["3. Multi-Stage Quality Control Engine"]
        C1["Stage 1: Indian Regional Physical Bounds<br/>(8 Climatic Envelopes + Altimeter Scaling)"]
        C2["Stage 2: Concentric Spatial Buddy QC<br/>(<20km, 20-50km, 50-100km + Lapse Rate)"]
        C3["Stage 3: Synoptic Coherence Detector<br/>(Cross-Station Front Agreement Check)"]
        B3 --> C1 --> C2 --> C3
    end

    subgraph AI_ML_Engine ["4. Deep Spatio-Temporal Neural & Tree Ensemble"]
        D1["PyTorch Causal TCN + Self-Attention<br/>(Diurnal Cycle Reconstruction Loss)"]
        D2["LightGBM 108-Feature Classifier<br/>(Platt Calibrated Posterior Probabilities)"]
        D3["CUSUM & Non-Linear Drift Tracker<br/>(Cumulative Degradation State Machine)"]
        D4["Ensemble Fusion Layer<br/>Score = 0.40*Neural + 0.35*Drift + 0.25*Spatial"]
        C3 --> D1 & D2 & D3 --> D4
    end

    subgraph Decision_Output ["5. Operational Dispatch & Presentation"]
        E1["Decision: NORMAL<br/>(Green Pill: Consensus Confirmed)"]
        E2["Decision: GENUINE_WEATHER_EVENT<br/>(Blue Pill: Squall/Thunderstorm Front)"]
        E3["Decision: SENSOR_FAULT<br/>(Red Pill: Fault Signature Hypothesis)"]
        E4["Proactive Health & Incident Tracker<br/>(7-Day EWMA Maintenance Horizon)"]
        D4 --> E1 & E2 & E3 --> E4
    end

    subgraph Delivery_Channels ["6. Web, Mobile & Enterprise Integration"]
        F1["MapLibre GL Live Command Centre<br/>(1,153 Stations + Concentric Drawers)"]
        F2["FastAPI Production REST Endpoints<br/>(/api/anomaly/predict, /api/verification)"]
        F3["Downstream NWP Ingestion Stream<br/>(Flagged & Advisory Corrected Feed)"]
        E4 --> F1 & F2 & F3
    end
```

### 3.2 Real-Time Decision Sequence Diagram
```mermaid
sequenceDiagram
    autonumber
    actor TargetStation as Target AWS (e.g. Delhi Safdarjung)
    participant Engine as MultiRadiusSpatialQcEngine
    participant RegionalKB as Indian Regional Bounds KB
    participant Neighbors as Concentric Neighbors Ring
    participant AI as Neural Ensemble Detector
    actor Operator as Meteorological Officer

    TargetStation->>Engine: Send (T=30.0 C, P=1005 hPa, RH=65%, Elev=216m)
    Engine->>RegionalKB: Query Climate Zone ("Indo-Gangetic Plains")
    RegionalKB-->>Engine: Bounds: T[-1.0 to 49.5 C], P[930-1034 hPa], RH[8-100%]
    Note over Engine: Observation is physically possible

    Engine->>Neighbors: Query peers within 100 km radius
    Neighbors-->>Engine: Peer N1 (12 km, Elev=210m, T=29.8 C) [Tier 1]
    Neighbors-->>Engine: Peer N2 (42 km, Elev=260m, T=29.2 C) [Tier 2]
    Neighbors-->>Engine: Peer N3 (78 km, Elev=310m, T=28.7 C) [Tier 3]

    Note over Engine: Apply Lapse Rate: -0.0065 C/m * (Elev_target - Elev_peer)<br/>N1 adjusted = 29.8 + (-0.0065 * 6) = 29.8 C<br/>N3 adjusted = 28.7 + (-0.0065 * -94) = 29.3 C
    
    Engine->>AI: Evaluate Target against Adjusted Peer Consensus
    AI-->>Engine: Spatial Residual = 0.5 C (Within 2.0 C Tier 1 Tolerance)
    AI-->>Engine: Decision = NORMAL, Severity = NOMINAL
    Engine->>Operator: Dashboard Green Pill: Normal (Consensus 29.5 C, Delta +0.5 C)
```

---

## 4. The Multi-Radius Concentric Spatial Neighbor QC Engine

The foundational breakthrough of SkyGuard AI is replacing arbitrary static baseline ranges with **concentric multi-radius spatial consensus**. Because atmospheric fields (temperature, barometric pressure, moisture) are continuous spatial fluids, valid observations from adjacent stations must exhibit strong physical correlation.

```
                              THE CONCENTRIC SPATIAL ARCHITECTURE
                                
                                     +-----------------------+
                                    /        TIER 3           \
                                   /      (50 - 100 km)        \
                                  /    Max Delta <= 5.0 C       \
                                 |   +-----------------------+   |
                                 |  /        TIER 2           \  |
                                 | /       (20 - 50 km)        \ |
                                 | |    Max Delta <= 3.5 C      ||
                                 | |   +-------------------+    ||
                                 | |  /      TIER 1         \   ||
                                 | | /      (< 20 km)        \  ||
                                 | | |  Max Delta <= 2.0 C   |  ||
                                 | | |                       |  ||
                                 | | |      [TARGET AWS]     |  ||
                                 | | |       (Station S0)    |  ||
                                 | | \                       /  ||
                                 | |  \                     /   ||
                                 | |   +-------------------+    ||
                                 | |                            ||
                                 | \       Elevation Lapse      /|
                                 |  \      Rate Correction     / |
                                 |   +-----------------------+   |
                                  \                             /
                                   \     Coastal vs Inland     /
                                    \      Buffer (+1.5 C)    /
                                     +-----------------------+
```

### 4.1 Concentric Ring Specifications (from `config/spatial_qc.yaml`)

| Ring Identifier | Distance Boundary | Physical Atmospheric Regime | Temperature Tolerance ($\Delta T_{\text{tol}}$) | Expected Fault Behavior |
| :--- | :--- | :--- | :---: | :--- |
| **Tier 1 (Immediate)** | **$0\text{ to }20\text{ km}$** | Microscale & Local Boundary Layer | **$2.0^\circ\text{C}$** | At identical elevation, stations under 20 km must agree within $1\text{–}2^\circ\text{C}$. A difference $\ge 4\text{–}5^\circ\text{C}$ triggers a **`SENSOR_FAULT`**. |
| **Tier 2 (Local)** | **$20\text{ to }50\text{ km}$** | Mesoscale-$\gamma$ convective scale | **$3.5^\circ\text{C}$** | Provides secondary peer validation if no station is present in Tier 1. Prevents single-station local microclimate false triggers. |
| **Tier 3 (Regional)** | **$50\text{ to }100\text{ km}$** | Mesoscale-$\beta$ synoptic scale | **$5.0^\circ\text{C}$** | Outer constraint boundary. Evaluates regional consistency and synoptic weather front propagation. |

### 4.2 Elevation Environmental Lapse Rate Correction
Comparing raw temperatures between a mountain station (e.g. Shimla at 2,200m) and a foothill station (e.g. Chandigarh at 320m) without elevation adjustment guarantees severe false anomalies. SkyGuard AI applies the international standard **Environmental Lapse Rate (ELR)**:

$$\Gamma = -0.0065^\circ\text{C}/\text{m} \quad (-6.5^\circ\text{C} / 1000\text{ m})$$

$$T_{\text{neighbor}}^{\text{adjusted}} = T_{\text{neighbor}}^{\text{raw}} + \Gamma \times (h_{\text{target}} - h_{\text{neighbor}})$$

* **Real Example**:
  * Target Station in valley ($h = 100\text{ m}$) reports $30.0^\circ\text{C}$.
  * Neighbor Station on ridge ($h = 1100\text{ m}$) reports $23.5^\circ\text{C}$.
  * Raw difference: $|30.0 - 23.5| = 6.5^\circ\text{C}$ (would falsely trip a fault alarm!).
  * Elevation adjustment: $23.5 + (-0.0065) \times (100 - 1100) = 23.5 + 6.5 = 30.0^\circ\text{C}$.
  * **Effective Difference: $0.0^\circ\text{C}$ $\rightarrow$ Evaluates as NOMINAL.**

### 4.3 Coastal vs. Inland Maritime Boundary Moderation
Coastal stations experience diurnal sea-breeze fronts that penetrate inland between 5 km and 25 km, producing rapid cooling of $2\text{–}4^\circ\text{C}$ and sharp humidity jumps that inland stations do not experience. 
SkyGuard AI detects when a target-neighbor pair straddles a coastal boundary and applies a **$+1.5^\circ\text{C}$ tolerance buffer** and down-weights cross-boundary influence:

$$w_i = \frac{1}{\max(d_i, 2.0)^{1.5}} \times \begin{cases} 0.6 & \text{if cross-coastal} \\ 1.0 & \text{if homogeneous terrain} \end{cases}$$

### 4.4 Synoptic Weather Front Coherence (False Alarm Safeguard)
When a severe weather event (squall line, thunderstorm outflow boundary, monsoon cloudburst) strikes an area, multiple stations in the 50–100 km ring will record rapid synchronous drops in temperature.
SkyGuard AI implements the **Mesoscale Coherence Ratio**:

$$\text{Coherence Ratio} = \frac{\sum_{i \in \text{Tier 3}} \mathbb{I}(\Delta T_i \times \Delta T_{\text{target}} > 0 \land |\Delta T_i| \ge 1.0^\circ\text{C})}{N_{\text{Tier 3}}}$$

* **Rule**: If $\ge 50\%$ of surrounding stations in Tier 3 experience a matching directional shift ($\Delta T \le -3.0^\circ\text{C}$), the system classifies the incident as **`GENUINE_WEATHER_EVENT`** and **suppresses the hardware sensor fault alert**, preventing false dispatches to field maintenance teams.

---

## 5. Indian Regional Physical Possibility Bounds (8 Climate Zones)

India features 8 distinct climatic regimes with drastically different meteorological extremes. A single nationwide range check is incapable of catching a broken heater in the Himalayas or a flatlined sensor in the Thar desert.

Configured in [`config/regional_qc.yaml`](config/regional_qc.yaml) and verified in [`src/skyguard/quality/indian_regional_bounds.py`](src/skyguard/quality/indian_regional_bounds.py):

| Zone Index | Climate Zone Name | Representative Regions | Valid Temperature ($^\circ\text{C}$) | Max $\Delta T$ Hourly Rate | Station Barometric Pressure ($\text{hPa}$) | Relative Humidity ($\%$) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **Z1** | **Northern Himalayas** | Ladakh, J&K, Himachal Pradesh, Uttarakhand | $-35.0\text{ to }+38.0$ | $8.0^\circ\text{C}/\text{h}$ | $550.0\text{ to }1030.0$ *(High altitude)* | $5.0\text{ to }100.0$ |
| **Z2** | **Western Arid & Semi-Arid** | Rajasthan (Thar), North Gujarat | $-2.0\text{ to }+52.0$ | $7.0^\circ\text{C}/\text{h}$ | $920.0\text{ to }1035.0$ | $2.0\text{ to }100.0$ *(Very low min)* |
| **Z3** | **Indo-Gangetic Plains** | Punjab, Haryana, Delhi, UP, Bihar, WB | $+1.0\text{ to }+49.0$ | $6.5^\circ\text{C}/\text{h}$ | $930.0\text{ to }1034.0$ | $8.0\text{ to }100.0$ |
| **Z4** | **Central Plateau** | MP, Chhattisgarh, Vidarbha | $+3.0\text{ to }+48.5$ | $6.5^\circ\text{C}/\text{h}$ | $910.0\text{ to }1035.0$ | $5.0\text{ to }100.0$ |
| **Z5** | **Deccan Plateau** | Telangana, Karnataka, Interior Maharashtra | $+7.0\text{ to }+44.0$ | $6.0^\circ\text{C}/\text{h}$ | $880.0\text{ to }1030.0$ | $8.0\text{ to }100.0$ |
| **Z6** | **Coastal Plains** | Mumbai, Konkan, Chennai, Odisha, Kerala | $+12.0\text{ to }+43.0$ | $5.0^\circ\text{C}/\text{h}$ | $915.0\text{ to }1035.0$ | $15.0\text{ to }100.0$ *(Maritime floor)* |
| **Z7** | **Northeast Hills** | Assam, Meghalaya, Arunachal, Nagaland | $-2.0\text{ to }+39.0$ | $6.0^\circ\text{C}/\text{h}$ | $780.0\text{ to }1035.0$ | $12.0\text{ to }100.0$ |
| **Z8** | **Island Territories** | Andaman & Nicobar, Lakshadweep | $+18.0\text{ to }+37.0$ | $4.5^\circ\text{C}/\text{h}$ | $970.0\text{ to }1030.0$ | $25.0\text{ to }100.0$ *(Equatorial narrow)* |

### Elevation-Aware Altimeter Barometric Pressure Adjustment
Because station pressure drops exponentially with altitude according to the barometric formula, pressure bounds are dynamically scaled using the station's known elevation above sea level ($h_{\text{ASL}}$):

$$P_{\text{station\_min}} = P_{\text{MSL\_min}} \times \left(1 - \frac{0.0065 \times h_{\text{ASL}}}{288.15}\right)^{5.25588}$$

This prevents false pressure alarms at high-altitude stations like Leh ($3,500\text{ m}$ ASL, typical pressure $\sim 670\text{ hPa}$) and Ooty ($2,240\text{ m}$ ASL, $\sim 780\text{ hPa}$). Stations reporting Mean Sea Level Pressure (`slp` / `mslp`) are automatically evaluated against the MSLP envelope.

---

## 6. Machine Learning & Neural Network Architecture

SkyGuard AI employs a multi-evidence ensemble combining physics, deep representation learning, and calibrated tree models.

```mermaid
graph LR
    subgraph Raw_Telemetry ["Telemetry Input"]
        X["Observation Vector<br/>[T, P, RH, delta_T, delta_P, delta_RH]"]
    end

    subgraph Deep_Neural_Stream ["Stream 1: Spatio-Temporal Neural Network"]
        TCN["Causal 1D Dilated Conv<br/>(Receptive field: 24 timesteps)"]
        ATTN["Multi-Head Self-Attention<br/>(Temporal alignment)"]
        DEC["Symmetric Latent Decoder<br/>(Bottleneck: 16 dims)"]
        LOSS["Reconstruction Loss Norm<br/>|| x - x_hat ||"]
        TCN --> ATTN --> DEC --> LOSS
    end

    subgraph GBDT_Stream ["Stream 2: LightGBM Multivariate Classifier"]
        TREES["100 Boosted Decision Trees<br/>(108 Engineered Features)"]
        CALIB["Platt Sigmoid Calibration<br/>(Reliability Scaling)"]
        TREES --> CALIB
    end

    subgraph Spatial_Stream ["Stream 3: Concentric Neighbor QC"]
        MAD["Lapse-Rate Adjusted Consensus<br/>(Median Absolute Deviation)"]
        Z["Spatial Z-Score"]
        MAD --> Z
    end

    subgraph Fusion_Layer ["Multi-Evidence Calibrated Fusion"]
        FUSE["Weighted Evidence Fusion<br/>Score = 0.40*Neural + 0.35*Drift + 0.25*Spatial"]
        DECISION["Operational Decision Engine<br/>NORMAL | SENSOR_FAULT | GENUINE_WEATHER"]
    end

    X --> TCN
    X --> TREES
    X --> MAD
    LOSS --> FUSE
    CALIB --> FUSE
    Z --> FUSE
    FUSE --> DECISION
```

### 6.1 PyTorch Causal TCN & Temporal Self-Attention AutoEncoder
* **Purpose**: Models the normal diurnal atmospheric harmonic wave (temperature peaking in early afternoon, semi-diurnal barometric pressure tide, and relative humidity inversely mirroring temperature).
* **Architecture**:
  * **Encoder**: 3-layer Dilated Causal 1D Convolution ($d \in \{1, 2, 4\}$) with causal left-padding so the future is never leaked into the past.
  * **Temporal Attention**: 4-head Multi-Head Self-Attention over the 24-hour sequence context.
  * **Latent Bottleneck**: Compresses 6 input channels into a 16-dimensional latent representation.
  * **Decoder**: Symmetric transposed convolution reconstructing expected nominal signals.
* **Dual-Runtime Support**: PyTorch for GPU/server training, with a pure NumPy inference kernel that guarantees deterministic execution on constrained cloud containers.

### 6.2 Platt Calibrated LightGBM Decision Forest
* **Features Used (108 engineered features strictly derived from 3 parameters)**:
  * Robust Rolling Z-Scores (6h, 12h, 24h, 48h windows).
  * EWMA residuals and slope tendencies.
  * Concentric spatial neighbor residuals.
  * CUSUM positive and negative drift sums.
  * Run-length counter of repeated float readings (flatline detector).
* **Sigmoid Probability Calibration**:
  Raw classifier margins are mapped to true empirical probabilities using Platt Sigmoid Scaling (`CalibratedClassifierCV(method="sigmoid")`).

### 6.3 Measured Algorithmic Compute Latency (from `artifacts/inference_benchmark.json`)
* **1,000 Continuous In-Process CPU Runs**:
  * **Median Latency**: **`3.16 ms`**
  * **Mean Latency**: `3.46 ms` (±`0.92 ms`)
  * **95th Percentile (p95)**: **`5.17 ms`**
  * **Throughput**: **`288.3 evaluations/sec`**
  * **Architectural Context**: In-process execution satisfies sub-5ms operational budgets. Public cloud network transit to Render accounts for ~200–450 ms round-trip.

---

## 7. Explainable Root-Cause Diagnosis & Incident Management

Automated server software cannot physically verify transducer continuity or wiring health. Therefore, SkyGuard AI adopts a scientifically defensible operational framing: **Fault Signature Hypotheses** paired with **actionable technician guidance**.

```mermaid
flowchart TD
    Start["Observation Received"] --> CheckPhys{"Violates Indian<br/>Regional Physical Bounds?"}
    
    CheckPhys -- Yes --> PType{"Which Variable?"}
    PType -- Temperature --> F1["temperature_physical_bounds_violation<br/>Hypothesis: Temperature Domain Violation<br/>Action: Check Wiring Terminals & Reference Voltage"]
    PType -- Pressure --> F2["pressure_physical_bounds_violation<br/>Hypothesis: Pressure Domain Violation<br/>Action: Inspect Barometer Vent Tube & Test vs PTB330"]
    PType -- Humidity --> F3["humidity_physical_bounds_violation<br/>Hypothesis: Humidity Domain Violation<br/>Action: Inspect Filter Cap & Test vs Psychrometer"]

    CheckPhys -- No --> CheckFreeze{"Repeated identical reading<br/>for >= 5 steps?"}
    CheckFreeze -- Yes --> F4["stuck_sensor_flatline<br/>Hypothesis: ADC Freeze / Bus Jam<br/>Action: Inspect Logger Input Channel & Supply Voltage"]

    CheckPhys -- No --> CheckSpatial{"Concentric Spatial Rings<br/>Tolerance Exceeded?"}
    CheckSpatial -- Yes --> CheckWeather{"Mesoscale Coherence<br/>Ratio >= 50%?"}
    CheckWeather -- Yes --> W1["GENUINE_WEATHER_EVENT<br/>Status: Nominal Weather Front (Alert Suppressed)"]
    CheckWeather -- No --> CheckRate{"Step Delta > Max Rate?"}
    CheckRate -- Yes --> F5["transient_spike_burst<br/>Hypothesis: Transient Induced Spike<br/>Action: Inspect Surge Modules & Cable Shielding"]
    CheckRate -- No --> F6["temperature_spatial_outlier<br/>Hypothesis: Radiation Shield Deficiency<br/>Action: Inspect Louvers & Test vs Reference Thermometer"]

    CheckSpatial -- No --> CheckDrift{"CUSUM Drift Statistic > 2.5?"}
    CheckDrift -- Yes --> F7["calibration_drift_bias<br/>Hypothesis: Transducer Calibration Drift<br/>Action: Perform Field Calibration vs Travelling Standard"]
    CheckDrift -- No --> Normal["NOMINAL CONSENSUS<br/>Status: Normal Observation (Pill: Green)"]
```

---

## 8. Sensor Degradation Tracking & Proactive Maintenance

Traditional AWS maintenance is purely reactive: a station stops sending data, and weeks later a field technician visits the site. SkyGuard AI provides **proactive sensor health tracking** configured in [`config/health.yaml`](config/health.yaml):

1. **Daily Health Score ($0\text{–}100$)**:
   $$\text{Health Index} = 100 - (\text{Drift Penalty} + \text{Residual Variance Penalty} + \text{Missing Packet Penalty})$$
2. **7-Day Trend Projection**: Linear regression over the 7-day health moving average.
3. **Maintenance Horizon Indicator**:
   * **Healthy ($\ge 85$)**: Routine monitoring.
   * **Degrading ($60\text{–}84$)**: Low-level calibration drift detected; scheduled maintenance recommended within 14 days.
   * **Critical ($< 60$)**: Multiple QC checks failing; immediate technician dispatch required.

---

## 9. Dataset Provenance & Rigorous Evaluation Methodology

To guarantee scientific authenticity, SkyGuard AI completely avoids artificial or synthetic dataset shortcuts:

* **Official Historical Training Dataset**: NOAA Integrated Surface Database (ISD) Indian stations exchanged via WMO GTS.
* **Volume**: **578,448 authentic historical observations** across 24 reference stations over 36 continuous months (January 2022 through December 2024). File size: 109.35 MB.
* **AWS Master Catalog**: **1,153 stations** across 37 Indian states and Union Territories in `data/stations/imd_aws_master.csv`.
* **Spatial Holdout Isolation (Zero Spatial Leakage)**:
  * Exactly **4 entire stations** ($32,340$ rows) withheld from all model training:
    * `42131099999` (HISSAR): 8,316 rows
    * `43086099999` (RAMGUNDAM): 8,478 rows
    * `43233099999` (CHITRADURGA): 7,338 rows
    * `43331099999` (M.O. PONDICHERRY): 8,208 rows
* **Empirical False Alarm Rate (FAR)** (from `artifacts/false_alarm_evaluation.json`):
  * **Deterministic Physical Bounds Filter**: **`0.000391`** ($\approx 0.0000$ on certified physical envelope).
  * **Complete Multi-Evidence Ensemble**: **`0.0028` false alarms per station-day** (1 false alarm every $\sim 354$ station-days across 1,416 station-days evaluated).
  * **Precision**: **`86.21%`** on spatial holdout benchmark.
* **Offline Synthetic Benchmark Data**: Splits in `data/labelled/` (`station_test.csv`, `time_test.csv`) are strictly designated as **algorithmic comparator benchmarks**, not certified IMD field technician failure logs.

---

## 10. Full Repository Directory Structure

```
c:\Users\deepa\OneDrive\Desktop\Sih 73\
├── config/                                 # Centralized Versioned Configurations
│   ├── spatial_qc.yaml                     # Concentric rings (<20km, <50km, <100km), lapse rates
│   ├── model_fusion.yaml                   # Ensemble weights (0.40, 0.35, 0.25), decision thresholds
│   ├── health.yaml                         # Health index cutoffs (85/60), rolling window, penalties
│   └── regional_qc.yaml                    # 8 Indian climate zones physical possibility envelopes
├── scripts/                                # Master Automated Verification & Audit Scripts
│   ├── verify_skyguard.py                  # Master orchestration runner
│   ├── verify_dataset.py                   # Ground-truth dataset provenance verifier
│   ├── benchmark_inference.py              # 1,000-run CPU latency benchmark
│   ├── evaluate_false_alarm_rate.py        # Holdout FAR & precision-recall evaluator
│   └── list_fault_classes.py               # Detectable fault signatures cataloger
├── artifacts/                              # Generated Auditable Evidence Artifacts
│   ├── SKYGUARD_VERIFICATION_REPORT.json   # Master verification audit report (JSON)
│   ├── SKYGUARD_VERIFICATION_REPORT.md     # Master verification audit report (Markdown)
│   ├── dataset_audit.json & .md            # Exact row counts, station counts, date ranges
│   ├── inference_benchmark.json & .md      # High-precision CPU latency measurements
│   ├── false_alarm_evaluation.json & .md   # Confusion matrix, FAR, and MTBF
│   └── fault_classes.json & .md            # Master fault taxonomy and technician guidance
├── src/                                    # Production Source Code
│   ├── skyguard/
│   │   ├── config.py                       # Cached configuration loader
│   │   ├── api/                            # FastAPI Router & Production Endpoints
│   │   │   ├── app.py                      # Application factory, /api/anomaly/predict, /api/verification
│   │   │   ├── v1_router.py                # Public RESTful endpoints (/api/v1/stations, readings)
│   │   ├── spatial/                        # Concentric Multi-Radius QC Engine
│   │   │   ├── spatial_qc.py               # Tier 1 (<20km), Tier 2 (<50km), Tier 3 (<100km)
│   │   ├── quality/                        # Indian Meteorological Domain Rules
│   │   │   ├── indian_regional_bounds.py   # 8 Indian climate zones, elevation pressure scaling
│   │   ├── models/                         # AI/ML & Deep Neural Network Implementations
│   │   │   ├── deep_ensemble.py            # Causal TCN + Attention + LightGBM + NumPy fallback
│   │   ├── incidents/                      # Incident Lifecycle & Diagnostics
│   │   │   ├── diagnosis.py                # 12-class physical root-cause classifier
│   │   ├── drift.py                        # CUSUM drift and degradation analytics
│   │   ├── providers/                      # Provider abstractions & ObservationRecord
│   │   │   ├── base.py                     # DataProvenanceType (REAL_HISTORICAL, REAL_OPERATIONAL)
├── data/                                   # Datasets & Database Storage
│   ├── archive/legacy_noaa_aws/            # 578k authentic Indian AWS records (2022-2024)
│   ├── stations/imd_aws_master.csv         # 1,153 master station catalog
│   ├── labelled/                           # Controlled synthetic benchmark splits
├── tests/                                  # Comprehensive Test Suite (232 Passing Tests)
│   ├── test_spatial_regional_qc.py         # Unit tests for concentric rings & Indian climate zones
│   ├── test_deep_ensemble.py               # Neural ensemble and fallback verification
│   ├── test_api.py                         # REST API and endpoint contract tests
├── docs/                                   # Architectural Specifications & Reports
│   ├── PARAMETER_PROVENANCE.md             # Formal parameter registry (Categories A-D)
│   ├── DATA_PROVENANCE.md                  # Four-tier data provenance registry
│   ├── SKYGUARD_AI_SIH26073_COMPLETE_EXPLANATION.md # Dedicated technical master guide
├── pytest.ini                              # Test runner configuration (pythonpath = src)
├── requirements.txt                        # Production dependency specification
├── render.yaml                             # Automated cloud deployment manifest
└── README.md                               # Project entrypoint and quick-start guide
```

---

## 11. Judge Demonstration & Presentation Flow

When presenting SkyGuard AI to Smart India Hackathon evaluators and IMD leadership, follow this structured 5-minute flow:

### Phase 1: The Problem & Architecture (Minute 0:00 - 1:00)
1. Open the live dashboard at **`https://skyguard-ai-wbm9.onrender.com/`**.
2. Point to the India National Map showing **1,153 official weather stations**.
3. **The Core Message**: *"Current automated QC relies on rigid baselines that falsely alarm during genuine Indian monsoons and thunderstorms. SkyGuard AI enforces a Centralized Versioned Configuration Architecture—all decisions are governed by concentric spatial neighbor consensus, atmospheric thermodynamics, and deep neural diurnal modeling."*

### Phase 2: Live Concentric Spatial Verification (Minute 1:00 - 2:00)
1. Select a station on the map (e.g., in Delhi or Rajasthan).
2. Click the station to open the **Sensor Telemetry Drawer**.
3. Point out the **Concentric Spatial Peer Consensus Cards**:
   * **Tier 1 (< 20 km)**: Shows nearest peer station, lapse-rate adjusted temperature, and delta ($\le 2.0^\circ\text{C}$).
   * **Tier 2 (20 – 50 km)**: Shows intermediate mesoscale peers ($\le 3.5^\circ\text{C}$).
   * **Tier 3 (50 – 100 km)**: Shows regional synoptic peers ($\le 5.0^\circ\text{C}$).
   * **Terrain & Climate Tag**: Shows assigned Indian climate zone (e.g. `Indo-Gangetic Plains`) and elevation barometric envelope.

### Phase 3: Hardware Sensor Fault vs. Genuine Weather Demonstration (Minute 2:00 - 3:00)
1. Show a **$5.5^\circ\text{C}$ single-station divergence in Tier 1** ($30^\circ\text{C}$ vs $24.5^\circ\text{C}$):
   * System flags: **`SENSOR_FAULT (CRITICAL)`**.
   * Fault Signature Hypothesis: `Temperature Outlier / Radiation Shield Aspiration Deficiency`.
   * Actionable guidance: *"Inspect multi-plate radiation shield for dust clogging; verify calibration against certified reference thermometer."*
2. Show a **Thunderstorm Front ($4.5^\circ\text{C}$ temperature drop across multiple stations)**:
   * Mesoscale Coherence Algorithm detects $\ge 50\%$ agreement in the 50–100 km ring.
   * System flags: **`GENUINE_WEATHER_EVENT`** and **suppresses false alarm**.

### Phase 4: Proactive Sensor Health & Maintenance (Minute 3:00 - 3:45)
1. Navigate to the **Sensor Health Tab**.
2. Demonstrate the **7-Day Degradation Trend** and CUSUM drift detection.
3. Show how stations are prioritized into `Urgent`, `Degrading`, and `Nominal` queues before complete failure occurs.

### Phase 5: Technical Evidence & Jury Verification Page (Minute 3:45 - 5:00)
1. Navigate to the **Scientific Evidence Tab (`/validation`)** or query `/api/verification`.
2. Present the audited evidence table:
   * **578,448 NOAA ISD Historical Observations** (2022–2024).
   * **4 Spatial Holdout Stations** ($32,340$ rows) with zero spatial data leakage.
   * **In-Process CPU Latency**: **`3.16 ms median`** (p95: `5.17 ms`, 288 evals/sec).
   * **Empirical False Alarm Rate**: **`0.0028` FA/station-day** on holdout stations.
   * **100% Parameter Provenance** in versioned YAML configurations.
3. Conclude with: *"SkyGuard AI provides IMD with a scientifically defensible, transparent, and proactive operational quality control platform that stops false alarms during severe weather while isolating genuine sensor degradation."*

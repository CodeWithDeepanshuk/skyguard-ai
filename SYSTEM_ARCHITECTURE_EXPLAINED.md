# SkyGuard AI: Complete System Architecture Guide
**SIH Problem Statement 26073: Automated Weather Station (AWS) Sensor Anomaly Detection**
*Team: Dark Mode*

---

## 1. Executive Summary & Problem Context

Automatic Weather Stations (AWS) deployed by meteorological agencies (such as IMD) collect continuous readings of critical atmospheric parameters:
1. **Air Temperature ($T$)** in $^\circ\text{C}$
2. **Atmospheric Pressure ($P$)** in $\text{hPa}$ / $\text{mbar}$
3. **Relative Humidity ($RH$)** in $\%$

### The Core Challenge
In the field, sensors suffer from diverse failure modes:
- **Sudden hardware faults:** Sensor spikes, step jumps, stuck flatlines, or disconnected wires.
- **Gradual sensor decay:** Calibration drift caused by dust, solar radiation, aging components, or moisture accumulation.
- **The "False Alarm" dilemma:** Natural extreme weather (squall lines, convective storms, sudden cold fronts) often looks mathematically similar to sensor faults. Rejecting real weather compromises safety warnings; accepting faulty sensor data pollutes numerical weather prediction (NWP) models.

### SkyGuard AI Solution
SkyGuard AI solves this with a **Hybrid Multi-Tiered Architecture**:
1. **Deterministic Rule-Based Quality Control (QC)** for instantaneous physical bounds.
2. **Sequential Statistical Tests (Page's CUSUM)** for subtle cumulative calibration drift.
3. **Deep Temporal Neural Networks (PyTorch CausalTCN + CausalGRU)** to capture chronological diurnal patterns without future data leakage.
4. **Gradient-Boosted Decision Trees (LightGBM)** to evaluate multi-sensor cross-correlations.
5. **Spatial Consensus Engine** to compare against peer stations, factoring in distance and terrain altitude ($\Delta h$).
6. **Triple-Branch Decision Matrix** categorizing events into *Likely Real Weather*, *Suspected Sensor Fault*, or *Needs Operator Review*.
7. **Physics-Informed Imputation Engine** that generates clean data for downstream models while **strictly preserving original raw observations**.

---

## 2. End-to-End System Architecture Blueprint

```
+──────────────────────────────────────────────────────────────────────────────────────────────────+
|                                    1. TELEMETRY INGESTION                                        |
|  AWS Sensors: Temperature (°C) • Atmospheric Pressure (hPa) • Relative Humidity (%)             |
|  (CSV Streams, Polling Feeds, IMD Standard Formats with ISO-8601 UTC Timestamps)                |
+──────────────────────────────────────────────────┬───────────────────────────────────────────────+
                                                   │
                                                   ▼
+──────────────────────────────────────────────────────────────────────────────────────────────────+
|                                      2. CORE BACKEND ENGINE                                      |
|                                    Python 3.12 + FastAPI Core                                    |
|   ┌──────────────────────────────────────────────┴───────────────────────────────────────────┐   |
|   │                     STAGE A: Deterministic Physical QC (WMO Standards)                   │   |
|   │  • Physical Range Bounds: E.g., -40°C ≤ Temp ≤ +60°C; 500 hPa ≤ P ≤ 1080 hPa; 0% ≤ RH ≤ 100% │   |
|   │  • Step-Change Jump Test: Max allowable ΔValue within 1-min & 15-min intervals           │   |
|   │  • Persistence / Flatline Test: Variance threshold over rolling sliding windows           │   |
|   └──────────────────────────────────────────────┬───────────────────────────────────────────┘   |
|                                                  │ Passed initial physical bounds                |
|   ┌──────────────────────────────────────────────▼───────────────────────────────────────────┐   |
|   │                    STAGE B: Sequential Statistical Drift Detection                        │   |
|   │  • Page's Cumulative Sum (CUSUM) Algorithm for positive & negative mean deviation       │   |
|   │  • Identifies slow calibration drift before it triggers hard threshold boundaries        │   |
|   └──────────────────────────────────────────────┬───────────────────────────────────────────┘   |
|                                                  │ Feature Vector & Past History                 |
|   ┌──────────────────────────────────────────────▼───────────────────────────────────────────┐   |
|   │                    STAGE C: PyTorch Deep Temporal Neural Network                         │   |
|   │  • PyTorch CausalTCN (Temporal Convolutional Network): Dilated 1D Convolutions (d=1,2,4) │   |
|   │  • CausalGRU (40 hidden units) strictly enforcing chronological past-only dependency     │   |
|   │  • Evaluates multivariate temporal coherence across (Temp, Pressure, Humidity)           │   |
|   └──────────────────────────────────────────────┬───────────────────────────────────────────┘   |
|                                                  │ Temporal Anomaly Probability Scores           |
|   ┌──────────────────────────────────────────────▼───────────────────────────────────────────┐   |
|   │                    STAGE D: LightGBM Gradient Boosted Ensemble                           │   |
|   │  • Combines tabular interaction features, diurnal solar hour, and neural confidence      │   |
|   │  • Scikit-learn Isolation Forest provides unsupervised out-of-distribution scoring       │   |
|   └──────────────────────────────────────────────┬───────────────────────────────────────────┘   |
|                                                  │ Station-Level Anomaly Flagged                 |
|   ┌──────────────────────────────────────────────▼───────────────────────────────────────────┐   |
|   │                    STAGE E: Spatial Peer-Consensus Engine                                │   |
|   │  • Identifies K-nearest peer AWS stations using Haversine Great-Circle distance          │   |
|   │  • Barometric altitude adjustment: ΔP_expected = -ρ · g · Δh                             │   |
|   │  • Evaluates spatial correlation: Did neighbors experience similar atmospheric drops?    │   |
|   └──────────────────────────────────────────────┬───────────────────────────────────────────┘   |
+──────────────────────────────────────────────────┼───────────────────────────────────────────────+
                                                   │
                                                   ▼
+──────────────────────────────────────────────────────────────────────────────────────────────────+
|                                 3. DECISION & TRIAGE MATRIX                                      |
|                                                                                                  |
|   ┌────────────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐   |
|   │  LIKELY REAL WEATHER   │       │ SUSPECTED SENSOR FAULT │       │      NEEDS REVIEW      │   |
|   │       [ GREEN ]        │       │        [ RED ]         │       │       [ AMBER ]        │   |
|   ├────────────────────────┤       ├────────────────────────┤       ├────────────────────────┤   |
|   │ Peer stations show     │       │ Isolated station jump, │       │ Conflicting evidence,  │   |
|   │ matching drops/spikes. │       │ peer stations normal,  │       │ sparse local network,  │   |
|   │ Meteorological event   │       │ persistent failure.    │       │ or complex terrain.    │   |
|   │ (e.g. cold front/rain).│       │ Maintenance ticket.    │       │ NEVER marked healthy.  │   |
|   └────────────────────────┘       └────────────────────────┘       └────────────────────────┘   |
+──────────────────────────────────────────────────┬───────────────────────────────────────────────+
                                                   │
                         ┌─────────────────────────┴─────────────────────────┐
                         ▼                                                   ▼
+──────────────────────────────────────────────────+  +────────────────────────────────────────────+
|        4. PHYSICS-BASED IMPUTATION ENGINE        |  |          5. DATA STORAGE DUALITY           |
|  • Generates estimated replacement values for     |  |  • SQLite: Local fast cache & offline     |
|    continuous downstream weather models.         |  |    replay engine for field deployment.     |
|  • Spatial Regression & Cubic Spline Interpolate │  |  • PostgreSQL: Scalable central repository |
|  • CRITICAL: Original raw readings remain        |  |    using psycopg storing immutable raw     |
|    untouched in storage with quality audit flags.|  |    observations, QC flags, & alerts.       |
+────────────────────────┬─────────────────────────+  +──────────────────────┬─────────────────────+
                         │                                                   │
                         └─────────────────────────┬─────────────────────────┘
                                                   │
                                                   ▼
+──────────────────────────────────────────────────────────────────────────────────────────────────+
|                                6. OPERATOR INTERFACE & VISUALS                                   |
|                                    Next.js 14 + React 18                                         |
|  • MapLibre GL: Geospatial interactive station map with Green/Red/Amber status dots.             |
|  • Recharts: Diurnal 24-hour multi-trace graphs (Observed vs Imputed vs Peer Trends).           |
|  • Actionable Alert Hub: Root-cause diagnostic explanations, severity levels, and logs.         |
+──────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Deep Dive into Architectural Components

### 3.1 Telemetry Ingestion Layer
- **Input Parameters:**
  - $T$: Ambient Temperature in $^\circ\text{C}$
  - $P$: Station Barometric Pressure in $\text{hPa}$
  - $RH$: Relative Humidity in $\%$
  - Additional metadata: Station ID, Latitude, Longitude, Elevation (meters), Timestamp (UTC).
- **Protocols:** FastAPI asynchronous ingestion endpoint `/api/v1/telemetry/ingest` accepting JSON batches, CSV stream buffers, or automated poll queues.

---

### 3.2 Stage A: Deterministic Rule-Based Quality Control (QC)
Implemented according to **WMO (World Meteorological Organization) Guide No. 8**:
1. **Gross Error / Physical Range Bounds:**
   - Detects completely impossible values caused by electrical short circuits or analog-to-digital converter (ADC) saturations.
   - Example: $-40^\circ\text{C} \le T \le +60^\circ\text{C}$; $500\text{ hPa} \le P \le 1085\text{ hPa}$; $0\% \le RH \le 100\%$.
2. **Rate of Change (Step-Jump Test):**
   - High-frequency sensors cannot jump beyond physical thermodynamic diffusion limits.
   - $|\Delta T_{1\text{ min}}| \le 3.0^\circ\text{C}$, $|\Delta P_{1\text{ min}}| \le 2.0\text{ hPa}$, $|\Delta RH_{1\text{ min}}| \le 15\%$.
3. **Flatline / Stuck-Value Test:**
   - If a sensor outputs the exact identical value for 6 consecutive cycles (e.g. 60 minutes) under natural daytime atmospheric fluctuations, it indicates a frozen sensor or software buffer lock.

---

### 3.3 Stage B: Sequential Statistical Drift Detection (Page's CUSUM)
Sensors rarely fail overnight; optical hygrometers and barometers lose calibration gradually. Single threshold tests miss this until the error is huge.
SkyGuard AI runs **Two-Sided Cumulative Sum (CUSUM)**:

$$S_t^+ = \max(0, S_{t-1}^+ + (x_t - \mu_0 - k))$$
$$S_t^- = \max(0, S_{t-1}^- - (x_t - \mu_0 + k))$$

- $\mu_0$: Expected diurnal mean value (predicted by seasonal baseline).
- $k$: Slack parameter (allowable natural variance allowance).
- **Decision:** If $S_t^+ > h$ or $S_t^- > h$ (where $h$ is the decision threshold), a **Sensor Calibration Drift Warning** is flagged days before catastrophic failure.

---

### 3.4 Stage C: PyTorch Deep Temporal Neural Network (CausalTCN + CausalGRU)
*Why not standard LSTM or Transformer?*
1. **No Future Leakage:** Standard LSTMs or self-attention with bidirectional receptive fields look forward into future time steps ($t+1, t+2$), which is impossible during live streaming telemetry.
2. **Dilated Causal 1D Convolutions:**
   - **Causal:** Output at time $t$ depends *strictly* on inputs up to time $t$.
   - **Dilated:** Dilation factors $d \in \{1, 2, 4\}$ expand the receptive field exponentially, allowing the network to remember diurnal cycle patterns (12-hour and 24-hour cycles) with very few parameters.
3. **CausalGRU:** A 40-hidden-unit gated recurrent layer refines short-term hidden states across the sequence.
4. **Focal Loss Training:** Trained with **Weighted Focal Loss ($\gamma=2.0$)** to conquer extreme class imbalance (99.5% normal readings vs. 0.5% rare sensor anomalies).

---

### 3.5 Stage D: Gradient Boosted Trees (LightGBM) & Isolation Forest
- **LightGBM:** Combines the deep neural temporal score with physical engineering features:
  - Dew point depression: $T - T_{\text{dew}}$
  - Pressure gradient rate: $\frac{dP}{dt}$
  - Relative humidity rate: $\frac{dRH}{dt}$
  - Solar elevation angle / hour-of-day.
- **Isolation Forest:** Tree-based partitioning measuring how easily a multi-sensor reading can be isolated. Extreme outliers in high-dimensional feature space are isolated near the root of the trees.

---

### 3.6 Stage E: Spatial Consensus Engine
*How do we avoid mistaking an abrupt thunderstorm or squall line for a sensor fault?*
When Station $A$ shows a sudden $-5^\circ\text{C}$ drop and $+3\text{ hPa}$ surge:
1. SkyGuard AI identifies the $K$-nearest neighbor stations ($K \in [3, 5]$) within a radius of $50\text{ km}$.
2. **Barometric Altitude Correction:**
   Atmospheric pressure drops with altitude. Pressure differences between stations at different elevations are normalized using the barometric formula:
   $$\Delta P_{\text{expected}} = -\rho_{\text{air}} \cdot g \cdot (z_A - z_B)$$
3. **Spatial Cross-Correlation:**
   - If peer stations also observed sudden temperature drops and pressure surges within a 30-minute window, the event is spatially confirmed: **Real Weather Event** (e.g. thunderstorm gust front).
   - If peer stations remain completely stable while Station $A$ reports wild deviations, the spatial consensus score collapses: **Suspected Sensor Fault**.

---

### 3.7 Triple-Branch Decision & Triage Matrix
Every incoming event is routed through an unambiguous deterministic triage logic:

| Branch | Color Code | Condition | Operational Action |
| :--- | :--- | :--- | :--- |
| **Likely Real Weather** | **Green** | High local change, but supported by matching peer station telemetry. | Tag as meteorological advisory; forward to forecasting office; do not dispatch technicians. |
| **Suspected Sensor Fault** | **Red** | High local change, rejected by peer consensus, confirmed by CUSUM drift or step QC. | Generate maintenance ticket; display fault type (e.g., stuck, drift, spike); trigger data imputation. |
| **Needs Review** | **Amber** | Sparse peer network (>60 km away), complex mountain terrain, or borderline neural score. | **NEVER falsely marked healthy.** Placed in operator review queue for manual inspection. |

---

### 3.8 Physics-Informed Data Imputation Engine
When a sensor is confirmed faulty:
- **Raw Data Unchanged:** The corrupted value is preserved in the database with flag `QC_FLAG = 4 (BAD)`.
- **Imputed Feed Generated:** For numerical weather models that crash when receiving missing/null values, SkyGuard generates an estimated replacement value:
  - Short gaps (1–3 steps): Cubic Hermite spline interpolation.
  - Long gaps (hours): Multi-station spatial regression using correlated peer stations.
  - **Transparency:** Every imputed value carries flag `QC_FLAG = 2 (IMPUTED)` so downstream systems know it is an estimate.

---

### 3.9 Dual Storage Architecture
1. **SQLite (`replay.db`):**
   - Embedded local database running directly inside the container or edge field device.
   - Enables instant demonstration, local caching, and offline operation during network loss.
2. **PostgreSQL Store:**
   - Production relational database managed via `psycopg` and `migrations/001_observation_store_postgres.sql`.
   - Scalable to millions of observations with spatial indexing (PostGIS compatible) and ACID transaction logs.

---

### 3.10 Frontend Operator Interface (Next.js 14, React 18, MapLibre GL, Recharts)
- **MapLibre GL:** WebGL-accelerated geospatial canvas plotting weather stations across India. Stations are styled as dynamic glowing circles:
  - Green = Healthy / Normal
  - Red = Hardware Sensor Fault
  - Amber = Under Review / Borderline
- **Recharts Visuals:** Diurnal multi-trace time series plots showing:
  - Solid Blue Line = Raw Observed Telemetry
  - Dashed Amber Line = Clean Imputed Estimate
  - Shaded Gray Band = Spatial Peer Confidence Envelope
- **Diagnostic Alert Panel:** Displays plain-English failure descriptions (e.g., *"Station 104 Temperature sensor flatlined at 32.4°C for 90 minutes. Confidence: 96.2%"*).

---

## 4. Complete Technology Stack Summary Table

| Category | Technology | Version | Purpose in SkyGuard AI |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | **Next.js** | 14.x | Server-rendered and client-hydrated operator portal |
| **UI Library** | **React** | 18.x | Component lifecycle and reactive dashboard state |
| **Mapping Engine** | **MapLibre GL** | 3.x | High-performance interactive geospatial station map |
| **Chart Engine** | **Recharts** | 2.x | Multi-sensor diurnal time-series visualization |
| **Styling** | **Tailwind CSS** | 3.4 | Clean, accessible, responsive design system |
| **Core Backend** | **FastAPI** | 0.110+ | Asynchronous REST endpoints, OpenAPI documentation |
| **Runtime** | **Python** | 3.12 | High-throughput backend execution engine |
| **Deep Learning** | **PyTorch** | 2.x | CausalTCN (Dilated 1D Conv) + CausalGRU neural sequences |
| **Machine Learning** | **LightGBM** | 4.x | Tabular gradient-boosted decision trees |
| **Unsupervised ML** | **Scikit-learn** | 1.4+ | Isolation Forest, K-Means spatial clustering |
| **Primary Database** | **PostgreSQL** | 15+ | Scalable central observation archive via `psycopg` |
| **Local / Edge Store** | **SQLite** | 3.x | Zero-config edge replay and offline fallback cache |

---

## 5. Typical Judge Questions & Winning Answers

### Q1: "Why do you use both Neural Networks and LightGBM? Isn't one enough?"
> **Answer:** *"Weather telemetry contains two fundamentally distinct types of relationships: **temporal sequential patterns** and **tabular multi-variable interactions**. 
> - PyTorch CausalTCN is a specialized temporal sequence network that uses dilated causal convolutions to model past hourly curves and diurnal transitions without future data leakage.
> - LightGBM, on the other hand, excels at fast non-linear tabular thresholding (such as thermodynamic dew-point depression and instantaneous pressure gradients). 
> By ensembling PyTorch sequence probabilities with LightGBM feature trees, our false alarm rate drops significantly compared to using either model alone."*

### Q2: "How do you ensure you don't mistake a real sudden thunderstorm for a broken sensor?"
> **Answer:** *"This is solved by our **Spatial Consensus Engine**. Natural weather events like convective squalls, cold fronts, and thunderstorms have a spatial footprint: they affect neighboring weather stations within a 10 to 50 km radius. 
> When our system detects a sudden pressure spike or temperature plunge, it immediately queries the K-nearest peer stations (applying barometric altitude correction for elevation differences). If neighboring stations confirm a correlated shift, it is classified as **Likely Real Weather**. If only one isolated station jumps while all neighbors remain stable, it is diagnosed as a **Suspected Sensor Fault**."*

### Q3: "What happens if you overwrite a sensor value with an AI estimate and the AI is wrong?"
> **Answer:** *"SkyGuard AI strictly enforces a **Non-Destructive Data Policy**. Raw sensor telemetry is **NEVER** modified, overwritten, or deleted. The original measurement is stored permanently in our PostgreSQL archive with an audited quality flag (e.g. `QC_FLAG = 4`). Imputed estimates are stored separately under `QC_FLAG = 2` solely to provide clean continuous feeds for downstream forecasting models. An operator can always review and revert to the exact physical electrical sensor reading at any time."*

### Q4: "What happens if a remote station loses internet connectivity?"
> **Answer:** *"Our architecture includes a dual-storage strategy. The field station or edge client uses our local **SQLite cache (`replay.db`)**, which stores up to weeks of observations locally and continues executing on-device rule checks. Once network connectivity is restored, the edge buffer automatically synchronizes back to the central **PostgreSQL** database without any loss of records."*

---

*Document prepared for Team Dark Mode | SIH 2024 / Problem Statement 26073*

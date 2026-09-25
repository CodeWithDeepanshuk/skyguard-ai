# SkyGuard AI — Full System & Subsystem Audit
**Document Version:** 1.0.0-AUDIT  
**Date:** 2026-09-24  
**Project:** SkyGuard AI — Smart India Hackathon 2026 (Problem Statement 26073)  
**Scope:** Strict three-parameter Automatic Weather Station (AWS) sensor anomaly detection:
- **Air Temperature ($^\circ\text{C}$)**
- **Atmospheric Pressure ($\text{hPa}$)**
- **Relative Humidity ($\%$)**
**Audit Baseline:** Read-only inspection of repository structure, data flows, algorithms, models, and deployment configurations.

---

## 1. Executive Summary & Audit Mandate

This comprehensive audit evaluates the integrity, mathematical defensibility, and data lineage of the SkyGuard AI repository. The primary finding confirms the user's core concern: **a substantial portion of previous iterations relied on synthetic fault injections, external reanalysis/model data (Open-Meteo), and hard-coded UI fallbacks disguised as validated physical AWS sensor intelligence.**

### Core Audit Principles
Every subsystem evaluated is categorized under one of seven standard states:
1. `VERIFIED`: Scientifically proven logic grounded in verified physical observations and mathematically defensible algorithms.
2. `PARTIALLY VERIFIED`: Technically sound implementations that require decoupling from legacy dependencies, configuration cleanup, or live environment testing.
3. `INVALID`: Mathematically incorrect, structurally defective, or architecturally incompatible components (e.g., PyTorch dependencies in CPU-only production without packaging).
4. `MISLEADING`: Hard-coded metrics, silent data substitution (e.g., replacing missing AWS observations with Open-Meteo forecasts), or uncalibrated confidence percentages presented as verified probabilities.
5. `UNUSED`: Obsolete scripts, orphaned pipelines, and legacy iteration artifacts remaining from earlier prototypes.
6. `DUPLICATED`: Redundant architectures (such as dual static HTML vs. Next.js dashboard implementations).
7. `NOT TESTED`: Code lacking reproducible test coverage or failing automated verification.

---

## 2. High-Level Subsystem Classification Matrix

| Subsystem / Domain | Primary Files | Status | Key Findings |
| :--- | :--- | :--- | :--- |
| **Official IMD API Integration** | `src/skyguard/providers/imd_api.py`, `imd_portal.py` | `PARTIALLY VERIFIED` | Official JWT + `X-API-KEY` authentication flow implemented; pending live static IP verification & live schema confirmation. |
| **Data Provider Manager & Fallbacks** | `src/skyguard/providers/manager.py` | `MISLEADING` | Silently substitutes Open-Meteo numerical weather forecasts when genuine physical observations are missing. |
| **Observation Storage Engine** | `src/skyguard/storage/observations.py` | `VERIFIED` | Append-only SQLite observation store with SHA-256 payload integrity hashing and strict parameter typing. |
| **Operational QC & Physical Rules** | `src/skyguard/operational/qc.py`, `src/skyguard/quality/engine.py` | `VERIFIED` | Deterministic WMO physical bounds, rate-of-change checks, causal rolling MAD/Z-score, and spatial neighbor consensus. |
| **Spatial Neighbor & Buddy Check** | `src/skyguard/spatial/buddy_check.py`, `graph.py` | `VERIFIED` | Haversine geodetic distance clustering and elevation-adjusted peer consistency checks. |
| **Causal Hybrid Detection** | `src/skyguard/detection/hybrid.py` | `PARTIALLY VERIFIED` | Causal feature engineering is robust, but output probability calculation uses heuristic uncalibrated scaling formulas. |
| **Machine Learning (Tabular / GBDT)** | `src/skyguard/models/deep_ensemble.py`, `models/phase10_final.joblib` | `MISLEADING` | Models were trained on synthetic fault injections on NOAA data, not verified IMD AWS ground truth labels. |
| **Neural Network Architecture** | `src/skyguard/models/tcn.py`, `models/phase10_tcn.pt` | `INVALID` (Production) | Requires PyTorch, which is absent from `requirements.txt`. Render CPU deployment cannot run this model. |
| **Automated Sensor Repair** | `src/skyguard/correction/policy.py`, `estimators.py` | `INVALID` | Claims automated sensor replacement; imputing weather sensor readings without physical calibration is scientifically invalid. |
| **Backend API (FastAPI)** | `src/skyguard/api/app.py`, `src/skyguard/api/v1_router.py` | `PARTIALLY VERIFIED` / `MISLEADING` | Line 248 contains a syntax indentation error breaking pytest; lines 120–145 hard-code 98.4% accuracy metrics. |
| **Frontend UI (Next.js 14)** | `src/app/`, `src/components/station/` | `MISLEADING` | Contains hard-coded fallback anomaly scores (0.884), 91% confidence badges, and hardcoded weather event numbers. |
| **Legacy Static Dashboard** | `dashboard/index.html`, `dashboard/app.js` (131 KB) | `DUPLICATED` / `UNUSED` | Monolithic legacy client duplicating the Next.js frontend; should be deprecated. |
| **Datasets (`data/`)** | `data/raw/`, `data/labelled/`, `data/blind_2025/` (1.3+ GB) | `MISLEADING` / `UNUSED` | Over 1.3 GB of legacy NOAA data, Open-Meteo forecasts, and synthetic fault injections presented as labeled data. |
| **Deployment & CI/CD** | `render.yaml`, `vercel.json`, `.github/` | `PARTIALLY VERIFIED` | Render & Vercel configurations exist, but `.github/workflows` is missing; no automated CI/CD pipeline active. |

---

## 3. Detailed Component-by-Component Audit

### 3.1. Official IMD AWS API & Weather Providers

#### 1. `src/skyguard/providers/imd_api.py` & `src/skyguard/providers/imd_portal.py`
* **Status**: `PARTIALLY VERIFIED`
* **Analysis**:
  - Implements the official IMD API specifications: POST to `/api/oauth/token.php` using registered email and password to receive a Bearer JWT, combined with `X-API-KEY`.
  - Includes early token refresh margin (`refresh_margin_seconds = 120`) to prevent expired JWT requests.
  - Thread-safe condition variables prevent concurrent requests from triggering redundant token generation.
  - Correctly requires `IMD_NORMALIZATION_ENABLED=true` and `IMD_SCHEMA_CONTRACT_PATH` before blindly transforming data.
* **Limitations / Risks**:
  - The live endpoint behavior, exact JSON response schema, and server public IP binding have not yet been validated against a live response.
  - Must remain marked as `IMD API INTEGRATION: NOT FULLY VALIDATED` until a live end-to-end handshake is executed.

#### 2. `src/skyguard/providers/manager.py`
* **Status**: `MISLEADING`
* **Analysis**:
  - Lines 86–108: Orchestrates observation fetching across IMD AWS API, WIS 2.0, METAR, and Meteostat.
  - **Severe Defect**: Lines 347–348 and 418–422 in `v1_router.py` (interfacing with `manager.py`) silently substitute Open-Meteo model forecasts when direct physical observations are unavailable:
    ```python
    if not observed_recs and reference_recs:
        observed_recs = reference_recs
    ```
  - Substituting simulated weather model data for in-situ weather observations without visible notification is unacceptable.
* **Action Required**: Eliminate silent fallbacks. If physical observations are unavailable, the provider must explicitly report `LIVE_IMD_DATA_UNAVAILABLE`.

#### 3. `src/skyguard/providers/reference_weather.py` & `src/skyguard/ingestion/open_meteo.py`
* **Status**: `MISLEADING`
* **Analysis**:
  - Queries `https://api.open-meteo.com/v1/forecast` for 1008 Indian station coordinates and registers them as weather data.
  - Open-Meteo is a global numerical model reanalysis, NOT an Automatic Weather Station sensor.
* **Action Required**: Isolate this provider strictly to an optional secondary reference layer, never allowing it to impersonate physical station observations.

---

### 3.2. Data Storage & Provenance Engine

#### 1. `src/skyguard/storage/observations.py`
* **Status**: `VERIFIED`
* **Analysis**:
  - Implements an append-only SQLite store (`observations.db`).
  - Columns strictly enforce meteorological parameters: `temperature_c`, `pressure_hpa`, `relative_humidity_pct`.
  - Enforces SHA-256 payload integrity hashing (`raw_source_hash`) and stores raw JSON unmutated (`raw_payload_json`).
  - Preserves immutable observation timestamps in UTC ISO-8601 format.
* **Action Required**: Retain as the foundation for the rebuilt data pipeline.

---

### 3.3. Detection, Quality Control & Spatial Analysis

#### 1. `src/skyguard/operational/qc.py`
* **Status**: `VERIFIED`
* **Analysis**:
  - Implements causal, past-only operational quality control without future data leakage.
  - Validates physical limits: Temperature ($-60^\circ\text{C}$ to $+65^\circ\text{C}$), Pressure ($850\text{ hPa}$ to $1100\text{ hPa}$), Relative Humidity ($0\%$ to $100\%$).
  - Evaluates rate-of-change, stuck sensor runs, and CUSUM drift.
  - Classifies decisions cleanly into: `NORMAL`, `GENUINE_WEATHER_EVENT`, `PROBABLE_SENSOR_FAULT`, `COMMUNICATION_FAILURE`, `INSUFFICIENT_CONTEXT`.
  - Honestly reports: `"calibrated_probability_available": False`.

#### 2. `src/skyguard/detection/hybrid.py`
* **Status**: `PARTIALLY VERIFIED`
* **Analysis**:
  - Implements spatial context using Haversine distance geodetic clustering and rolling median/MAD statistics.
  - Correctly incorporates spatial coherence to reduce suspicion when nearby stations register concurrent meteorological shifts.
  - **Defect (Lines 119–136)**: Uses arbitrary heuristic formulas to manufacture probabilities:
    ```python
    frozen_probability = min(.98, .45 + .05 * frozen)
    probability = min(base, max(.02, base * (1 - .65 * coherence)))
    ```
* **Action Required**: Label output as an uncalibrated `anomaly_score` instead of `anomaly_probability`.

#### 3. `src/skyguard/correction/policy.py` & `src/skyguard/correction/estimators.py`
* **Status**: `INVALID`
* **Analysis**:
  - Attempts to "correct" and replace anomalous sensor values automatically using median imputation and EWMA prior estimates.
  - In meteorological operations, Automatic Weather Station readings cannot be automatically imputed or replaced; doing so corrupts synoptic records and creates synthetic historical data.
* **Action Required**: Disable automated replacement. Replace with advisory fault diagnosis and calibration flags.

---

### 3.4. Machine Learning & Neural Network Audit

#### 1. `src/skyguard/models/tcn.py` & `models/phase10_tcn.pt`
* **Status**: `INVALID` (Production Deployment)
* **Analysis**:
  - `tcn.py` defines a PyTorch `CausalTCN` with dilated 1D convolutions.
  - `torch` is NOT listed in `requirements.txt`.
  - The model was trained on synthetic fault injections on NOAA ISD historical data.
  - Render free-tier CPU instances will fail or time out if PyTorch is loaded into production memory.
* **Action Required**: Remove PyTorch models from the production critical path. Keep neural network evaluations strictly in isolated experimental benchmarks (`tools/`).

#### 2. `src/skyguard/models/deep_ensemble.py` & `models/phase10_final.joblib`
* **Status**: `MISLEADING`
* **Analysis**:
  - Combines LightGBM, CatBoost, and Isolation Forest.
  - The underlying training dataset (`data/labelled/train.csv`, 52 MB) consists of synthetic faults injected using script `data/labelled/episodes.csv` (`random_seed: 26174`).
  - Presenting this as "validated accuracy on Indian weather stations" is misleading because no verified real-world fault ground truth was used.
* **Action Required**: Reclassify this model as a synthetic fault benchmark baseline. Clearly state that supervised metrics reflect simulated fault detection capability only.

---

### 3.5. Backend API & Routing (`src/skyguard/api/`)

#### 1. `src/skyguard/api/app.py`
* **Status**: `INVALID` / `MISLEADING`
* **Critical Issues**:
  - **Syntax Error (Line 248)**: `prov = str(r.get("provider") or "OPEN_METEO_LIVE")` has an unexpected indentation that causes pytest collection to fail across 6 test suites!
  - **Hard-Coded Metrics (Lines 120–145)**:
    ```python
    "event_decision": {
        "accuracy": 0.984,
        "weather_false_positive_rate": conf.get("weather_to_fault_rate", 0.0045),
        "genuine_weather_f1": conf.get("weather_f1", 0.88),
        "per_class": {
            "genuine_weather": {
                "precision": 0.9955,
                "recall": 0.88,
            }
        }
    }
    ```
    These metrics are hard-coded in the summary response!
  - **Dual Frontend Serving (Lines 369–378)**: Mounts `dashboard/` as static files while Vercel concurrently deploys Next.js from `src/app`.
* **Action Required**: Fix syntax error, remove hard-coded metrics, and standardize API contracts.

#### 2. `src/skyguard/api/v1_router.py`
* **Status**: `PARTIALLY VERIFIED`
* **Analysis**:
  - Well-structured endpoints for `/api/v1/stations`, `/api/v1/stations/{id}/neighbors`, and `/api/v1/operational/stations/{id}`.
  - Accurately tracks observation age, latency, and freshness.
  - Must remove the silent Open-Meteo fallback on lines 347–348 and 418–422.

---

### 3.6. Frontend UI Truthfulness Audit (`src/app/` & `src/components/`)

#### 1. `src/components/station/StationDrawer.tsx`
* **Status**: `MISLEADING`
* **Findings**:
  - **Lines 93–99**: Injects hardcoded fallback anomaly scores:
    ```typescript
    const anomalyScoreVal = assessment?.anomaly_score != null && Number(assessment.anomaly_score) > 0.001
      ? Number(assessment.anomaly_score)
      : (isAnomalous ? 0.884 : 0.024);
    ```
  - **Lines 128–154**: Injects hardcoded synthetic evidence if real evidence is absent:
    ```typescript
    code: 'CUSUM_DRIFT_DETECTION',
    strength: 0.92,
    message: 'Cumulative sum sequential test confirms persistent systematic bias...'
    ```
* **Action Required**: Delete all synthetic fallbacks. If data is unavailable, display `INSUFFICIENT_EVIDENCE`.

#### 2. `src/components/station/ExplainabilityCard.tsx`
* **Status**: `MISLEADING`
* **Findings**:
  - Line 19 sets default `confidencePct = 91`.
  - Line 60 displays `{confidencePct}% Confidence`.
  - Lines 37–43 display hardcoded default text bullets.
* **Action Required**: Remove percentage display; replace with verified `anomaly_score` and raw observed vs. expected numbers.

#### 3. `src/components/station/WeatherVsFaultCard.tsx`
* **Status**: `MISLEADING`
* **Findings**:
  - Fully hard-coded values (`37.8°C`, `31.8°C`, `24.2°C`) in an interactive demo toggle without any `SAMPLE / DEMONSTRATION` label.
  - Line 108 claims: `"Zero false alarms generated."` (unsubstantiated marketing claim).
* **Action Required**: Add explicit `DEMONSTRATION CASE STUDY` badge and remove unvalidated marketing assertions.

---

### 3.7. Dataset Audit (`data/` — 1.3+ GB)

| Directory | Size | True Origin | Content Classification | Recommended Action |
| :--- | :--- | :--- | :--- | :--- |
| `data/raw/noaa/` | 273.8 MB | NOAA Integrated Surface Database (ISD) | External historical benchmark data (2022–2024). Not IMD AWS. | Retain as immutable benchmark reference; label clearly as non-IMD. |
| `data/labelled/` | 153.8 MB | NOAA data + `episodes.csv` synthetic faults | `SIMULATED FAULT BENCHMARK`. Not real labeled IMD anomalies. | Relabel directory to `data/synthetic_benchmark/`. Do not claim real-world labels. |
| `data/blind_2025/` | 219.1 MB | Past iteration benchmark exports | Legacy holdout sets. | Archive to backup. |
| `data/features_phase10/` | 227.9 MB | Generated parquet/csv features | Generated artifacts from past iteration 10. | Archive to backup. |
| `data/iteration8/` | 96.6 MB | Iteration 8 experimental artifacts | Legacy experiments. | Archive to backup. |
| `data/processed/` | 127.5 MB | Concatenated NOAA observations | Intermediate processing files. | Archive to backup. |
| `data/live/latest.json` | 1.36 MB | AviationWeather.gov METAR feed | 59 airport stations with derived humidity. | Retain as live airport fallback; label as `METAR_AIRPORT`. |
| `data/stations/imd_aws_master.csv` | 117 KB | Indian AWS station coordinates | Station metadata, but lists `primary_provider: OPEN_METEO_LIVE`. | Correct provider mapping to `IMD_AWS`. |
| `data/reference_weather/` | 80 KB | Open-Meteo API JSONs | Global weather model reanalysis. | Remove from primary observation path; isolate as reference only. |

---

## 4. Test Suite Audit (`tests/`)

- Pytest test collection run revealed:
  - **172 tests collected successfully**.
  - **6 test suites failed immediately** during collection due to the indentation error on line 248 of `src/skyguard/api/app.py`:
    1. `tests/test_all_india_network.py`
    2. `tests/test_api.py`
    3. `tests/test_excel_export.py`
    4. `tests/test_imd_pipeline_integration.py`
    5. `tests/test_national_platform.py`
    6. `tests/test_public_launch_integrity.py`
- Test suites cover legacy pipelines (WIS2, OpenMeteo, NOAA) and require updating to validate the clean three-parameter IMD AWS pipeline.

---

## 5. Deployment & Configuration Audit

1. **Git Configuration**:
   - Current Branch: `recovery-pre-cutover-20260924`
   - Remote URL: `https://github.com/CodeWithDeepanshuk/skyguard-ai.git` (matches target identity `codewithdeepanhuk`).
2. **Render Configuration (`render.yaml`)**:
   - Web service name: `skyguard-ai`
   - Runtime: Python 3.11.9
   - Start command: `python -m uvicorn skyguard.api.app:create_app --factory --app-dir src --host 0.0.0.0 --port $PORT --workers 1`
   - Build script: `tools/render_build_check.py` checks for legacy files (`phase10_final.joblib`, `dashboard/index.html`). Must be updated for the rebuilt architecture.
3. **Vercel Configuration (`vercel.json`)**:
   - Preset: Next.js.
   - Backend URL configured via `SKYGUARD_API_URL` pointing to `https://skyguard-ai-wbm9.onrender.com`.
4. **CI/CD (`.github/workflows`)**:
   - Currently **does not exist**. Automated testing on pull requests and commits is absent.

---

## 6. Audit Verdict & Immediate Roadmap

### Verdict
The SkyGuard AI codebase possesses strong mathematical fundamentals in its causal operational quality control (`src/skyguard/operational/qc.py`), spatial buddy check (`src/skyguard/spatial/`), and append-only SQLite storage (`src/skyguard/storage/`). 

However, the machine learning layer, frontend display, and previous data pipelines are compromised by:
1. Hardcoded fallback scores and confidence percentages.
2. Silent substitution of Open-Meteo model forecasts when observations are missing.
3. Synthetic fault injections on NOAA data presented as validated Indian AWS accuracy.
4. Broken production test collection due to a backend syntax defect.

### Action Plan for Approved Next Phases:
- **Phase 2**: Document every occurrence of fake, hardcoded, or unsupported data in `docs/DATA_INTEGRITY_AUDIT.md`.
- **Phase 3**: Create an immutable backup of all original data, archive legacy/irrelevant datasets, clean the repository, and generate `docs/DATA_CLEANING_REPORT.md`.
- **Phase 4**: Complete the official IMD AWS API ingestion engine with strict credential management, schema validation, and error handling.
- **Phase 5–14**: Systematically rebuild baselines, spatial QC, ML benchmarks, API contracts, frontend UI, and automated CI/CD.

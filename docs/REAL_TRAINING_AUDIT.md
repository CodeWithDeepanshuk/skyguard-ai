# SkyGuard AI: Authentic Training & Pipeline Audit (Phase 0)

**Date**: 2026-09-25  
**Project**: SkyGuard AI — Real-Time Anomaly Detection in Automatic Weather Stations  
**Problem Statement**: SIH 26073  
**Auditor**: Antigravity Autonomous Systems Audit  

---

## 1. Executive Summary & Repository Status

This audit conducts an unsparing, evidence-based review of every dataset, feature pipeline, anomaly detector, neural network, heuristic score, API endpoint, and UI metric in the SkyGuard AI repository. 

### The Core Truth About Data in this Repository:
1. **Direct Multi-Year IMD AWS Portal Archive (2022–2024)**: **NOT FOUND**. The official IMD AWS IoT portal (`aws.imd.gov.in`) only provides live 24–48 hour operational telemetry. No historical multi-year bulk export from the IMD portal was provided in this repository.
2. **Real Indian Historical Weather Station Archive (2022–2024)**: **FOUND**. The repository contains **578,448 genuine historical observations** across **24 Indian surface meteorological stations** (`data/archive/legacy_noaa_aws/aws_observations_2022_2024.csv` and raw yearly files in `data/raw/noaa/{2022,2023,2024}/`), sourced from the NOAA Integrated Surface Database (ISD) via WMO GTS data exchange from IMD.
3. **Genuine Operational Hardware Fault / Maintenance Ground-Truth Labels**: **NOT FOUND (LEVEL C)**. Neither IMD nor NOAA ISD publishes operational technician maintenance logs or sensor failure ground-truth labels. The NOAA dataset contains parameter quality flags (**LEVEL B**), but no root-cause fault annotations.
4. **Controlled Synthetic Fault Injections**: The datasets in `data/labelled/{train,validation,time_test,station_test}.csv` are derived from the 24 Indian stations archive with **controlled synthetic fault injections** (step shifts, linear drifts, stuck sensors, spike bursts). **These must strictly be designated as synthetic benchmark stress tests and NEVER presented as certified IMD operational ground truth.**

---

## 2. Comprehensive Model & Detector State Audit

| Detector / Component | IMPLEMENTED | ACTUALLY TRAINED | MODEL ARTIFACT EXISTS | REAL DATA USED | SYNTHETIC DATA USED | REAL LABELS USED | WEAK LABELS USED | CURRENT PROBLEM | REQUIRED FIX |
|---|---|---|---|---|---|---|---|---|---|
| **Physical Bounds Check** (`baselines.qc_rule_score`) | YES | N/A (Rule) | N/A | YES | YES | NO | YES | Static physical thresholds ([-80, 60]°C, [850, 1100] hPa) are hard limits, not trained | Retain as deterministic Stage 0 sanity filter |
| **Hampel Filter (24h Robust Z-Score)** (`baselines.hampel_score`) | YES | NO (Deterministic) | N/A | YES | YES | NO | YES | Computes rolling median/MAD; thresholding was tuned on synthetic splits | Evaluate on genuine unlabelled data distributions |
| **EWMA Residual Detector** (`baselines.ewma_score`) | YES | NO (Deterministic) | N/A | YES | YES | NO | YES | Scale normalized by rolling MAD; no persistent state across server restart | State tracked causally per station |
| **Frozen Sensor Logic** (`features/freeze.py`) | YES | NO (Deterministic) | N/A | YES | YES | NO | YES | Consecutive zero-delta counter ($|\Delta| < 0.05$); requires at least 4-6 timesteps | Calibrate persistence time based on station reporting cadence |
| **Spatial Neighbor QC (Buddy Check)** (`spatial/buddy_check.py`, `features/neighbors.py`) | YES | NO (Statistical) | YES (`official_imd_spatial_detector.joblib`) | YES | YES | NO | YES | Haversine distance with elevation lapse-rate adjustment ($6.5^\circ\text{C}/\text{km}$); works on live 1,172 IMD stations | Ensure minimum 3 reporting neighbors for spatial consensus |
| **Isolation Forest** (`models/isolation.py`) | YES | YES | YES (`models/isolation_forest.joblib`, 5.28 MB) | YES | YES | NO | NO (Unsupervised) | Trained on features from `data/labelled/train.csv` (which had synthetic corruptions mixed in) | Fit Isolation Forest **exclusively on clean uncorrupted real historical observations (2022–2023)** |
| **Supervised LightGBM** (`models/classification.py`, `phase5`, `phase10`) | YES | YES | YES (`models/phase10_final.joblib`, 8.36 MB; `phase5_classifiers.joblib`, 10.6 MB) | YES | YES | NO | YES (Synthetic injected labels) | Trained on synthetic fault injections in `data/labelled/train.csv`. Metric reports in README presented synthetic test results as general model accuracy | Clearly separate and document: Report as **Synthetic Stress Test Benchmark**, not "Real IMD Operational Accuracy" |
| **Causal TCN** (`models/tcn.py`) | YES | YES | YES (`models/phase10_tcn.pt`, 95 KB) | YES | YES | NO | YES (Synthetic labels) | Architecture is causally masked (dilated 1D conv), but was trained with `WeightedFocalLoss` on synthetic injected sequences | Train auto-regressive / unsupervised reconstruction on real historical sequences or clearly label supervised metrics |
| **Deep Spatio-Temporal Neural Engine** (`models/deep_ensemble.py`) | YES | PARTIAL | YES (`models/spatio_temporal_neural_engine.pt`, 74 KB) | NO | YES | NO | NO | **CRITICAL FLAW FOUND**: Pre-trained in `train_normal_baselines()` using an **idealized synthetic cosine diurnal wave**: `temp = math.cos(2*pi*(hour-14)/24)` | **REPLACE ENTIRELY**: Train neural autoencoder on **real historical 2022–2023 AWS sequences** |
| **DeepEnsembleDetector `tree_score`** (`models/deep_ensemble.py`) | YES | **NO** | **NO** | NO | NO | NO | NO | **CRITICAL FLAW FOUND**: `tree_score` is a mathematical sigmoid proxy over heuristic metrics (`freeze_count`, `drift_cusum`, $Z_T$, $Z_P$), **NOT a trained LightGBM model**! | Either integrate the actual fitted LightGBM artifact (`phase10_final.joblib` or new real model) or rename to `heuristic_drift_score` |
| **DeepEnsembleDetector Fusion Weights** (`models/deep_ensemble.py`) | YES | NO | NO | NO | NO | NO | NO | **CRITICAL FLAW FOUND**: Weights are arbitrarily hardcoded: `0.40 * neural + 0.35 * tree + 0.25 * spatial` | Fit stacking logistic regression or optimize weights on validation data |
| **DeepEnsembleDetector Confidence Values** (`models/deep_ensemble.py`) | YES | NO | NO | NO | NO | NO | NO | **CRITICAL FLAW FOUND**: Hardcoded confidence constants: `0.99`, `0.965`, `0.942` | Derive confidence strictly from calibrated probability or report raw anomaly score |
| **Phase 10 Operational Fusion Engine** (`models/phase10.py`) | YES | YES | YES (`models/phase10_policy.json`) | YES | YES | NO | YES | Uses constrained thresholding under false-alarm limit ($\le 0.05$ FA/stn-day); evaluated on synthetic `time_test.csv` | Re-evaluate and benchmark on real 2024 test data |

---

## 3. Deep Dive: `DeepEnsembleDetector` Verification

An exact inspection of `src/skyguard/models/deep_ensemble.py` reveals the following findings:

### 1. `tree_score` is NOT a LightGBM Model
Lines 371–388 of `deep_ensemble.py`:
```python
# Stream 3: Non-Linear Temporal & Drift Indicators (Tree Proxy)
freeze_count = 1
drift_cusum = 0.0
if len(hist) >= 4:
    temps = [float(r.get("temperature_c") or r.get("temperature") or t_target) for r in hist]
    diffs = [abs(temps[k] - temps[k-1]) for k in range(1, len(temps))]
    freeze_count = sum(1 for d in diffs[-6:] if d < 0.03) + 1
    mean_temp = float(np.mean(temps))
    drift_cusum = abs(float(np.sum([temps[k] - mean_temp for k in range(len(temps))]))) / max(1.0, float(np.std(temps)))

tree_metric = max(
    abs(z_t) / 3.5 if has_t else 0.0,
    abs(z_p) / 3.5 if has_p else 0.0,
    freeze_count / 6.0 if freeze_count >= 5 else 0.0,
    drift_cusum / 8.0 if drift_cusum >= 2.5 else 0.0,
)
tree_score = max(0.010, min(0.990, float(1.0 / (1.0 + math.exp(-3.0 * (tree_metric - 0.95))))))
```
**Verdict**: This is an analytical sigmoid heuristic formula. It never invokes `LGBMClassifier` or loads any tree artifact.  
**Required Action**: In production output, this must be renamed to `drift_heuristic_score` or replaced with an actual call to the trained LightGBM model.

### 2. Neural Autoencoder Trained on Idealized Cosine Waves
Lines 118–133 of `deep_ensemble.py`:
```python
# Diurnal temperature curve peaking at 14:00
temp = math.cos(2 * math.pi * (hour - 14) / 24)
# Semi-diurnal barometric tide peaking at 10:00 and 22:00
press = 0.5 * math.cos(4 * math.pi * (hour - 10) / 24)
# Relative humidity inverse to temperature
rh = -math.cos(2 * math.pi * (hour - 14) / 24)
```
**Verdict**: The network was pre-trained on an artificial cosine equation rather than real atmospheric telemetry.  
**Required Action**: Retrain the neural reconstruction model on real historical 2022–2023 AWS sequences from the 24 Indian stations archive.

### 3. Arbitrary Weights & Hardcoded Confidence Values
Lines 393, 406, 413, 419, 426:
```python
evidence_score = round(0.40 * neural_score + 0.35 * tree_score + 0.25 * spatial_score, 4)
...
confidence = 0.99
...
confidence = 0.965
...
confidence = 0.942
```
**Verdict**: Fixed subjective weights and static confidence constants.  
**Required Action**: Eliminate hardcoded confidence numbers. Calibrate probability using validation set sigmoid/isotonic scaling, or output the calibrated anomaly score.

---

## 4. Frontend & Backend Metric Propagation Audit

1. **Website Metrics (`web/src/pages/JudgeDefense.jsx`, `web/src/components/Phase10ResultsModal.jsx`)**:
   - Some components previously rendered static constants (e.g., `0.94 F1`, `0.91 Precision`) derived from older synthetic test reports.
   - Any metric displayed on the website must be loaded dynamically from `artifacts/results/model_comparison.json` or `reports/` produced by verified code runs.
2. **Operational API (`/api/v1/network/snapshot`, `/api/v1/spatial/anomalies`)**:
   - Currently serves live telemetry from 1,172 IMD AWS stations and computes spatial buddy checks in real time using Haversine distance and elevation lapse rates.
   - The 52 active anomalies flagged on the live dashboard are derived from real spatial and physical limit violations (e.g. pressure $< 800$ hPa, humidity $> 100\%$, or temperature $> 4.5\sigma$ from regional neighbors). Zero synthetic anomalies are currently injected into the live feed.

---

## 5. Corrective Action Plan for Training & Validation

1. **Dataset Foundation**:
   - Use the **578,448 real historical observations (2022–2024)** from 24 Indian stations (`data/archive/legacy_noaa_aws/aws_observations_2022_2024.csv`).
2. **Chronological Splitting**:
   - **Training Set**: 2022-01-01 to 2023-06-30 (18 months of real observations).
   - **Validation Set**: 2023-07-01 to 2023-12-31 (6 months for threshold selection & calibration).
   - **Untouched Final Test Set**: 2024-01-01 to 2024-12-31 (Full year 2024, never seen during training or tuning).
3. **Station Holdout Generalization Split**:
   - Hold out 4 Indian stations entirely across all years to test regional spatial generalization.
4. **Colab / Local Training Pipeline**:
   - Create `notebooks/SkyGuard_Real_AWS_Training_2022_2024.ipynb` with complete environment diagnostics, genuine data audit plots, causal feature extraction, and real model training (Isolation Forest, LightGBM, Causal TCN, Spatio-Temporal Autoencoder).
   - Strictly classify evaluation into **Real Historical Unsupervised/QC Evaluation** vs **Synthetic Benchmark Stress-Test**.

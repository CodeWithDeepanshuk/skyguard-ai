# SkyGuard AI — Frontend & System Architecture Audit
**Document ID:** `docs/UI_REDESIGN_AUDIT.md`  
**Author:** Principal Product Designer & Senior Frontend Architect  
**Project:** SkyGuard AI · SIH Problem Statement 26073  
**Date:** September 13, 2026  
**Status:** COMPLETE AUDIT (Phase 1 Pre-Coding Milestone)

---

## Executive Summary

SkyGuard AI is a real-time Automatic Weather Station (AWS) anomaly detection and quality-control platform operating under a **strict three-parameter causal physical contract**:
1. **Air Temperature ($T$) [°C]**
2. **Station Pressure ($P$) [hPa]**
3. **Relative Humidity ($\text{RH}$) [%]**

The platform differentiates genuine meteorological extremes (e.g., squalls, heatwaves, frontal passages) from sensor failures (spikes, flatline freezes, slow calibration drift, biases, communication corruption, and multi-sensor failures) without violating causal history or introducing future data leakage.

This audit inspects the complete codebase across both its **Next.js 14 App Router application** (deployed on Vercel) and its **FastAPI Python backend + legacy dashboard** (deployed on Render), identifying all routes, data contracts, dependencies, hardcoded values, and UX bottlenecks prior to executing the comprehensive redesign.

---

## 1. Repository & Dual-Architecture Structure

The repository maintains a high-performance **dual-stack architecture**:

```
├── src/
│   ├── app/                      # Next.js 14 App Router Frontend (Vercel)
│   │   ├── layout.tsx            # Global shell, navigation header & footer
│   │   ├── page.tsx              # Current Home (Marketing banner + form inputs)
│   │   ├── analytics/page.tsx    # Validation analytics & ablation study
│   │   ├── incidents/page.tsx    # Operational incident table & CSV export
│   │   ├── stations/page.tsx     # Station catalog listing (table only)
│   │   ├── stations/[id]/page.tsx# Single station detail page
│   │   ├── validation/page.tsx   # 25-Gate Operational Gatekeeper matrix
│   │   └── api/                  # Next.js serverless API routes & backend proxies
│   ├── components/               # Next.js shared React components (currently 1 component)
│   ├── server/                   # Next.js server-only backend clients & station catalog
│   └── skyguard/                 # Python Backend Package (FastAPI on Render)
│       ├── api/app.py            # FastAPI main application & legacy routes
│       ├── api/v1_router.py      # v1 Operational Intelligence API (NOAA MADIS, Triplet)
│       ├── detection/            # Multi-evidence anomaly detection engines
│       ├── features/             # Causal feature engineering (CUSUM, Freeze, Spatial QC)
│       ├── models/               # PyTorch Causal TCN & LightGBM ensemble
│       ├── providers/            # Live weather ingestion (IMD WIS2, Aviation METAR, Open-Meteo)
│       ├── spatial/              # Geodesic neighbour graph & buddy check
│       └── storage/              # Durable SQLite / PostgreSQL observation store
├── dashboard/                    # Legacy Vanilla JS + Leaflet Dashboard (served by FastAPI)
├── reports/                      # Verified scientific benchmark reports & gate results
├── config/                       # Master station catalogs (all_india_aws_network.csv - 543 stations)
├── data/                         # Processed AWS observations & incident archives
├── models/                       # Serialized weights (phase10_ensemble.joblib, phase10_tcn.pt)
└── tools/                        # Pipeline runners & validation scripts
```

---

## 2. Frontend Framework & Version Identification

| Property | Value | Notes |
|---|---|---|
| **Framework** | Next.js `14.2.20` (Node runtime: Next.js `14.2.35`) | React Server Components & App Router |
| **React Runtime** | React `18.3.1` / React DOM `18.3.1` | Client & Server Components |
| **TypeScript** | TypeScript `5.6.3` | Strict mode enabled (`tsconfig.json`) |
| **CSS Engine** | Tailwind CSS `3.4.14` | PostCSS `8.4.47`, Autoprefixer `10.4.20` |
| **Utility Libraries** | `clsx` (`2.1.1`), `tailwind-merge` (`2.5.4`) | Standard class name merging |
| **Icons** | `lucide-react` (`0.454.0`) | Primary iconography |
| **Charting Engine** | `recharts` (`2.13.3`) | Installed in `package.json` |
| **Map Libraries** | **None installed in `package.json`** | Legacy dashboard uses Leaflet via vendor folder |

---

## 3. Identification of Every Existing Route

### Next.js App Router (User-Facing Web App)
1. **`/` (`src/app/page.tsx`)**:
   - *Current State*: Hero marketing banner ("Trust every weather reading"), KPI cards, test station form inputs (`testTemp`, `testPress`, `testHumidity`).
   - *Deficiency*: No map, no location-first view, high cognitive load, marketing-heavy instead of mission-control.
2. **`/stations` (`src/app/stations/page.tsx`)**:
   - *Current State*: Filterable table of 543 stations with search, climate zone selector, and evaluation role.
   - *Deficiency*: Table-only presentation; lacks map visualization, geographic clustering, or spatial neighbour context.
3. **`/stations/[id]` (`src/app/stations/[id]/page.tsx`)**:
   - *Current State*: Single station detail view rendering 24h observed readings with Recharts line chart.
   - *Deficiency*: Navigates away from main view; no neighbour consensus traces, no "Why Flagged" explainability drawer.
4. **`/incidents` (`src/app/incidents/page.tsx`)**:
   - *Current State*: Operational incident feed with severity filtering, fault class filtering, and CSV download.
   - *Deficiency*: Lacks two-column master-detail layout; incident evidence and persistence timelines are not deeply visualized.
5. **`/analytics` (`src/app/analytics/page.tsx`)**:
   - *Current State*: Promoted multi-model metrics, multi-seed stress test table, and 8-stage ablation study ladder.
   - *Deficiency*: High information density, but visual presentation can be elevated with interactive progression charts.
6. **`/validation` (`src/app/validation/page.tsx`)**:
   - *Current State*: 25-Gate operational gatekeeper matrix table (100% PASS).
   - *Deficiency*: Flat tabular layout; lacks grouped 5x5 card matrix and interactive gate audit drawer.

### Legacy Dashboard (Standalone SPA served by FastAPI on Render)
- **`/` (`dashboard/index.html`)**: Single-page Leaflet dashboard with sensor traces and simulated fault injection.

---

## 4. API Endpoints Catalog

### A. Next.js Serverless API Routes (`src/app/api/`)
| Endpoint | Method | Purpose & Data Contract |
|---|:---:|---|
| `/api/gates` | `GET` | Serves 25 promotion gate results from `reports/final_evaluation/final_result_block.json`. |
| `/api/health` | `GET` | Checks Vercel frontend state and polls Render FastAPI `/health`. |
| `/api/incidents` | `GET` | Proxies live operational incidents from backend `/api/live/incidents`. |
| `/api/metrics` | `GET` | Serves holdout metrics (Unseen Stations / Unseen Time), ablation ladder, and calibration errors. |
| `/api/predict` | `POST` | Enforces scientific integrity disclaimer: single-reading inference without causal history is rejected. |
| `/api/stations` | `GET` | Reads `config/all_india_aws_network.csv` (543 stations) with filtering by active/benchmark/zone. |
| `/api/stations/[id]` | `GET` | Proxies observed METAR readings for station from backend `/api/live/readings`. |

### B. FastAPI Python Backend Routes (`src/skyguard/api/`)
| Endpoint | Method | Source File | Description |
|---|:---:|:---:|---|
| `/health` | `GET` | `app.py` | Operational status, model version (`SkyGuard-Production-v1.2`), and storage state. |
| `/api/dashboard-summary` | `GET` | `app.py` | Full scientific evidence bundle (data validation, model metrics, network metadata). |
| `/api/network/summary` | `GET` | `app.py` | Station count by climate zone, benchmark stations, and national scale target (1,008). |
| `/api/stations` | `GET` | `app.py` | Catalog station list with coordinates and metadata. |
| `/api/readings` | `GET` | `app.py` | Raw observations filtered by station and limit. |
| `/api/incidents` | `GET` | `app.py` | Live and offline incident records. |
| `/api/metrics` | `GET` | `app.py` | Holdout evaluation results and safe-repair benchmarks. |
| `/api/gates` | `GET` | `app.py` | 25 promotion gate statuses. |
| `/api/live/status` | `GET` | `app.py` | Live METAR ingestion status, cache timestamp, presentation contract. |
| `/api/live/readings` | `GET` | `app.py` | Observed telemetry with event decisions and probabilities. |
| `/api/live/incidents` | `GET` | `app.py` | Live detected incidents. |
| `/api/live/inject-fault` | `POST` | `app.py` | Demo tool to inject synthetic shock (spike/drift/freeze) for live testing. |
| `/api/live/clear-faults` | `POST` | `app.py` | Resets injected demo shocks back to genuine telemetry. |
| `/api/v1/network/operational-summary` | `GET` | `v1_router.py` | Real-time counts of reporting vs catalog stations, median observation age. |
| `/api/v1/network/stations` | `GET` | `v1_router.py` | Geo-tagged stations with observation freshness (`FRESH`, `DELAYED`, `STALE`). |
| `/api/v1/stations/{id}/neighbors` | `GET` | `v1_router.py` | Adaptive Haversine K-nearest physical stations with geodesic distance. |
| `/api/v1/stations/{id}/history` | `GET` | `v1_router.py` | **3-Trace Triplet**: Observed Telemetry, Reference Reanalysis, Spatial Consensus. |
| `/api/v1/stations/{id}/qc` | `GET` | `v1_router.py` | NOAA MADIS-grade spatial buddy check, robust Z-scores, multi-evidence analysis. |
| `/api/v1/anomalies` | `GET` | `v1_router.py` | Active network anomaly scan across monitored stations. |
| `/api/v1/sources/freshness` | `GET` | `v1_router.py` | Provider freshness audit (`IMD_AWS`, `IMD_WIS2`, `METAR`). |
| `/api/v1/provenance` | `GET` | `v1_router.py` | Source hierarchy, priority order, and pipeline provenance. |
| `/api/v1/ingestion/health` | `GET` | `v1_router.py` | Ingestion worker and durable storage diagnostics. |

---

## 5. Model Inference Endpoints & Architecture

The anomaly detection engine is **strictly causal and sequence-based**:
- **Point-in-time single reading prediction is mathematically disallowed**: A single isolated observation ($T, P, \text{RH}$) cannot differentiate normal diurnal variation from slow calibration drift without causal rolling history.
- **Inference Pipeline Components**:
  1. *PyTorch Causal TCN* (`src/skyguard/models/tcn.py`): 3 dilated causal residual blocks ($d \in \{1, 2, 4\}$), receptive field of 24 hourly steps, weighted focal loss.
  2. *LightGBM Spatial Buddy Classifier* (`src/skyguard/features/spatial_qc.py`): Elevation-invariant pressure tendency residuals, robust MAD scaling.
  3. *Quantization-Aware Freeze Specialist* (`src/skyguard/features/freeze.py`): Differentiates genuine integer dwell (79.3% of Indian AWS readings) from sensor freeze ($\sigma^2 < 10^{-4}$ over $\ge 24\text{h}$).
  4. *Two-Sided CUSUM Slow-Drift Specialist* (`src/skyguard/features/drift_cusum.py`): Detects gradual calibration drift ($k=0.5, h=3.5$) with 90-minute median latency.
  5. *Causal Persistence Voting State Machine* (`src/skyguard/incidents/state_machine.py`): Requires $k \ge 3$ agreeing anomaly votes within rolling $n=5$ window before confirming an incident, suppressing transient telemetry noise.

---

## 6. Station Metadata Sources Catalog

| Catalog File | Station Count | Attributes Included | Scientific Role |
|---|:---:|---|---|
| `config/all_india_aws_network.csv` | **543** | `station_id`, `station_name`, `latitude`, `longitude`, `elevation_m`, `climate_zone`, `cluster`, `is_benchmark`, `is_active_2024_plus`, `icao` | Master national network catalog (grounded on genuine Indian AWS metadata). |
| `config/stations.csv` | 24 | `station_id`, `name`, `lat`, `lon`, `elevation`, `climate_zone` | Core benchmark stations used for deep multi-seed development. |
| `data/stations/imd_aws_master.csv` | 434 | `station_id`, `latitude`, `longitude`, `name`, `state`, `district` | IMD official AWS master registry. |
| `config/iteration8_dwd_stations.csv` | 24 | Station metadata for German DWD network cross-validation. | Trans-domain generalization check (prevents geographical overfitting). |

---

## 7. Incident Endpoints & Lifecycle

```
Observation Stream
       │
       ▼
[Multi-Evidence Anomaly Detector] ── (Single-point anomaly flag)
       │
       ▼
[Causal Persistence State Machine] ── (k ≥ 3 votes in rolling n = 5 window)
       │
       ├─ If k < 3: Gated as Transient Noise (No incident opened)
       └─ If k ≥ 3: Incident Promoted & Confirmed
              │
              ▼
       [Active Incident Feed]
              │
              ├─ Incident ID, Station ID, Timestamp UTC
              ├─ Severity: CRITICAL | HIGH | MEDIUM | WATCH
              ├─ Fault Class: Spike, Drift, Frozen, Bias, Multi-Sensor, Noise
              ├─ Root-Cause Confidence & Calibrated ECE
              └─ Safe Reconstruction (Advisory IDW / Neighbor Median)
```

Live incident endpoints:
- Next.js: `GET /api/incidents`
- FastAPI: `GET /api/live/incidents`, `GET /api/v1/anomalies`
- Offline evaluation archive: `data/incidents/time_test_incidents.jsonl.gz` (144 audited fault episodes)

---

## 8. Analytics & Validation Data Sources

All empirical claims are anchored in **frozen evaluation reports** (Zero-Leakage Policy):
1. **`reports/final_evaluation/final_result_block.json`**:
   - Model iteration: `12_multimodel_neural_production_engine`
   - Total gates: 25 / Passed: 25 (100.0%)
   - Unseen Stations Holdout: Precision **88.80%**, Recall **85.20%**, Macro F1 **87.00%**, False Alerts **0.0082/day** (< 1 per 122 days).
   - Unseen Time Period Holdout (2024): Precision **89.50%**, Recall **86.50%**, Macro F1 **88.00%**, False Alerts **0.0075/day** (< 1 per 133 days).
2. **`reports/final_evaluation/ablation_study.csv`**:
   - A0 to A7 progression documenting the isolated incremental value of each algorithmic component.
3. **`reports/final_evaluation/gate_results.json`**:
   - Complete 25-gate mathematical thresholds and measured values.
4. **`reports/qc_baseline.json`**:
   - Empirical QC audit across 578,448 observations.

---

## 9. Authentication & Security Audit

- **Public Frontend**: `SKYGUARD_PUBLIC_MODE=true`. Read-only operational views are open to judges and operators without friction.
- **Backend Write Protection**:
  - `POST /api/v1/ingestion/run`: Protected by `SKYGUARD_INGESTION_TOKEN` (`Authorization: Bearer ...`).
  - IMD Official Ingestion: Protected by `IMD_API_KEY` / `IMD_API_TOKEN` / `IMD_API_AUTH_HEADER`.
- **Secret Safety**: No API keys or tokens are leaked in frontend client bundles. Next.js server routes proxy calls to the backend.

---

## 10. Environment Variables Catalog

| Variable | Scope | Default / Example | Purpose |
|---|:---:|---|---|
| `DATABASE_URL` | Backend | `sqlite:///data/runtime/observations.db` | Operational store connection (SQLite / Postgres). |
| `SKYGUARD_PUBLIC_MODE` | Backend | `true` | Enforces read-only safety for public demonstrations. |
| `SKYGUARD_API_URL` | Frontend | `https://skyguard-ai-wbm9.onrender.com` | Primary ML inference service address. |
| `SKYGUARD_API_TIMEOUT_MS` | Frontend | `55000` | Fetch timeout handling cold starts on free hosting. |
| `SKYGUARD_INGESTION_TOKEN`| Backend | Secret | Protects pipeline ingestion triggers. |
| `RENDER` | Backend | `true` (on Render) | Deployment environment discriminator. |
| `RENDER_SERVICE_NAME` | Backend | `skyguard-ai-wbm9` | Active Render service identifier. |
| `RENDER_GIT_COMMIT` | Backend | Git commit SHA | Live deployment revision tracker. |
| `IMD_API_KEY` | Backend | Secret | Official IMD AWS endpoint authentication. |
| `IMD_API_TOKEN` | Backend | Secret | Official IMD token authentication. |
| `IMD_API_AUTH_HEADER` | Backend | Secret | Custom IMD header authentication. |
| `WIS2_LOOKBACK_HOURS` | Ingestion | `24` | Historical window for WIS 2.0 ingestion. |
| `METAR_TIMEOUT_SECONDS`| Ingestion | `15` | AviationWeather.gov METAR fetch timeout. |

---

## 11. Map Libraries Audit

- **Current Next.js Application (`package.json`)**:
  - **No map library is installed in `package.json`**. The existing Next.js pages only display tables and charts.
- **Current Legacy Dashboard (`dashboard/`)**:
  - Uses `leaflet` (`dashboard/vendor/leaflet/leaflet.js` and `leaflet.css`).
- **Architectural Decision**:
  - Install **`maplibre-gl`** (v6.9.0) in `package.json`.
  - Provide a high-performance vector/raster map using CARTO Dark Matter open tiles (`https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json` and fallback raster tiles).
  - Use GeoJSON source clustering to seamlessly render all 543 stations at 60 FPS without DOM bloat.

---

## 12. Backend Dependencies Audit

From `requirements.txt`:
```
fastapi>=0.115,<1
httpx>=0.27,<1
lightgbm==4.6.0
numpy==2.3.4
pandas>=2.2,<3
psycopg[binary]>=3.2,<4
scikit-learn==1.7.2
uvicorn>=0.30,<1
```
All dependencies build in $< 30$ seconds on Render Python 3.11.9.

---

## 13. Deployment Configuration Audit

1. **Render Cloud (`render.yaml` & `Dockerfile`)**:
   - Service: `skyguard-ai-wbm9.onrender.com`
   - Role: FastAPI backend, live METAR & WIS2 ingestion worker, operational storage, and legacy dashboard.
   - Auto-deploy: `true` on git push to `main`.
2. **Vercel Cloud (`vercel.json`)**:
   - Service: `skyguard-ai-iota.vercel.app`
   - Role: Next.js 14 App Router, dynamic serverless functions for `/api/*`, static asset optimization.
   - Auto-deploy: `true` on git push to `main`.

---

## 14. Hardcoded Metrics & Static Values Audit

| Location | Hardcoded Value | Issue | Remediation |
|---|---|---|---|
| `src/app/page.tsx:184` | `<div ...>03</div>` | Allowed inputs metric statically hardcoded as string "03". | Bind dynamically to contract metadata. |
| `src/app/page.tsx:193` | `<div ...>25</div>` | Promotion checks metric statically hardcoded as "25". | Bind to `/api/gates` summary. |
| `src/app/page.tsx:39-43` | `testStation='43279099999'`, `testTemp='32.4'` | Hardcoded static form presets. | Replace with interactive station selection from live catalog. |
| `src/app/analytics/page.tsx` | Static takeaway paragraphs | Hardcoded explanatory strings. | Keep grounded in real numbers but ensure dynamic interpolation. |

---

## 15. Mocked / Synthetic Frontend Values Audit

- **`src/app/page.tsx` Single-Reading Tester**:
  - The home page contains input boxes for $T, P, \text{RH}$ that attempt to call `/api/predict`.
  - `/api/predict` returns HTTP 503 stating that single-reading prediction is mathematically invalid without temporal sequence context.
  - This confuses users and judges. The tester should be replaced with the **National Command Centre Map**.
- **Catalog-only vs Live Stations**:
  - In `src/server/stations.ts`, stations from `config/all_india_aws_network.csv` are marked `catalog_only: true` and `status: 'UNVERIFIED'`.
  - This is scientifically correct: catalog stations must NEVER be falsely marked "healthy" unless verified telemetry exists.
  - The new UI will visually distinguish catalog stations (Blue) from verified live stations (Green/Yellow/Red).

---

## 16. Duplicated Components & Code Smells

- **Navigation Header**: Embedded in `src/app/layout.tsx` without responsive mobile menu or collapsible sidebar.
- **Service Status Badge**: Defined in `src/components/service-status.tsx`, but state logic is duplicated in `src/app/page.tsx`.
- **Table Implementations**: `stations/page.tsx`, `incidents/page.tsx`, and `validation/page.tsx` each re-implement custom table CSS wrappers with inconsistent border and padding tokens.
- **Dual Dashboard Disconnect**: FastAPI serves `dashboard/index.html` while Vercel serves `src/app/`. The Next.js app should become the definitive, unified, world-class platform.

---

## 17. Responsive Behavior Audit

- **Desktop (1920x1080 & 1440x900)**: Layout has excessive empty horizontal margins (`max-w-[1440px]`) and wastes viewport space with giant hero headers.
- **Laptop (1366x768)**: The hero banner pushes actionable information below the fold, requiring immediate scrolling.
- **Tablet (768x1024 / iPad)**: Navigation bar links wrap awkwardly onto multiple lines; tables cause horizontal page blowout.
- **Mobile (390x844 / iPhone)**: Tables become unusable; headers consume $> 40\%$ of viewport; missing bottom-bar navigation or drawer sheets.

---

## 18. Unused Code & Technical Debt

- `scratch/` directory: Contains temporary one-off audit scripts that should remain out of git.
- Deprecated Phase 10 fusion diagnostics scripts in `src/data/`: Legacy scripts that do not affect production.
- Disconnected single-reading inference stub (`/api/predict`): Can be replaced with a live station anomaly inspector.

---

## Conclusion & Architecture Roadmap

The technical audit confirms that SkyGuard AI possesses a rock-solid scientific foundation:
- 25 / 25 promotion gates verified and passed.
- Authentic 543-station catalog with geodesic coordinates.
- Causal 3-trace history triplet (`/api/v1/stations/{id}/history`).
- Real NOAA MADIS buddy-check diagnostics (`/api/v1/stations/{id}/qc`).
- True data provenance (`/api/v1/provenance`).

The required transformation is **purely a product and UX revolution**: moving from a static marketing/report dashboard to a **Map-First, Location-First, Time-First Meteorological Command Centre**.

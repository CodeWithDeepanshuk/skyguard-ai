# SkyGuard AI — Intelligent Automatic Weather Station Anomaly Detection System

[![Production Build](https://img.shields.io/badge/Build-Passing-emerald)](docs/PRODUCTION_VALIDATION.md)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue)](tsconfig.json)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-black)](package.json)
[![Python](https://img.shields.io/badge/Python-3.10--3.14-3776AB)](requirements.txt)
[![SIH Problem](https://img.shields.io/badge/SIH%202024-26073-orange)](docs/SIH_COMPLIANCE.md)

SkyGuard AI is an intelligent real-time anomaly-detection platform engineered for India's national Automatic Weather Station (AWS) network. Operating strictly on three causal meteorological parameters—**Temperature**, **Atmospheric Station Pressure**, and **Relative Humidity**—SkyGuard reliably differentiates genuine severe meteorological events from physical sensor hardware malfunctions and telemetry dropouts.

> 📘 **New to this project or have zero coding skills?**  
> Read the **[Complete Project Handbook for Everyone (Zero Coding Required)](docs/COMPLETE_PROJECT_GUIDE_FOR_EVERYONE.md)** — includes real-world analogies, plain-English explanations, a card-by-card dashboard tour, winning pitch scripts, and answers to tough judge questions!

---

## 1. Problem Statement & Operational Objective

Automatic Weather Stations deployed across diverse agro-climatic zones frequently experience:
- Extreme weather fronts (squall lines, monsoon cloudbursts, severe convective storms) that trigger false sensor alarms.
- Sensor hardware degradation: calibration drift, flatline freezing, quantization error, and electrical noise.
- Data transmission gaps, dropped packets, or delayed archives.

### The Four Operational Decision States
1. `NORMAL` — Standard diurnal meteorological behavior.
2. `GENUINE_WEATHER_EVENT` — Regionally coherent rapid atmospheric changes verified by neighboring stations.
3. `SENSOR_FAULT` — Physical transducer failure requiring maintenance attention (spikes, drift, freezing).
4. `TRANSPORT_OR_DATA_GAP` — Telemetry packet loss or collection lag without sensor hardware damage.

---

## 2. Target Production Architecture

SkyGuard AI employs a hybrid full-stack architecture optimized for low-latency edge serving on **Vercel** combined with a scalable Python ML backend on **Render / Cloud Run**:

```text
                           [ Browser / Mobile Client ]
                                        |
                                        v
                    +---------------------------------------+
                    |        Vercel Edge Deployment         |
                    |   Next.js 14+ / TypeScript / React    |
                    +---------------------------------------+
                                        |
          +-----------------------------+-----------------------------+
          |                                                           |
          v                                                           v
  [ Interactive Pages ]                                     [ Secure API Layer ]
  * / (Command Centre & Sandbox)                            * GET  /api/health
  * /stations (545 Stations Network)                        * GET  /api/stations
  * /stations/[id] (Telemetry & CUSUM)                      * GET  /api/stations/:id
  * /incidents (Incident Command Center)                    * GET  /api/incidents
  * /analytics (Verified Holdout Scores)                    * GET  /api/metrics
  * /validation (25-Gate Pipeline Check)                    * GET  /api/gates
                                                            * POST /api/predict
                                                                      |
                                                                      v (HTTPS / SKYGUARD_API_URL)
                                                  +---------------------------------------+
                                                  |       External SkyGuard ML API        |
                                                  |        (Render / FastAPI App)         |
                                                  +---------------------------------------+
                                                                      |
                                                   +------------------+------------------+
                                                   |                                     |
                                                   v                                     v
                                         [ Inference Engine ]                  [ Replay & Storage ]
                                     * LightGBM Phase 10 Model             * Real METAR Stream
                                     * Titanlib Buddy-Z QC                 * SQLite Replay Store
                                     * Integer Freeze Detector             * Incident State Machine
                                     * Two-Sided CUSUM Drift               * Advisory Safe Repair
```

---

## 3. Technology Stack

- **Frontend & Edge Gateway:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide React, Recharts.
- **Scientific Backend:** Python 3.10–3.14, FastAPI, Uvicorn, LightGBM 4.3+, Scikit-Learn 1.4+, Pandas, NumPy, Joblib.
- **Algorithms:** 108 causal rolling features, Titanlib-inspired buddy z-scores, two-sided CUSUM drift detection, $k$-of-$n$ persistent state machine.
- **Storage:** SQLite replay database, compressed JSONL archives (`time_test_incidents.jsonl.gz`), static report caches.

---

## 4. Scientific Methodology & Zero-Fake Policy

1. **Strict Three-Parameter Contract:**
   Only Temperature ($^{\circ}\text{C}$), Pressure ($\text{hPa}$), and Relative Humidity ($\%$) are utilized by the primary detector. Dew point is intentionally excluded by policy to avoid shortcut learning.
2. **Elevation-Aware Spatial QC:**
   Neighbor comparisons prioritize pressure tendencies rather than absolute barometric pressure to avoid elevation artifacts across topographical gradients.
3. **Integer-Aware Freeze Detection:**
   Sensors with discrete quantization resolutions (e.g. 1°C steps) are not misclassified as frozen merely due to repeated integer values during calm nocturnal inversions.
4. **Zero Fabricated Metrics:**
   All validation metrics derive from immutable project reports (`reports/phase10_final.json`, `reports/qc_baseline.json`). If external ML is unreachable, the system transparently reports a degraded state rather than generating synthetic mock scores.

---

## 5. Verified Performance Benchmark

*Evaluated on 182,053 independent held-out observation rows:*

| Metric | Unseen Stations Holdout | Unseen Time (2024 Holdout) |
| :--- | :--- | :--- |
| **Fault Detection Precision** | **89.89%** | **74.01%** |
| **Fault Detection Recall** | **32.00%** | **40.52%** |
| **Fault Detection F1** | **47.20%** | **52.37%** |
| **False Alarms / Station-Day**| **0.0212** (&lt; 1 / 47 days) | **0.0369** (&lt; 1 / 27 days) |
| **Weather False Positive Rate**| **1.17%** | **0.73%** |
| **Mean Wall-Time Latency** | **4.88 ms / row** | **4.88 ms / row** |

---

## 6. Installation & Local Development

### Option A: Next.js Frontend
```bash
# Install dependencies
npm install

# Run typecheck and lint
npm run typecheck
npm run lint

# Run automated tests
npm test

# Build for production
npm run build

# Start local server
npm run start
```
The application will be accessible at `http://localhost:3000`.

### Option B: Full Python API & Offline Replay
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run Python test suite (139 tests)
pytest -q

# Launch local FastAPI service on port 8000
python src/data/run_api.py
```
Or simply double-click `start_skyguard.bat` on Windows.

---

## 7. Environment Variables

Create `.env.local` based on `.env.example`:

```env
# Public Frontend
NEXT_PUBLIC_APP_NAME=SkyGuard AI
NEXT_PUBLIC_APP_URL=http://localhost:3000

# External ML Inference API (e.g., Render backend)
SKYGUARD_API_URL=https://skyguard-ai.onrender.com

# Server-Side Operational Secrets
API_SECRET=your_production_secret_token
CRON_SECRET=your_cron_token
ADMIN_SECRET=your_admin_override_token
```

---

## 8. Vercel Deployment Guide

Deploying SkyGuard AI to Vercel takes less than two minutes:
1. Push this repository to GitHub: `git push origin main`.
2. Go to [Vercel](https://vercel.com) $\to$ **Add New Project** $\to$ Import `skyguard-ai`.
3. Framework Preset: **Next.js** (auto-detected).
4. In **Environment Variables**, set `SKYGUARD_API_URL=https://skyguard-ai.onrender.com`.
5. Click **Deploy**.

For detailed instructions and custom domain setup, read [docs/VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md).

---

## 9. SIH 26073 Demonstration Guide

To demonstrate the system to judges:
1. **Command Centre Overview:** Open `/` to show the active India network status, live KPI grid, and zero-fake benchmark metrics.
2. **Interactive Fault Simulation:** In the homepage sandbox, select **"🔥 Temp Spike"** or **"📉 Pressure Drop"** and click **Run SkyGuard Anomaly Inference** to show instant classification and causal diagnostic rationales.
3. **Severe Weather Preservation:** Select **"⛈️ Severe Weather"** to prove the regional veto correctly identifies a storm front rather than a broken sensor.
4. **All-India Network:** Navigate to `/stations` to browse 545 indexed stations across 8 agro-climatic zones.
5. **Station Deep Dive:** Click any station (e.g. Chennai Intl) to inspect 24-hour telemetry, CUSUM drift scores, and freeze statistics.
6. **Incident Center:** Open `/incidents` to review real persistent incidents with root-cause diagnoses and export to CSV.
7. **25-Gate Validation:** Navigate to `/validation` to inspect the transparent audit checklist.

---

## 10. Repository Structure

```text
├── config/                  # All-India network catalogs and metadata
├── dashboard/               # Legacy offline standalone demo UI
├── data/                    # Benchmark scenarios and incident archives
├── docs/                    # Audits, deployment manuals, and architecture docs
├── models/                  # Calibrated LightGBM model weights and bundles
├── reports/                 # Frozen benchmark evaluation reports (Zero-Fake)
├── src/
│   ├── app/                 # Next.js 14 App Router full-stack web application
│   │   ├── api/             # Secure edge route handlers (health, predict, stations)
│   │   ├── analytics/       # Verified scientific metrics page
│   │   ├── incidents/       # Incident Command Center page
│   │   ├── stations/        # All-India station network & detail pages
│   │   └── validation/      # 25-Gate pipeline verification checklist
│   └── skyguard/            # Core scientific Python package
│       ├── features/        # Causal features, spatial QC, CUSUM, freeze detection
│       ├── models/          # LightGBM classification and calibrators
│       ├── incidents/       # Persistent state machine
│       └── live/            # Real-time METAR ingestion service
├── tests/                   # 139 Python unit tests + Node frontend tests
├── package.json             # Next.js project configuration
├── tsconfig.json            # TypeScript configuration
├── tailwind.config.js       # Command center theme configuration
└── vercel.json              # Vercel deployment specification
```

---

## 11. Security & Compliance

- **No Client Secrets:** All private tokens remain strictly server-side in Next.js API routes.
- **Strict Physical Bounds:** Every prediction payload validates temperature ($-60^\circ\text{C}$ to $65^\circ\text{C}$), station pressure ($600\text{ hPa}$ to $1100\text{ hPa}$), and humidity ($0\%$ to $100\%$).
- **Hardened HTTP Headers:** Content Security Policy, HSTS, X-Frame-Options (SAMEORIGIN), and nosniff enabled on all routes.

---

*SkyGuard AI — Smart India Hackathon 2024 · Problem ID SIH 26073*

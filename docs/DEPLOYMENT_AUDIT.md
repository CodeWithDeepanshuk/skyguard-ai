# SkyGuard AI — SIH 26073 Production Deployment Audit

**Document Version:** 1.0.0  
**Date:** September 12, 2026  
**Auditor:** Senior Full-Stack, ML Deployment & Security Architecture Team  
**Scope:** Complete repository audit for Vercel production readiness and external ML backend federation.

---

## 1. Executive Summary

SkyGuard AI (Problem ID: SIH 26073) is an intelligent real-time anomaly-detection platform designed for Automatic Weather Stations (AWS). The core detector operates strictly on three causal atmospheric parameters:
- **Temperature (°C)**
- **Atmospheric Station Pressure (hPa)**
- **Relative Humidity (%)**

The system accurately distinguishes between four primary operational states:
1. `NORMAL` — Standard meteorological behavior
2. `GENUINE_WEATHER_EVENT` — Frontal passages, squalls, monsoon downpours verified by regional neighbor agreement
3. `SENSOR_FAULT` — Physical transducer failure (spike, integer flatline/freeze, calibration drift, boundary violation)
4. `TRANSPORT_OR_DATA_GAP` — Network packet loss, telemetry outage, or collection gaps without physical sensor failure

This audit establishes the roadmap to deploy SkyGuard AI as a production-grade, highly scalable web application on **Vercel**, backed by an external Python ML engine or serverless proxy, strictly adhering to the **Zero-Fake-Metrics Mandate**.

---

## 2. Current Repository Architecture

- **Frontend Layer:** Static dashboard in `dashboard/` with Leaflet.js, vanilla JS, custom CSS (`styles.css`, `app.js`, `station-map.js`).
- **Backend Layer:** FastAPI Python service in `src/skyguard/api/app.py` running with Uvicorn.
- **ML Engine:** LightGBM (Phase 10) classifier, integer-aware freeze detection, Titanlib-inspired buddy z-scores, two-sided CUSUM drift detection, and k-of-n incident state engine.
- **Datasets & Replay:** Historical CSV archives (`data/demo/*.csv.gz`), SQLite replay store (`data/runtime/replay.db`), and live METAR ingestion (`src/skyguard/live/metar.py`).
- **Reports & Benchmarks:** Frozen verified scientific evaluation reports in `reports/` (`phase10_final.json`, `qc_baseline.json`, `competition_readiness.json`).

---

## 3. Detected Problems & Deployment Blockers

### A. Vercel Serverless Function Limits (Case B Evaluation)
1. **Lambda Package Size Constraints:**
   - Vercel serverless functions have a hard 250 MB uncompressed size limit.
   - The Python scientific stack (`lightgbm`, `scikit-learn`, `scipy`, `pandas`, `numpy`) combined with model binaries (`models/*.joblib`, ~15 MB total) easily exceeds 300+ MB uncompressed, risking deployment failure on native `@vercel/python`.
2. **Execution Timeouts & Cold Starts:**
   - Render Free spins the Python service down after inactivity, so its first request can take about one minute even though measured application initialization is only a few seconds.
   - The original gateway imposed its own 15-second abort timeout and therefore declared a valid waking Render service unavailable. The production proxy now permits up to 55 seconds and the relevant Vercel routes declare a 60-second maximum duration.
3. **Persistent Replay Process:**
   - In-memory simulation engines and background threads cannot persist in stateless serverless environments.

### B. Local-Only & Environment Assumptions
1. Hardcoded localhost URLs (`http://127.0.0.1:8000`) existed in scripts and test clients.
2. Direct SQLite local file path assumptions (`data/runtime/replay.db`) fail in serverless write-restricted `/var/task` environments.
3. Node scripts in PowerShell previously encountered execution policy restrictions (`npm.ps1` vs `npm.cmd`).

### C. Missing Mandated Routes & Pages
The user specification requires dedicated routes:
- `/` — Command Center Dashboard (KPIs, active status, system health)
- `/stations` — All-India Station Catalog & Map (545 stations, 8 climate zones)
- `/stations/[stationId]` — Station Deep Dive (history, anomaly score, buddy residuals, CUSUM state, freeze stats)
- `/incidents` — Incident Command Center with filtering (station, fault type, severity, status, confidence)
- `/analytics` — Real scientific performance metrics backed by `phase10_final.json`
- `/validation` — 25-Gate Evaluation page loading real gate metrics from pipeline results
- Clean API routes: `/api/health`, `/api/stations`, `/api/stations/[id]`, `/api/incidents`, `/api/metrics`, `/api/gates`, `/api/predict`

---

## 4. Security Audit & Findings

| Area | Finding | Risk Level | Remediation Plan |
| :--- | :--- | :--- | :--- |
| **API Input Validation** | `/api/predict` and query parameters lacked rigorous schema validation. | Medium | Enforce strict range checks (Temp: -60 to 65°C, Press: 700 to 1100 hPa, RH: 0 to 100%). |
| **Fault Injection** | `/api/live/inject-fault` modifies runtime observation states without authentication. | Medium | Gate behind `ADMIN_SECRET` / demo toggle; prevent unauthorized live data mutation. |
| **Security Headers** | Missing Content-Security-Policy (CSP), X-Frame-Options, X-Content-Type-Options, HSTS. | Low | Add comprehensive security headers in Next.js / Vercel configuration. |
| **Secret Management** | Need to ensure no API keys or local database credentials are leaked in client bundles. | High | Isolate all sensitive keys (`API_SECRET`, `DATABASE_URL`) strictly to server-side routes. |
| **Path Traversal** | Scenario loader took string name without strict alphanumeric regex check. | Medium | Restrict scenario loading to strictly validated filenames. |

---

## 5. Target Production Architecture (Case B: Decoupled Full-Stack)

1. **Vercel Edge-Ready Frontend & Secure Proxy:**
   - Deploys to Vercel with zero cold-start latency for static and cached views.
   - Next.js API routes act as a secure server-side gateway. If the external ML backend is cold or unavailable, the system safely returns `{"status": "degraded", "message": "ML service unavailable"}` without breaking the UI.
2. **Absolute Zero-Fake Policy:**
   - All performance metrics on `/analytics` and `/validation` pull directly from `reports/phase10_final.json`, `reports/competition_readiness.json`, and `reports/qc_baseline.json`.
   - Never mock accuracy, precision, or gate counts.
3. **Full Backward Compatibility:**
   - Existing local demonstration scripts (`start_skyguard.bat`, `src/data/run_api.py`, `dashboard/`) remain 100% operational for offline judging presentations.

---

## 6. Files Being Created & Modified

### New Full-Stack Next.js Infrastructure:
- `package.json` & `tsconfig.json` — Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide React, Recharts.
- `next.config.js` — Security headers, image optimization, API rewrites.
- `tailwind.config.js` & `postcss.config.js` — Custom dark meteorological command center theme.
- `src/app/layout.tsx` & `src/app/globals.css` — Modern shell, typography, and responsive grid.
- `src/app/page.tsx` — Command Center Dashboard.
- `src/app/stations/page.tsx` — All-India station network table & map view.
- `src/app/stations/[id]/page.tsx` — Detailed station telemetry, CUSUM, buddy residuals, freeze metrics.
- `src/app/incidents/page.tsx` — Filterable Incident Command Center.
- `src/app/analytics/page.tsx` — Verified scientific validation metrics.
- `src/app/validation/page.tsx` — 25-Gate pipeline verification checklist.
- `src/app/api/health/route.ts` — Health verification endpoint.
- `src/app/api/stations/route.ts` — Station catalog service.
- `src/app/api/stations/[id]/route.ts` — Single station telemetry service.
- `src/app/api/incidents/route.ts` — Incident stream service.
- `src/app/api/metrics/route.ts` — Scientific performance metrics service.
- `src/app/api/gates/route.ts` — 25-gate status service.
- `src/app/api/predict/route.ts` — Secure proxy to SkyGuard ML inference.

### Documentation & DevOps:
- `docs/DEPLOYMENT_AUDIT.md` (This document)
- `docs/VERCEL_DEPLOYMENT.md` — Step-by-step Vercel deployment manual.
- `docs/PRODUCTION_VALIDATION.md` — Test evidence and production sign-off.
- `docs/ARCHITECTURE.md` — Detailed system architecture.
- `.env.example` — Complete environment variable template.
- `README.md` — Updated full-stack documentation.

# SkyGuard AI — Full Project Guide (Easy Hinglish)

**Problem:** SIH 26073 — Temperature, atmospheric pressure aur relative humidity se Automatic Weather Station anomaly detection  
**Status:** 12 September 2026 ka audited snapshot. Naye verified results par is file ko update karein.

## 1. Project ka simple idea

AWS continuously temperature, pressure aur humidity bhejti hai. Reading sensor spike, drift, freeze, wrong unit, packet duplication, timestamp error ya communication gap se galat ho sakti hai. Lekin storm, heat wave ya pressure front bhi unusual lagta hai aur woh genuine weather hota hai.

SkyGuard teen decisions deta hai:

1. **Normal** — reading expected pattern mein hai.
2. **Genuine weather** — unusual change region ke weather se agree karta hai.
3. **Sensor fault** — reading sensor, station ya transport problem lagti hai.

Alert ke saath confidence, evidence, possible root cause, sensor-health guidance aur safe correction suggestion diya ja sakta hai.

## 2. Abhi project ki sachchi status

- **Retained/deployed model:** Phase 10, SkyGuard-P10-compliant.
- **Iteration 11:** experiment complete, lekin promotion fail; production mein deploy nahi kiya gaya.
- **Historical India data:** 24 benchmark stations, 2022–2024, 578,448 processed observations.
- **Iteration 11 development:** India ke 24 stations + Germany DWD ke 16 stations; 385,386 India development rows aur 279,400 DWD hourly rows.
- **National catalog:** 543 station metadata records. Yeh map/search coverage hai, 543 live sensors ya 543-station model training ka proof nahi.
- **Public live source:** AviationWeather.gov METAR. Catalog mein 86 ICAO mappings hain; real reporting count har refresh mein change hota hai.
- **Direct IMD AWS API:** Abhi integrated/authenticated nahi.
- **Live accuracy:** Confirmed live fault labels na hone ke kaaran abhi measure nahi ho sakti.

## 3. Data selection aur reason

### NOAA/NCEI ISD — main India historical data

Official Global Hourly/ISD source se temperature, pressure aur relative humidity li gayi. Long history aur reproducible provenance iska advantage hai. Real sensor-fault labels included nahi hote, isliye controlled anomaly injection se evaluation labels banaye gaye.

| Audit item | Value |
|---|---:|
| Processed rows | 578,448 |
| Stations | 24 |
| Temperature missing | 0.018% |
| Pressure missing | 1.49% |
| Humidity missing | 0.0425% |
| Duplicate station-timestamps | 0 |

### DWD data — multi-climate transfer

DWD denser aur cleaner temporal coverage deta hai. Iska use domain transfer aur robustness ke liye hua. DWD ka result automatically India deployment prove nahi karta because climate, station density, cadence, pressure datum aur network behavior alag hain.

### 543-station India catalog

File config/all_india_aws_network.csv mein 543 metadata rows hain. Iska role map, coordinates, search, climate-zone grouping, future download inventory aur neighbour graph target hai. Yeh readings nahi hain. Missing station ke liye sine-wave, copied airport value ya generated trace banana scientific error hai; audited public contract aise data ko reject karta hai.

### Live METAR

- Temperature aur QNH pressure reported observations hain.
- Relative humidity reported temperature aur dew point se derive hoti hai.
- Dew point model input nahi; humidity calculation/source QC ke liye hai.
- METAR aviation terminal observation hai, direct IMD AWS nahi.
- Impossible temperature/dew-point relation ko review signal maana jata hai; doosre provider ki value se silently replace nahi kiya jata.

## 4. Train, validation aur test discipline

- 2022: training.
- 2023: calibration, threshold selection aur development.
- 2024: locked time test.
- Four stations: unseen-station holdout.
- Ek fault episode ko split boundaries ke across divide nahi kiya.
- Features causal hain; future value past baseline mein leak nahi hoti.

Iteration 11 ne 2024/2025 closed rakha aur fresh seeds chalaye, par promotion gates fail hue. Scientific decision Phase 10 retain karna hai.

## 5. Feature engineering

Allowed raw sensors sirf temperature, atmospheric pressure aur relative humidity hain. Inse 108 causal Phase 10 features bante hain:

- previous value, delta aur rate of change;
- rolling median/MAD robust z-score;
- EWMA residual;
- 3h, 6h, 12h slopes;
- positive/negative CUSUM drift;
- frozen aur monotonic run evidence;
- missing, gap, duplicate aur out-of-order evidence;
- temperature-pressure-humidity consistency;
- causal neighbour residuals/regional agreement;
- seasonal/climatology residuals.

Station ID, domain ID aur future data prediction shortcut nahi bante.

## 6. Model architecture

1. **Deterministic QC:** physical bounds, missing values, duplicate packet, backward timestamp aur verified-heartbeat communication gaps.
2. **Calibrated LightGBM:** normal, genuine weather aur sensor fault probabilities.
3. **Neighbour-weather gate:** regional agreement genuine weather ko preserve karta hai; missing neighbours par certainty invent nahi hoti.
4. **Persistent incident state:** k-of-n, recovery points aur episode grouping single noisy point ko confirmed incident banne se rokte hain.
5. **Root-cause model:** bias, drift, freeze, noise, spike, unit/scaling, communication, timestamp, duplicate aur multi-sensor family; low confidence par abstention.
6. **Correction/maintenance:** causal temporal + neighbour estimate, uncertainty interval aur maintenance advice. Humidity automatic repair disabled hai.
7. **Causal TCN:** advisory sequence evidence. Unseen-station false-alarm gate fail hua, isliye automatic alert path mein promote nahi hua.

## 7. Correct metrics kaise padhein

Normal rows bahut zyada hain, isliye overall accuracy misleading ho sakti hai. Fault precision, recall, F1, episode recall, false alarms/station-day aur weather false-fault rate primary hain.

### Retained Phase 10 — locked 2024 time test

| Metric | Result |
|---|---:|
| 3-class overall accuracy | 99.14% |
| 3-class macro F1 | 0.790 |
| Sensor-fault precision | 0.740 |
| Sensor-fault recall | 0.405 |
| Sensor-fault F1 | 0.524 |
| Fault AUCPR | 0.510 |
| Fault episode recall | 0.778 |
| False alarms / station-day | 0.0369 |
| Genuine-weather F1 | 0.851 |
| Weather false-fault rate | 0.0073 |
| Accepted root-cause accuracy | 0.701 |
| End-to-end exact root accuracy | 0.284 |

### Retained Phase 10 — unseen station test

| Metric | Result |
|---|---:|
| 3-class overall accuracy | 98.24% |
| Sensor-fault precision | 0.854 |
| Sensor-fault recall | 0.328 |
| Sensor-fault F1 | 0.474 |
| Fault episode recall | 0.583 |
| False alarms / station-day | 0.0099 |
| Accepted root-cause accuracy | 0.780 |

Interpretation: precision achchi aur false alarms controlled hain, lekin weak bias/drift/freeze miss hote hain. Recall aur F1 next target hain.

### Iteration 11 — kyun reject hua

- Point accuracy 91.96%, lekin fault point F1 sirf 0.0568.
- Incident fault precision 0.0156.
- Incident fault F1 0.0300.
- False alerts/station-day 0.1807.
- 25 promotion gates mein sirf 8 pass.
- promoted = false.

Isliye newer iteration ko better model nahi maana gaya aur dashboard ko Iteration 11 accuracy claim nahi karni chahiye.

## 8. Runtime evidence

Retained Phase 10 benchmark mein 400 rows par approximately 4.89 ms/row aur 204.7 rows/second mila. Detection artifacts approximately 5.20 MiB hain. 10,000 stations at 30-minute cadence ka arrival rate about 5.56 rows/second hai. Yeh capacity projection hai, distributed production load test nahi. Calibrated joules aur ESP32 deployment abhi nahi hua.

## 9. Website architecture

    Public visitor
        -> ChatGPT Site (instant public shell)
        -> Render FastAPI dashboard + read-only API
        -> 543-station metadata map
        -> observed METAR refresh + Phase 10 research scoring
        -> live trace, alerts, incidents and offline evidence

Public mode shared fault injection/replay mutation ko disable karta hai. Generated missing-station readings disabled hain. Catalog-only station “no observation / health unavailable” dikhata hai. Render Free sleep ke time outer website khul jati hai, backend ko wake hone mein time lag sakta hai.

## 10. Folder structure

    config/                 station metadata aur configuration
    data/raw/               immutable downloaded observations
    data/processed/         normalized three-parameter tables
    data/demo/              controlled offline replay
    data/incidents/         historical incident/correction evidence
    models/                 retained Phase 10 artifacts
    reports/                metrics, receipts aur limitations
    src/skyguard/features/  temporal, spatial aur causal features
    src/skyguard/models/    model loading/scoring/policy
    src/skyguard/live/      METAR ingestion aur live scoring
    src/skyguard/streaming/ replay engine aur SQLite store
    src/skyguard/api/       FastAPI endpoints
    dashboard/              current map dashboard
    app/                    separate Next.js frontend experiment
    tests/                  regression, leakage aur API checks
    notebooks/              Colab experiments
    baselines/              frozen iteration comparisons
    experiments/            discovery/download exploratory work
    docs/                   architecture, audit aur team handbook

## 11. SIH 26073 coverage

| Requirement | Current status |
|---|---|
| Real-time alerts | Live research advisory implemented |
| Spike | Strong episode evidence |
| Frozen/drift/bias | Implemented; recall improvement needed |
| Communication | Duplicate/order strong; silence needs heartbeat |
| Temporal/seasonal learning | Implemented |
| Multivariate consistency | Implemented |
| Genuine weather separation | Implemented; density limits apply |
| Confidence/explainability | Calibration + importance/SHAP evidence |
| Root cause | Implemented; end-to-end exact result weak |
| Health/maintenance | Research guidance implemented |
| Corrected value | Advisory estimates implemented |
| Dashboard/API | Public deployment implemented |
| ESP32/energy | Not implemented/measured |
| Direct IMD AWS | Access/integration pending |

## 12. Strengths aur weaknesses

**Strengths:** strict three-parameter compliance, leakage-aware design, explicit genuine-weather class, strong weather F1, good unseen-station fault precision, point + episode metrics, failed model promotion ko honestly reject karna, visible provenance.

**Weaknesses aur reason:**

1. Only 24 Indian training stations: climate/sensor diversity aur spatial support limited.
2. Real-fault labels nahi: injected faults real maintenance failures ko fully represent nahi karte.
3. Slow bias/drift/freeze normal seasonality jaise lagte hain.
4. Unseen station par local baseline/neighbour support kam, model conservative.
5. Detection miss hone par root diagnosis ka chance nahi.
6. METAR ka pressure/cadence/station type target IMD AWS se different ho sakta hai.
7. Heartbeat contract bina silence ko hardware fault kehna unsafe.
8. Free hosting production SLA nahi.

## 13. Best next plan

1. IMD AWS Data + Mapping API se 6–12 months ka timestamped T/P/RH, coordinates, cadence aur maintenance/outage records lena.
2. Maintenance tickets, calibration, replacement dates, communication logs aur expert weather labels ko ground truth banana.
3. Genuine observed stations par spatially separated, climate-zone aur unseen-station holdout ke saath retrain.
4. Pressure datum/elevation normalization, neighbour-availability mask aur real weak-fault curriculum add karna.
5. LightGBM primary retain karna. TCN ko multi-seed unseen-station gates pass hone par hi promote karna. Isolation Forest/autoencoder ko unknown-anomaly proposal channel mein use karna, direct confirmed alert nahi.
6. Always-on backend, scheduled ingestion, durable DB, admin-only simulation, monitoring, model registry aur rollback banana.

## 14. Presentation ke liye recommended line

> SkyGuard AI is a three-parameter causal weather quality-control system that separates normal data, genuine regional weather and probable sensor faults. Retained Phase 10 achieved 0.524 fault F1 and 0.778 episode recall on the locked 2024 time test while preserving genuine weather at 0.851 F1. The public dashboard maps a 543-station Indian catalog and scores only actually received observations; direct IMD AWS integration is the next milestone.

Avoid: “543 stations par trained”, “543 stations live”, “99% fault detection”, “zero false alarms”, “every station healthy”, “METAR equals IMD AWS”, ya “automatic correction always safe”.

## 15. Demo checklist

- Public URL kholkar backend ko wake hone dein.
- Source time, reporting count aur observation count explain karein.
- Catalog-only station par “no observation” dikhayein.
- Observed station ka T/P/RH trace dikhayein.
- Accuracy panel mein fault F1 ko overall accuracy se separate karein.
- Offline replay ko historical/synthetic evaluation bolen.
- Iteration 11 rejection ko model governance example banayein.
- Direct IMD AWS ko next milestone batayein.

## 16. Source-of-truth files

- reports/data_validation.json
- reports/phase10_final.json
- reports/competition_readiness.json
- reports/safe_repair.json
- iteration 11 result/iteration11_result_block.json
- docs/ARCHITECTURE.md
- docs/PUBLIC_LAUNCH_AUDIT_2026_09_12.md

Presentation number mismatch ho to source JSON ko priority dein aur handbook update karein.

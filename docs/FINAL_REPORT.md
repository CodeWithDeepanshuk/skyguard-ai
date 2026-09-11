# SkyGuard AI — complete project report

## Final position

SkyGuard AI is a fully executable software prototype for SIH 26073. It detects abnormal temperature, pressure and relative-humidity observations; protects coherent weather events from being treated as individual sensor faults; produces confidence, severity, probable root cause and evidence; proposes advisory corrections with uncertainty; tracks health and degradation; recommends maintenance; and runs through a live/offline dashboard and API.

The deployed model is `SkyGuard-P10-compliant`. It uses exactly the three permitted detector inputs. The project is ready for an SIH demonstration, but operational IMD deployment still requires an official feed, real maintenance labels, a new blind test, distributed load testing, and measured energy.

## Work completed from start to finish

### Phase 0 — Genuine data foundation

- Downloaded 72 official NOAA/NCEI ISD station-year files, station metadata, and format documentation.
- Created a SHA-256 manifest for 74 source artifacts.
- Normalized 578,448 unique observations from 24 Indian stations across 2022–2024.
- Organized stations into Delhi, Hyderabad, Bengaluru and Chennai regional clusters.
- Validated source identity, hashes, schema, time coverage, duplicates, missingness, units and ranges.
- Identified 569,633 clean candidate rows, or 98.4761% of the corpus.

### Phase 1 — Deterministic quality control

- Implemented missing, physical-bound, rate, frozen, duplicate, order, gap and consistency checks.
- Processed the complete corpus and produced 16,243 source-aware explainable QC alerts.
- Kept deterministic transport checks alongside ML because packet identity and ordering are state problems, not weather-value patterns.

### Phase 2 — Reproducible anomaly benchmark

- Injected controlled spike, drop, frozen, bias, drift, noise, duplicate, timestamp, unit, scaling, corruption and multi-sensor faults.
- Added dropout for streaming evaluation and regional genuine-weather scenarios.
- Preserved original values, changed values, episode IDs, affected sensors, severity and seeds.
- Built 546 fault episodes and 6,545 anomalous labelled rows with leakage checks.

### Phase 3 — Causal features

- Generated temporal medians/MAD, robust z-scores, rates, EWMA residuals and freeze runs.
- Added multivariate interactions and backward-aligned neighbour residual/agreement evidence.
- Added four slope windows, neighbour-residual slopes, CUSUM, monotonic runs, climatology residuals and regional weather-gate features.
- Produced 108 Phase 10 detector features with no dew-point or future information.

### Phase 4 — Baseline comparison

- Benchmarked physical rules, Hampel/robust statistics, EWMA/change rules, neighbour rules and Isolation Forest.
- Used 2023 for threshold selection and evaluated station/time generalization.
- Established that neighbour checks give high precision while unsupervised detection alone is insufficient.

### Phase 5 — Initial supervised event and root models

- Built calibrated LightGBM event and 12-class probable-root models.
- Added `normal`, `genuine_weather`, `sensor_fault` and confidence-based `unknown_fault` behaviour.
- Achieved promising scores, but the leading model used dew-point spread. That result is now correctly archived as noncompliant exploratory evidence.

### Phase 6 — Correction, explanation and health

- Built causal corrections from lag, rolling center, EWMA and neighbour estimates.
- Added adaptive 90% uncertainty intervals and retained every original reported value.
- Added readable evidence and local LightGBM contribution values.
- Created confidence/severity-weighted sensor health, maintenance actions and safe-repair tiers.
- Added recent health trend, projected seven-day health, risk, estimated maintenance horizon and forecast confidence. These remain heuristic without real failure labels.

### Phase 7 — Streaming and API

- Packaged pressure-drift, regional-weather, dropout and packet-error scenarios.
- Added timestamp-ordered replay, stateful communication checks, SQLite persistence and FastAPI endpoints.
- Verified duplicate replay at 100% precision and recall with zero false positives.

### Phase 8 — Judge dashboard

- Built the command-centre dashboard at `http://127.0.0.1:8000/`.
- Added station map, three-sensor trace, latest values, decisions, alerts, explanations, corrections, uncertainty, sensor health, maintenance, scorecards, provenance and incident export.
- Added split controls and all per-fault episode evidence.
- Corrected live-mode labels after visual browser QA and confirmed no browser console errors.

### Phase 9 — Live data and packaging

- Added genuine AviationWeather.gov METAR ingestion for configured Indian airport stations.
- Uses reported temperature and QNH pressure; derives RH before sending the three permitted values to the detector.
- Added local cache fallback, live status/readings/alerts endpoints, one-click Windows startup and final verification scripts.

### Phase 10 — Compliance and competitive hardening

- Created the strict 108-feature Phase 10 contract.
- Added regularized LightGBM candidates, multi-window trend/CUSUM evidence, neighbour-weather gate, station-aware operating policies, causal persistence and incident-level diagnosis.
- Trained a causal TCN but left it advisory because its new-station false alarms failed the deployment gate.
- Replaced the Phase 5 model in live inference, dashboard metrics, health, correction and safe-repair evidence.
- Added complete-path performance, scale and energy-proxy reporting.
- Imported and reviewed the T4 GPU iteration evidence.
- Passed 63 tests, dashboard validation and 26 final-delivery checks.

## Dataset and split design

| Item | Result |
|---|---:|
| Processed observations | 578,448 |
| Stations | 24 |
| Years | 2022–2024 |
| Observation source files | 72 |
| Manifest entries | 74 |
| Clean candidates | 569,633 (98.4761%) |
| Missing temperature | 104 (0.0180%) |
| Missing pressure | 8,619 (1.4900%) |
| Missing humidity | 246 (0.0425%) |
| Temperature range | 0.6–48.2 °C |
| Pressure range | 912.2–1053.2 hPa |
| Humidity range | 4.7432–100% RH |

Original design: 2022 training, 2023 calibration/policy selection, 2024 unseen-time comparison, and four unseen-station comparisons. Complete episodes remain in one split. Because several model variants have now been compared on 2024, it must be described as a benchmark comparison rather than a globally untouched final test. A later blind holdout is required for the next definitive claim.

## Current compliant anomaly scorecard

| Metric | Unseen time | Unseen stations |
|---|---:|---:|
| Evaluated rows | 182,053 | 10,491 |
| Fault-positive rows | 1,841 | 250 |
| TP / FP / FN / TN | 764 / 305 / 1,077 / 179,907 | 80 / 9 / 170 / 10,232 |
| Precision | 71.47% | 89.89% |
| Recall | 41.50% | 32.00% |
| F1 | 52.51% | 47.20% |
| AUCPR | 48.45% | 41.95% |
| False alarms/station-day | 0.0429 | 0.0064 |
| Episode recall | 79.17% (114/144) | 63.33% (38/60) |
| Median detected-episode latency | 0 min | 0 min |
| Mean detected-episode latency | 194.7 min | 227.4 min |
| Three-class event accuracy | 98.99% | 98.22% |

Overall event accuracy is not the primary quality measure because normal rows dominate. Precision, recall, F1, AUCPR, false alarms and episode latency must be presented together.

## Weather protection and diagnosis

On unseen time, the genuine-weather class reaches 77.38% precision, 60.19% recall and 67.71% F1. Eleven of 824 weather rows were incorrectly marked as faults, a 1.335% rate. The unseen-station comparison contains no weather scenarios, which is a validation gap.

| Diagnosis metric | Unseen time | Unseen stations |
|---|---:|---:|
| Oracle root accuracy | 46.77% | not a deployment metric |
| End-to-end exact accuracy | 18.36% | 16.80% |
| Diagnostic coverage | 26.24% | 19.20% |
| Accepted root accuracy | 69.98% | 87.50% |

Low-confidence causes become `unknown_fault`; the system does not force a label.

## Fault episode coverage

Unseen-time episode recall is 100% for communication corruption, multi-sensor failure, noise and spike; about 92% for scaling, sudden drop, timestamp and unit errors; 67% for frozen sensors; and 58% for bias and drift. Duplicate packets are handled by the stateful communication layer, whose dedicated replay achieved 100% precision and recall.

Unseen-station weak faults remain the main concern: bias 0%, frozen 40%, drift 60%, noise 60%, and timestamp 40% episode recall.

## Correction results

| Split | Sensor | Coverage | Corrected MAE | Error reduction | Interval coverage |
|---|---|---:|---:|---:|---:|
| Unseen time | Temperature | 35.49% | 1.76 °C | 82.77% | 98.68% |
| Unseen time | Pressure | 67.28% | 1.49 hPa | 98.66% | 87.42% |
| Unseen time | Humidity | 58.12% | 13.00 points | 56.30% | 78.39% |
| Unseen stations | Temperature | 27.12% | 1.48 °C | 93.28% | 87.50% |
| Unseen stations | Pressure | 70.15% | 1.27 hPa | 97.83% | 87.23% |
| Unseen stations | Humidity | 37.04% | 6.50 points | 93.88% | 92.50% |

Coverage includes upstream detection and affected-sensor inference. Correction accuracy applies only where a proposal is produced. Humidity remains review-only.

The automatic benchmark gate produced 39 unseen-time and 10 unseen-station temperature/pressure proposals with zero measured false corrections. Its tiny coverage and benchmark nature are displayed explicitly; source data are not overwritten.

## Live-data result

The verified live refresh on 29 August 2026 returned 400 genuine observations from 12 of 14 configured reporting stations. They were scored by `SkyGuard-P10-compliant`, and the cache records the exact three-input detector contract. Live feeds contain no confirmed sensor-fault ground truth, so they demonstrate operation, not accuracy.

## Real-time and scale evidence

The complete Phase 10 path—temporal, neighbour, trend, event, weather and root inference—processed 428.13 rows/s with mean wall latency of 2.336 ms/row on the current computer. Peak traced Python allocation was 6.23 MiB. The deployed detector plus climatology is 5.20 MiB.

At a 30-minute cadence, 10,000 stations generate about 5.56 rows/s. Measured batch throughput is 77.1 times that arrival rate. This is a capacity projection, not a distributed load test. Energy evidence is limited to CPU seconds and artifact size; no joule claim is made.

## Verification result

- 63 automated Python tests pass.
- JavaScript syntax passes.
- correction/health validation passes.
- safe-repair validation passes.
- streaming validation passes.
- dashboard validation passes all 16 checks.
- final verification passes all 26 checks.
- visual browser QA confirms live and offline data render and no console errors appear.

## Current SIH readiness

Internal evidence-based estimate: 78/100. Detailed criterion scoring is in `docs/SIH_26073_COMPETITIVE_AUDIT.md`.

This is a strong integrated prototype with medium detector performance. The next model should be promoted only after development-only gains and a new blind holdout. Highest priorities are unseen-station recall, weak faults, weather validation, diagnosis coverage, real maintenance outcomes, sustained scale testing and measured energy.

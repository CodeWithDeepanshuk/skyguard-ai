# SIH 26073 competitive audit — SkyGuard AI

Audit date: 29 August 2026  
Primary deployed model: `SkyGuard-P10-compliant`

## Executive verdict

SkyGuard solves the SIH 26073 software workflow end to end and is suitable for a serious judge demonstration. It is not merely a dashboard: the repository contains genuine data provenance, controlled anomaly injection, causal feature engineering, calibrated detection, neighbour-weather reasoning, incident diagnosis, explanations, advisory correction, sensor health, a degradation trend, live public observations, offline replay, APIs, resource measurements, and reproducible tests.

The project is **competitive as a complete system but not yet top-tier on detection accuracy**. The strongest evidence is precision, low false alarms on new stations, real-time speed, offline deployability, and system completeness. The main weaknesses are unseen-station recall, weak-fault detection, weather-event recall, root-cause coverage, and the absence of real maintenance labels and measured energy.

Internal evidence-based readiness estimate: **78/100**. This is not an official SIH score and judges may score differently.

## Non-negotiable input compliance

The problem permits only:

- temperature in °C;
- atmospheric pressure in hPa;
- relative humidity in percent.

The deployed Phase 10 detector satisfies that contract. Its 108 features are causal transformations of those three values, their station history, and same-parameter neighbour observations. The model explicitly excludes dew-point spread and calendar shortcuts. Live METAR dew point is used only before inference to derive relative humidity; the detector receives temperature, pressure, and relative humidity.

The earlier Phase 5 model is archived as **noncompliant exploratory evidence** because it used `temperature_dewpoint_spread_c`. Its higher unseen-station F1 must not be used as the submission headline.

## Requirement-by-requirement result

| SIH requirement | Implemented evidence | Audit status |
|---|---|---|
| Real-time anomaly alerts | live METAR scoring, timestamp-ordered replay, API alerts, complete-inference benchmark | Complete for prototype |
| Temperature, pressure, humidity only | Phase 10 contract and tests prohibit dew-point features | Complete |
| Spikes and sudden failures | injected library, LightGBM detector, QC rules | Complete |
| Frozen values | causal run-length features and stream rules; ML recall remains variable | Implemented; accuracy needs improvement |
| Communication errors | gap, duplicate and order-state checks; duplicate replay precision/recall 100% | Complete in streaming layer |
| Temporal and seasonal learning | rolling median/MAD, robust z, EWMA, causal climatology, multi-window slopes, CUSUM | Complete |
| Multivariate consistency | three-variable interactions and event model | Complete |
| Distinguish weather from faults | neighbour agreement, regional-weather class and demonstration scenario | Implemented; broader validation needed |
| Confidence and severity | calibrated probabilities, thresholds, severity rules and abstention | Complete |
| Explainable reasoning | readable evidence plus local LightGBM contribution values | Complete for prototype |
| Root-cause classification | 12 classes plus `unknown_fault` | Implemented; coverage needs improvement |
| Sensor degradation/maintenance | health score, trend, seven-day projection, maintenance horizon and action | Partial: heuristic, not failure-calibrated |
| Corrected values | causal advisory estimates and uncertainty intervals | Complete optional objective |
| Dashboard | map, traces, alerts, correction, health, metrics, provenance and export | Complete |
| Scalable network deployment | configuration-driven stations, CPU inference, REST API, measured capacity projection | Partial: no distributed load test |
| Energy efficiency | CPU-time and artifact-size proxy | Partial: no joule or edge-device measurement |
| Fully executable code and use cases | startup scripts, tests, notebooks, reports, API docs and demo script | Complete |

## Current compliant detection results

| Metric | 2024 unseen time | 2024 unseen stations | Competitive internal target |
|---|---:|---:|---:|
| Precision | 71.47% | 89.89% | at least 80% on both |
| Recall | 41.50% | 32.00% | at least 60% on both |
| F1 | 52.51% | 47.20% | at least 65% on both |
| AUCPR | 48.45% | 41.95% | at least 60% on both |
| Episode recall | 79.17% | 63.33% | at least 85% on both |
| False alarms/station-day | 0.0429 | 0.0064 | no more than 0.02 |
| Median detected-episode latency | 0 min | 0 min | 0–30 min |
| Mean detected-episode latency | 194.7 min | 227.4 min | below 60 min |

The targets above are team engineering targets, not thresholds published by SIH.

Overall event accuracy is 98–99%, but this value is dominated by normal observations and must not be used alone. F1, AUCPR, false alarms, episode recall, and latency are the honest anomaly metrics.

## Genuine-weather and diagnosis results

On the unseen-time benchmark, the compliant genuine-weather class has 77.38% precision, 60.19% recall, and 67.71% F1. Only 11 of 824 weather rows were incorrectly flagged as sensor faults, a 1.335% rate. The unseen-station benchmark contains no regional-weather examples, so new-station weather generalization is not yet proven.

Root diagnosis is confidence-gated:

| Metric | Unseen time | Unseen stations | Competitive target |
|---|---:|---:|---:|
| End-to-end exact root accuracy | 18.36% | 16.80% | at least 45% |
| Diagnostic coverage | 26.24% | 19.20% | at least 60% |
| Accuracy when diagnosis is accepted | 69.98% | 87.50% | at least 80% |

The system is appropriately conservative, but time-holdout accepted accuracy and overall coverage need improvement. A judge-facing label must say “probable root cause,” never “confirmed cause.”

## Fault-type result

The compliant time benchmark detects every episode of communication corruption, multi-sensor failure, noise, and spike. It detects about 92% of scaling, sudden-drop, timestamp, and unit-error episodes; 67% of frozen episodes; and 58% of bias and drift episodes. Duplicate packets score 0% in the row classifier because identity/order faults belong to the stateful stream layer. The separate communication replay detects all 16 duplicates with zero false positives and all 10 duplicate episodes.

A proposed row-table override using non-positive time intervals was tested and rejected: it added 35 validation false alarms because natural repeated timestamps are not equivalent to identical packet IDs. The packet-identity stream detector is retained instead.

On unseen stations, bias and duplicate row-classifier recall are 0%, frozen and timestamp recall are 40%, and drift/noise recall are 60%. These are the highest-priority accuracy gaps.

## Correction and repair result

Operational correction means a fault was detected, the affected sensor was inferred, and a causal estimate was available.

| Split | Sensor | Coverage | Corrected MAE | MAE reduction | 90% interval coverage |
|---|---|---:|---:|---:|---:|
| Unseen time | Temperature | 35.49% | 1.76 °C | 82.77% | 98.68% |
| Unseen time | Pressure | 67.28% | 1.49 hPa | 98.66% | 87.42% |
| Unseen time | Humidity | 58.12% | 13.00 points | 56.30% | 78.39% |
| Unseen stations | Temperature | 27.12% | 1.48 °C | 93.28% | 87.50% |
| Unseen stations | Pressure | 70.15% | 1.27 hPa | 97.83% | 87.23% |
| Unseen stations | Humidity | 37.04% | 6.50 points | 93.88% | 92.50% |

The strict automatic gate produced 35 temperature and 4 pressure proposals on unseen time, and 8 temperature and 2 pressure proposals on unseen stations, with 100% measured precision. Coverage is intentionally tiny. Humidity remains review-only. These are benchmark results, not permission to overwrite operational data automatically.

## Model and method inventory

| Component | Method | Deployment role | Decision |
|---|---|---|---|
| Deterministic QC | physical range, missing, rate, freeze, gap, duplicate and order checks | stream safeguards and communication faults | Keep |
| Statistical baselines | Hampel/robust z, EWMA/change, neighbour rules | benchmark and interpretable evidence | Keep |
| Isolation Forest | unsupervised anomaly score | baseline comparison | Do not use as primary |
| Calibrated LightGBM | regularized gradient-boosted trees | production event/fault model | Primary model |
| LightGBM root model | calibrated 12-class diagnosis | probable incident root cause | Keep with abstention |
| Causal TCN | dilated temporal convolutions with focal loss | sequence evidence | Advisory only; false-alarm gate failed |
| CatBoost ensemble | five GPU seeds, isotonic calibration | GPU development candidate | Promising; not yet promoted |
| Sensor-specific LightGBM | temperature/pressure/humidity changed-value classifiers | correction opportunity and safety gates | Supporting only |
| Causal correction ensemble | lag, rolling center, EWMA and neighbour estimators | advisory corrected value | Keep |
| Health trajectory | risk decay plus recent linear trend | maintenance indication | Label as heuristic |

L1 and L2 regularization are already present through LightGBM `reg_alpha` and `reg_lambda`. Multi-window slopes, neighbour-residual slopes, CUSUM, monotonic runs, and climatology residuals are also already implemented. Adding more model names without a leakage-safe ablation is unlikely to help.

## Comparison with conventional AWS quality control

| Conventional operational approach | SkyGuard equivalent or extension |
|---|---|
| hard physical limits | deterministic range rules |
| step/rate checks | causal deltas, rates, EWMA residuals, CUSUM |
| persistence/frozen checks | run length plus temporal model evidence |
| internal consistency checks | multivariate interactions across the three permitted parameters |
| climatological checks | station/cluster/month/hour causal climatology residuals |
| spatial “buddy” checks | distance-aware backward neighbour residual and agreement features |
| manual analyst review | confidence, evidence, probable root cause and maintenance queue |
| missing-value replacement | advisory causal estimate with uncertainty and safety tier |

SkyGuard’s novelty is not replacing these proven checks with a black box. It combines them with calibrated ML, neighbour-weather protection, incident-level reasoning, uncertainty-aware correction, and an offline/live evidence platform.

## SIH weighted readiness estimate

| Official criterion | Maximum | Current internal estimate | Evidence and remaining gap |
|---|---:|---:|---|
| Innovation & novelty | 25 | 21.5 | strong self-healing workflow and neighbour gate; needs prospective degradation learning |
| Detection accuracy | 20 | 12.0 | high precision, but F1/recall and new-station weak faults are below competitive target |
| Real-time capability | 15 | 13.5 | full path 428.13 rows/s and 2.336 ms/row; needs sustained p95 test |
| Explainability | 10 | 8.0 | local contributions and readable evidence; root coverage is low |
| Scalability | 10 | 7.5 | projected 77.1× capacity for 10,000 stations at 30-minute cadence; not a distributed load test |
| Practical deployability | 10 | 8.0 | offline startup, API, cache and live mode; no official IMD adapter or pilot |
| Visualization/UI | 5 | 4.5 | complete judge dashboard and export; should add mobile/responsive judge rehearsal |
| Energy efficiency | 5 | 3.0 | 5.20 MiB detector and CPU proxy; no measured joules or ESP32 deployment |
| **Total** | **100** | **78.0** | strong complete prototype; accuracy is the main score limiter |

A realistic podium target is at least 88/100 internal readiness, driven mainly by a 6–8 point gain in the accuracy criterion and stronger real-world evidence.

## Experimental-validity warning

The repository originally treated 2024 as locked, but multiple local Phase 5/Phase 10 variants have now been compared on it. Therefore 2024 remains a useful benchmark comparison, but it is no longer a globally untouched final test. Future model choices must be made only on development blocks. After freezing the next policy, build a new 2025 or later station/time holdout and open it once.

## Exact priority order

1. Run GPU Iteration 4 without opening final tests. Promote causal state only if every block meets precision, false-alarm, point-F1 and event-F1 safeguards.
2. Build a new blind holdout before any further production model choice.
3. Compare the development CatBoost ensemble against LightGBM using station-season blocks and confidence intervals.
4. Train incident-level weak-fault specialists for bias, drift and frozen faults; do not optimize only row F1.
5. Expand injected weather cases beyond regional warming and include weather events on unseen stations.
6. Improve diagnosis with hierarchical stages: event → affected sensor → fault family → subtype, with calibrated abstention at each stage.
7. Replace heuristic degradation probability with a prospective survival/time-to-maintenance model when real maintenance outcomes exist.
8. Add sustained concurrent load, p95/p99 latency and measured energy evidence.
9. Integrate an authenticated IMD AWS adapter without changing the detector contract.

## Final answer to “best or worst?”

SkyGuard is **good system engineering with medium detection performance**. It is much stronger than a superficial dashboard and clearly solves the requested workflow. It is not yet the best possible anomaly model because compliant F1 is 47–53%, weak-fault recall is unstable, and diagnosis coverage is below 27%. Continue improving, but only through development-only experiments with explicit promotion gates; do not add neural networks merely to make the architecture sound advanced.

# SkyGuard AI — Iteration 8 audit and Iteration 9 runbook

## Decision

Iteration 8 is a useful research gain but is **not deployable**. It passed 8 of 14 development gates, so the accepted Iteration 5 detector remains unchanged. The purpose of Iteration 9 is to solve the remaining SIH26073 detection problems, not to optimize a presentation score.

No DWD/NOAA 2024 or 2025 observation/label is authorized in Iteration 9.

## What the complete project already solves

| SIH26073 requirement | Current status | Evidence/implementation |
| --- | --- | --- |
| Only temperature, pressure and relative humidity as observation inputs | Complete | Phase 10 has an explicit three-parameter contract; dew point and calendar shortcuts are excluded. |
| Real-time AWS anomaly alerts | Complete | Offline streaming/replay API, causal features, alert queue and live METAR adapter exist. |
| Spike and sudden-error detection | Complete | Hard physical checks plus supervised temporal/spatial detection. |
| Frozen sensor detection | Complete but still measured per domain | Frozen-run rules, specialist model and incident logic exist. |
| Communication errors | Complete under a verified cadence/heartbeat contract | Missing packets, duplicate packets, out-of-order timestamps and gaps are handled separately from weather values. |
| Learn temporal and seasonal behaviour | Complete | Lag, robust rolling, EWMA, climatology residual, slope, CUSUM and monotonic-run features. |
| Multivariate and neighbour consistency | Complete | Same-time neighbour residuals, regional agreement and trend-disagreement features. |
| Genuine weather versus sensor fault | Partial | DWD confirmation weather F1 is strong, but India confirmation weather F1 is weak. |
| Confidence and explainability | Complete, calibration still improvable | Probabilities, alert reasons, model feature importance and dashboard explanations exist. |
| Root-cause classification | Partial | Iteration 8 detected-row accuracy is 0.7403; macro F1 and per-class transfer were not yet acceptable evidence. |
| Sensor degradation and maintenance | Functional | Sensor health trend and maintenance recommendations exist; slow drift recall remains the key model gap. |
| Corrected/imputed values | Complete as advisory output | Corrected estimate and uncertainty interval are available; automatic overwrite is intentionally disabled. |
| Visualization dashboard | Complete | Map, readings, alerts, health, explanations, metrics, fault injection and reports are implemented. |
| Scalable software deployment | Complete for a laptop/server demonstration | Measured throughput is 405.27 rows/s, with a 72.95× projected capacity factor for 10,000 stations at 30-minute cadence. |

## Iteration 8 result — what improved and what did not

### Strong evidence

| Confirmation slice | Precision | Point F1 | Event F1 | Weather F1 | False alarms/station/day |
| --- | ---: | ---: | ---: | ---: | ---: |
| India | 0.8421 | 0.5494 | 0.6526 | 0.3400 | 0.01524 |
| DWD all stations | 0.6667 | 0.2245 | 0.3051 | 0.9084 | 0.01537 |
| DWD pseudo-unseen stations | 0.7656 | 0.4516 | 0.4211 | 0.9038 | 0.01845 |

Iteration 8 greatly improved transfer over the unadapted India-only baseline on DWD. It also improved India event F1 and weak-fault recall. These are real gains.

### Blocking failures

1. DWD confirmation precision is below the required 0.80 safety floor.
2. India point F1 is 0.0018 below the frozen reference; no regression is allowed.
3. India confirmation weather F1 is only 0.34.
4. Worst supported India climate weather F1 is 0.3643.
5. DWD fault-to-weather rate reaches 0.01227, above the 0.01 cap.
6. DWD confirmation drift episode recall is 0.0.
7. Root-cause detected-row accuracy is 0.7403 and macro-F1 evidence is missing.
8. The validation curriculum has one episode per family/climate/scope, so results have high seed variance.

## Why these failures occurred

Feature importance shows `temperature_rolling_median_24h`, `humidity_rolling_median_24h`, `nearest_neighbor_km` and `pressure_rolling_median_24h` among the strongest predictors. These values can identify geography or climate domain instead of fault physics. The model therefore learns part of the DWD/India boundary and transfers inconsistently.

The weather model also uses one global threshold. A score calibrated for German climate events is not automatically calibrated for Indian regional events. Max-fusion with the LSTM can raise weak anomalies, but it can also inflate isolated novelty scores and reduce precision. Finally, one injected episode per cell means a single easy or difficult random event can change the reported family recall sharply.

## Iteration 9 solution

### 1. Domain-invariant residual LightGBM

The new supervised contract retains 87 of 108 causal features and removes 21 shortcut-prone fields:

- raw temperature, pressure and humidity;
- raw temperature-humidity/pressure-temperature combinations;
- nearest-station distance;
- absolute lag, rolling median and EWMA prior for each sensor;
- absolute neighbour weighted mean and median for each sensor.

Multi-window slopes, CUSUM, robust z-scores, MAD, frozen runs, climatology residuals, neighbour residuals and regional consistency remain. Hard physical limits stay outside the ML model.

### 2. Causal station calibration

Each residual score is normalized against the station's preceding 30 days. The current observation is shifted out of the baseline, and a new station uses a training-only fallback. This makes one frozen threshold more transferable without using station ID or domain labels.

### 3. L2-calibrated fusion

The system compares:

- residual-only score;
- full-tree/residual consensus;
- L2-calibrated fusion of the frozen full tree, residual tree, clean-only Isolation Forest and causal LSTM.

The calibrator cannot see domain, station, coordinates or climate cluster. This replaces unsafe max-score fusion with learned regularized weighting.

### 4. Strict chronological selection

The first half of each domain's tune period is used for early stopping/calibration. The later half is used for threshold selection. DWD pseudo-unseen stations are excluded. Discovery and confirmation are never searched.

### 5. Three-seed stress corpus

The existing seed 8023 is combined with independent seeds 9029 and 9049. Each seed preserves the same anomaly prevalence and every family/climate/scope contract. Feature tables are cached independently so interrupted Colab sessions can resume.

### 6. Hierarchical diagnosis evidence

A shortcut-free root-cause CatBoost model reports accuracy, macro F1 and per-family precision/recall on both all fault rows and actually detected fault rows.

## Functional acceptance gates

Iteration 9 may proceed to one locked confirmation only if all gates pass:

- precision at least 0.80 in India, DWD and DWD pseudo-unseen confirmation;
- false alarms at most 0.02 incidents/station/day;
- no point-F1, event-F1 or weak-fault recall regression versus Iteration 8;
- India weather F1 at least 0.65;
- DWD weather F1 at least 0.75;
- every supported climate weather F1 at least 0.65;
- fault-to-weather rate at most 0.01;
- all three stress seeds completed with no F1 regression;
- mean stress drift episode recall at least 0.50;
- detected-fault root-cause macro F1 at least 0.70 and accuracy at least 0.80;
- no domain/station identifiers or locked-year data used.

Passing development gates means only **eligible for one locked confirmation**. It does not automatically replace the deployed model.

## Colab instructions

1. Upload/open `SkyGuard_AI_GPU_Iteration_09_Domain_Invariant_Calibration_Colab.ipynb`.
2. Keep the existing Iteration 8 Drive experiment folder and both development bundles in place.
3. Select a T4 GPU.
4. Keep `UNLOCK_FINAL_TESTS=False`, `REUSE_SAVED_MODELS=True` and `RUN_ITER9_STRESS=True`.
5. Run all cells in order.
6. If Colab disconnects, reconnect and run all again. Completed features/models are reused.
7. Return every JSON/CSV path printed by the final cell. Do not open locked data.

## Current internal SIH scoring snapshot (secondary audit only)

This is not the project objective and is not an official judge score. The current end-to-end system remains approximately 78/100 on the supplied SIH weightage: innovation 21.5/25, detection 12/20, real-time 13.5/15, explainability 8/10, scalability 7.5/10, deployability 8/10, UI 4.5/5 and energy evidence 3/5. The single number must not be confused with model accuracy. Iteration 9 is judged by the functional gates above.

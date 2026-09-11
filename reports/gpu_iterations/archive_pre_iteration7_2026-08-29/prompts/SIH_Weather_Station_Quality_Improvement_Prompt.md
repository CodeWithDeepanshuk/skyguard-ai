# Master implementation prompt — SIH weather-station data quality system

You are a senior machine-learning scientist, meteorological data-quality engineer, MLOps engineer, and SIH product mentor. Work inside my existing project/repository and improve the current Phase 10 system without discarding working components.

## Current verified baseline

- Unseen-time: precision 71.47%, recall 41.50%, F1 52.51%, AUPRC 48.45%, episode recall 79.17%, false alarms 0.0429/station-day, mean delay 194.7 min.
- Unseen-station: precision 89.89%, recall 32.00%, F1 47.20%, AUPRC 41.95%, episode recall 63.33%, false alarms 0.0064/station-day, mean delay 227.4 min.
- Diagnosis: coverage 26.24%/19.20%; accepted accuracy 69.98%/87.50%; end-to-end exact root accuracy 18.36%/16.80%.
- Weak episode classes: frozen 66.67%, bias 58.33%, drift 58.33%. Duplicate packets are found by streaming rules but missing from unified ML evaluation.
- Correction weaknesses: unseen-time temperature MAE 1.66 C and humidity MAE 12.92% RH; temperature correction coverage 33.90%/42.37%; humidity 90% intervals are miscalibrated.
- Streaming loop: 5,924–33,733 rows/s and 0.03–0.17 ms/row; preserve this strength and additionally measure end-to-end API latency.

## Non-negotiable scientific rules

1. Do not use random row splits. Preserve chronology and station independence. Hold unseen stations out from every training, tuning, calibration, normalization, feature-selection, and threshold-selection operation.
2. Create immutable partitions: `train`, `tune`, `calibration`, `test_time`, and `test_station`. The two test sets are opened only once after the complete pipeline and thresholds are frozen.
3. Fit imputers, scalers, climatology, feature selection, calibrators, ensemble weights, and thresholds on development data only. All rolling features must be causal: use only timestamps available at inference time; shift rolling statistics before comparing the current observation.
4. Keep real faults and synthetic faults separate. Synthetic injection is allowed only in train/tune, never in calibration or either final test. Sample synthetic episodes—not isolated random rows—with realistic duration, magnitude, ramp rate, season, missingness, and sensor coupling. Report real-only and synthetic-only performance separately.
5. Do not optimize overall accuracy or ROC-AUC. Primary model-selection measures are AUPRC, event precision/recall/F1, first-hit delay, false-alarm episodes per station-day, per-fault episode recall, and performance on unseen stations.
6. Every final metric must include a 95% station/block-bootstrap confidence interval and results over at least five fixed random seeds. Report mean, standard deviation, and worst seed. Never claim improvement when confidence intervals substantially overlap without a paired bootstrap result.
7. Select the operating threshold only on the calibration set under explicit constraints. Default policy: maximize event F2, subject to false alarms <=0.02 per station-day and point precision >=0.75. Treat recall >=0.65 and median delay <=60 min as stretch gates, not official SIH requirements. If no threshold is feasible, report the Pareto frontier and constraint violations.
8. Evaluate event predictions without point-adjustment. Report both point metrics and strict event metrics. One detected point must not cause an entire true episode to be counted as pointwise correct. Define episode matching, merge gap, tolerance, and latency explicitly.
9. No manual, station-specific tuning on either test set. Any per-station adaptation must be learned online from past normal data with a fixed algorithm and cold-start policy.
10. Retain an immutable Phase 10 baseline and build an ablation table. No architecture is accepted unless it improves the operational objective and does not materially harm unseen-station performance, false alarms, or latency.

## Required pipeline

### A. Data contract and audit

- Require: timestamp, station ID, sensor values and units, sampling cadence, anomaly label, episode ID or derivable episode boundaries, fault type, weather-event label/source, and clean reference values for correction when available.
- Validate duplicates, timestamp order, missingness, cadence changes, impossible values, label conflicts, unit consistency, station metadata, sensor replacement/maintenance dates, and leakage through IDs or corrected targets.
- Produce: station coverage table, label/fault counts by station and split, event duration/severity distributions, missingness map, and a split manifest with hashes.

### B. Hybrid detector; preserve interpretable rules

Create a union of deterministic communication/physics checks and calibrated learned scores.

- Hard-rule channel: duplicate packet, missing packet/dropout, timestamp reversal/gap, impossible physical range, impossible rate of change, invalid humidity range, invalid pressure/temperature units, and explicit communication corruption. These rules must flow into the same alert, root-cause, dashboard, and evaluation tables as ML predictions.
- Forecast-residual channel: global station-independent CatBoost/LightGBM models for expected temperature, pressure, and humidity using causal lags, hour/day cyclic features, rolling median/MAD, seasonal/climatological residual, cross-sensor features, and leave-self-out neighbouring-station context when operationally available.
- Specialist scores:
  - spike/drop: robust first-difference and forecast residual;
  - frozen: constant-run length, quantization-aware equality, near-zero rolling MAD, and contradiction with neighbouring stations;
  - bias: persistent signed residual using Page-Hinkley/CUSUM/EWMA;
  - drift: robust residual slope plus change-point score over several windows;
  - noise: rolling MAD/expected-noise ratio and high-frequency energy;
  - scale/unit: candidate transform likelihoods such as C/F, Pa/hPa, factor-10/factor-100, and residual ratios;
  - multi-sensor: broken physical/cross-sensor relationships and masked reconstruction error;
  - communication: deterministic packet/timestamp evidence.
- Optional GPU TCN: use a small causal dilated TCN for forecasting or masked reconstruction. It must be an ablation, not the default winner. Tune receptive field to cover the longest relevant bias/drift horizon. Export raw scores and calibrate them before fusion.
- Calibrated fusion: fit out-of-fold/held-out calibrators and a simple monotonic stacker over rule, residual, specialist, and optional TCN scores. Hard communication rules may override the learned probability. Compare isotonic, Platt/logistic, and beta calibration using Brier score, log loss, reliability diagrams, and expected calibration error.
- Alert policy: tune hysteresis (`start_threshold > continue_threshold`), minimum duration, cooldown, and merge gap on calibration data only. Optimize early first-hit detection under the false-alarm budget.

### C. Genuine weather versus sensor fault

- Do not use the weather model as an early gate that can erase faults. First detect abnormal behaviour, then classify the source hierarchically as genuine weather, sensor/communication fault, both/uncertain, or normal.
- Use spatial agreement, physically consistent multi-sensor changes, official weather/event references when available, and calibrated probabilities.
- Report genuine-weather precision/recall/F1, weather-to-fault error, fault-to-weather error, and performance during extreme-weather subsets.

### D. Root-cause diagnosis with safe abstention

- Train diagnosis only on true/predicted alert candidates, using class-weighted CatBoost/LightGBM plus deterministic overrides.
- Use hierarchical classes: communication, temporal, value fault, behaviour fault, multi-sensor, genuine weather, unknown.
- Calibrate class probabilities. Choose abstention thresholds from calibration risk–coverage curves; do not target coverage alone.
- Report oracle-detection diagnostic accuracy, accepted accuracy, coverage, macro-F1, per-class recall, risk–coverage/AURC, and exact end-to-end root accuracy. Explain the gap between oracle and end-to-end performance.

### E. Correction and uncertainty

- Correct only when the alert and root cause make correction defensible. Never overwrite raw observations; output raw value, corrected value, interval, confidence, method, and audit trail.
- Train station-independent quantile CatBoost/LightGBM forecasters using normal data and operationally available neighbour/context features. Compare persistence, seasonal median, linear/state-space, and learned baselines.
- Calibrate intervals separately by sensor and, if sample size permits, season/station cluster using rolling/adaptive conformal residuals. Evaluate coverage and mean interval width together; nominal 90% alone is not enough.
- Automation policy: auto-correct only when calibrated coverage and error gates pass on both tests; otherwise mark review-only. Humidity remains review-only until recalibrated.

### F. Validation and evidence

Run the following ablations: Phase 10; rules only; ML only; rules+forecast residual; +specialists; +calibration/fusion; +post-processing; +weather hierarchy; +TCN. For every row report point AUPRC/precision/recall/F1, strict event precision/recall/F1, per-fault event recall, delay distribution (median/P90/mean), false-alarm episodes/station-day, diagnosis metrics, correction MAE/coverage/interval width, CPU/GPU latency, memory, serialized size, and energy estimate with measurement method.

Perform failure analysis by station, season, sensor, fault, duration, severity, missingness, and weather regime. Save at least 20 representative false negatives and false positives with time-series plots and explanations.

## Product and SIH deliverables

- Preserve offline operation and graceful degradation when neighbouring stations or weather APIs are unavailable.
- Export a unified incident JSON containing raw values, alert probability, rule evidence, model evidence, fault class, calibrated confidence, correction, interval, action, timestamps, model/data versions, and audit trail.
- Add dashboard views for live alerts, incident timeline, station health, spatial map, root-cause evidence, correction with uncertainty, offline/sync state, and performance/resource cards.
- Produce an SIH evidence matrix for the published criteria: novelty; complexity; clarity/detail; feasibility; practicability; sustainability; scale of impact; user experience; and future progression. For every claim, link a demo, metric, ablation, architecture artifact, or user workflow. Do not invent a numerical official SIH score.
- Produce: reproducible Colab notebook, environment lockfile, model card, data card, experiment ledger, saved split manifest, ablation CSV, final test report, API contract, dashboard payload examples, and a three-minute demo script.

## Execution order

1. Inspect the existing repository and find the Phase 10 data schema, split logic, rule engine, models, thresholds, evaluation, streaming API, and dashboard integration.
2. Write a gap report before changing code. Explicitly identify leakage, inconsistent metric definitions, test-set tuning, and missing rule/ML fusion.
3. Reproduce Phase 10 exactly and save its metrics/artifacts.
4. Implement one controlled change at a time in the ablation order. Use Optuna only on tune/calibration partitions; never on final tests.
5. Freeze the winning configuration and all thresholds, record hashes, then run final tests once.
6. If a required column or label is missing, do not fabricate it. Add a schema check and clearly mark the blocked experiment.

## Acceptance gates

- Mandatory: no split/feature leakage; deterministic packet errors included end-to-end; strict event metrics; calibrated probabilities; frozen test protocol; reproducible seeds; confidence intervals; Phase 10 comparison; complete resource benchmarking; and dashboard incident integration.
- Desired operational gates on both final tests: event recall >=0.85, point recall >=0.65, point F1 >=0.70, false-alarm episodes <=0.02/station-day, median first-hit delay <=60 min, diagnosis accepted accuracy >=0.85 at >=0.60 coverage, and clearly calibrated correction intervals. These are team goals, not official SIH thresholds.
- If desired gates conflict, prioritize: safety-critical episode recall, false-alarm budget, unseen-station robustness, early detection, then point F1. Present a Pareto table rather than hiding the trade-off.

Return concrete code changes, commands, experiment tables, plots, remaining limitations, and the next highest-value experiment. Do not claim success from training metrics or a single split.

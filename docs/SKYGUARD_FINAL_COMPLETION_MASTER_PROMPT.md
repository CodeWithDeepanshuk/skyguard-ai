# SkyGuard AI — final completion master prompt

Use this prompt as the engineering and scientific acceptance contract for the
next SkyGuard AI completion pass. It is intentionally stricter than a normal
hackathon build prompt because a high dashboard score cannot compensate for an
invalid anomaly experiment.

## Role

Act as the lead meteorological-ML engineer, streaming-systems engineer,
scientific auditor, and SIH 26073 submission owner. Continue from the existing
SkyGuard repository and its audited Iteration 9 checkpoint. Do not restart the
project, discard validated components, or claim improvements that have not
been measured.

## Mission

Deliver the strongest honest, fully executable software solution possible for
SIH 26073: real-time anomaly detection for Automatic Weather Stations using
only temperature in degrees Celsius, atmospheric pressure in hPa, and relative
humidity in percent as detector observations.

The completed system must:

1. detect physical, temporal, multivariate, spatial, communication, and slow
   degradation anomalies causally;
2. distinguish normal observations, genuine regional weather, and sensor/data
   faults without an unsafe weather veto;
3. group row evidence into operational incidents;
4. provide severity, calibrated confidence, probable root cause, evidence,
   correction advice, uncertainty, sensor health, and maintenance guidance;
5. run from both an offline deterministic replay and a genuine live-data
   adapter;
6. remain reproducible on a normal laptop, with GPU training optional;
7. expose a judge-facing dashboard, API, reports, example scenarios, and a
   one-command verification path.

## Immutable scientific rules

- The automatic detector may use only the three permitted observations and
  causal transformations of their past and same-parameter neighbour history.
- Never use dew point, latitude, longitude, station ID, domain ID, climate
  label, injected label, original clean value, future observation, or split
  identity as an inference feature. Dew point may be used by an input adapter
  only to derive relative humidity when the source does not report RH.
- Every online feature and decision must be reproducible at the time of the
  alert. Future rows may be used only for retrospective correction evaluation,
  never for live inference.
- Never randomly mix rows from the same station or fault episode across
  training and evaluation. Split by year/time block, station, season, and full
  incident.
- Use 2022 for fitting and 2023 only for calibration, policy development,
  discovery, and confirmation. Keep NOAA/DWD 2024 and all 2025 material closed
  until all development gates pass. Previously opened years are comparison
  benchmarks, not pristine blind evidence.
- Do not call an unverified archive silence a communication failure. Automatic
  dropout alerts require an adapter-provided cadence and heartbeat SLA;
  otherwise emit an explicit low-confidence data-gap advisory.
- Corrections are advisory and preserve the original observation. Never
  silently overwrite source data.
- Synthetic/injected faults provide exact controlled labels; public weather
  observations provide genuine meteorological context. Do not represent
  injected-fault accuracy as real maintenance-fault accuracy.
- Save data URLs, station metadata, hashes, code/model versions, random seeds,
  thresholds, feature contracts, split contracts, predictions, and every
  rejected ablation.

## Audited starting checkpoint

- The current product already has a working offline replay, live METAR mode,
  deterministic QC, 108 compliant causal features, LightGBM models,
  explainability, advisory correction, health/maintenance outputs, FastAPI,
  dashboard, exports, and automated tests.
- Iteration 9 is valid but non-promotable. It passed 12 of 23 gates.
- Iteration 9 achieved excellent DWD precision and weather recognition but
  missed too many rows and weak incidents because a row threshold near 0.891
  was required to control false alarms.
- Independent binary fault/weather models plus a weather veto routed some
  faults into weather. Row-level diagnosis also collapsed minority root-cause
  classes.
- The accepted deployed policy must remain unchanged until a challenger passes
  every predeclared gate.

## Data plan

1. Re-audit the official NOAA/NCEI India corpus rather than assuming it is
   small. Measure per-station/year valid T/P/RH coverage, cadence regularity,
   pressure provenance, duplicate timestamps, source hashes, and causal
   neighbour availability.
2. Use all supportable 2022–2023 Indian stations in regional clusters around
   Delhi, Hyderabad, Bengaluru, and Chennai. Keep at least one station per
   cluster completely unseen during model fitting and calibration.
3. Add an official station only if both development years are present, the
   three required variables meet the declared completeness rule, metadata is
   verified, and its cadence contributes useful temporal or regional support.
4. Retain the DWD 2022–2023 10-minute corpus as a cross-climate development
   domain, not as a replacement for India evidence.
5. Generate independent train, calibration, policy, discovery, and
   confirmation fault/weather curricula with distinct seeds. Balance episode
   mass so long incidents do not dominate.

## Final decision architecture

### Layer 0 — deterministic transport and physical QC

Detect impossible range, missing/invalid fields, timestamp disorder, true
duplicate packet identity, unit/scaling corruption, verified heartbeat gaps,
and multi-sensor freeze. These rules have deterministic priority and produce
human-readable evidence.

### Layer 1 — high-recall causal candidate evidence

Retain the compliant residual LightGBM ensemble, robust statistics, rolling
median/MAD, EWMA residuals, 3/6/12/24-hour slopes, neighbour-residual slopes,
CUSUM, monotonic runs, frozen runs, multivariate consistency, Isolation Forest,
and the causal sequence model only as evidence. Use a lower candidate threshold
than the final alert threshold. A candidate is not yet an alert.

### Layer 2 — causal incident state

Aggregate candidate evidence by station and affected sensor using:

- an instant path for impossible values, severe spikes, timestamp/packet
  faults, unit/scaling faults, and obvious corruption;
- a k-of-n persistence path for bias, drift, frozen, and noise;
- hysteresis and recovery to prevent alert flapping;
- cadence-aware windows measured in elapsed time, not a fixed row count;
- incident features including duration, evidence count, score max/mean/slope,
  CUSUM growth, monotonicity, affected-sensor count, neighbour isolation,
  regional extent, and recovery behaviour.

All state updates must depend only on the current and previous observations.

### Layer 3 — mutually exclusive three-way triage

At the incident level, estimate exactly one state:

1. normal/advisory;
2. genuine regional weather;
3. sensor/data fault.

Use a multiclass model or a fault-given-candidate discriminator. Do not use an
independent weather model as a hard veto. Weather requires independent spatial
coherence: enough recent nearby stations, physically consistent multi-sensor
movement, suitable regional extent, and no deterministic transport fault. A
high fault score alone must never increase the weather probability.

### Layer 4 — hierarchical incident diagnosis

First diagnose the broad family:

- communication/data-order fault;
- abrupt sensor fault;
- persistent sensor degradation;
- multi-sensor/station-power fault.

Then diagnose the subtype with family specialists:

- communication: dropout, duplicate packet, timestamp disorder, corruption;
- abrupt: spike, sudden drop, unit error, scaling error;
- persistent: bias, drift, frozen sensor, excessive noise;
- station: multi-sensor freeze or corrupted multi-parameter failure.

Aggregate evidence across the incident, calibrate confidence, and abstain to
`unknown_fault` when the diagnosis is unsafe.

### Layer 5 — dedicated drift/degradation state

Use neighbour-residual slope, multi-window trend agreement, signed CUSUM,
monotonic persistence, and recovery/reset conditions. Require sustained
evidence and report latency. Feed repeated drift/bias incidents into the sensor
health trajectory. Until real maintenance outcomes exist, label the predicted
maintenance horizon as heuristic decision support, not a calibrated failure
probability.

### Layer 6 — correction and self-healing advice

For a detected fault, infer the affected sensor and provide a causal estimate
from lag/EWMA/rolling and age-weighted neighbour evidence. Report a calibrated
interval and a safety tier. Keep humidity and uncertain/domain-shift cases
review-only. Store both original and proposed values.

## Models and ablations

- Mandatory reference: current compliant LightGBM policy.
- Primary challenger: regularized multi-seed LightGBM/CatBoost evidence plus
  incident-state aggregation and a three-state incident classifier.
- Dedicated drift specialist: interpretable slope/CUSUM state machine, with an
  ML specialist only if it adds cross-seed recall under the false-alarm cap.
- Sequence models: keep TCN/LSTM-autoencoder evidence only when an ablation
  proves incremental incident-level value. Do not promote a neural network for
  novelty.
- Calibrate on data disjoint from base-model fitting. Fit policy thresholds on
  a later disjoint block. Never search discovery or confirmation results.

## Required metrics

Report per domain, climate cluster, station macro, season, injection seed, and
fault family:

- TP, FP, FN, TN;
- precision, recall, F1, AUCPR;
- incidents per station-day and false alerts per station-day;
- incident precision, recall, F1;
- median, mean, and p90 detection latency;
- weak-fault and drift incident recall;
- genuine-weather precision/recall/F1;
- fault-to-weather and weather-to-fault rates;
- root-cause incident accuracy, macro F1, accepted accuracy, and coverage;
- Brier score, expected calibration error, and reliability bins;
- correction coverage, MAE/RMSE, improvement over reported values, and interval
  coverage;
- end-to-end p50/p95 latency, throughput, memory, CPU use, and artifact size.

Overall accuracy alone is prohibited because normal rows dominate.

## Promotion gates

A challenger may replace the accepted deployment only if all gates pass on
fresh 2023 confirmation seeds:

- precision at least 0.80 in India, DWD, and pseudo-unseen stations;
- false alerts no more than 0.02 incidents per station-day in every domain;
- no point-F1 or incident-F1 regression against the best retained baseline in
  any primary domain;
- India and DWD weather F1 at least 0.75 where supported, and worst supported
  climate F1 at least 0.65;
- fault-to-weather rate no more than 0.01 in every confirmation domain;
- drift incident recall at least 0.50, including unseen stations;
- incident root-cause macro F1 at least 0.70, accuracy at least 0.80, and honest
  confidence/coverage reporting;
- three or more unseen confirmation injection seeds with seed intervals;
- no forbidden feature, split leak, future row, locked year, or threshold
  tuning on confirmation.

If any gate fails, archive the result as a valid negative experiment, retain
the existing deployment, and state the exact failed gate. Never lower a gate
after seeing the result.

## Product completion requirements

- Integrate the incident state and triage contract into offline replay and the
  live adapter without changing the three-input contract.
- Keep `/` as the judge dashboard and `/docs` as the developer API tester.
- Surface whether neighbour evidence is available, stale, or absent.
- Surface `normal`, `advisory`, `genuine_weather`, `candidate_fault`, and
  `confirmed_fault` distinctly.
- Add incident lifecycle, confidence decomposition, affected sensors,
  correction safety tier, health trend, and maintenance advice to API/export.
- Preserve cached offline operation if the live source is unavailable.
- Add unit, causality, leakage, data-integrity, API, replay, model-loading, and
  dashboard regression tests.

## Deliverables

Produce:

1. validated and checksummed 2022–2023 India development bundle;
2. incident-state, triage, drift, diagnosis, and metric modules with tests;
3. a T4-compatible Iteration 10 notebook with restart-safe caches, fresh seeds,
   ablations, promotion gates, and explicit locked-year protection;
4. model/feature/split/communication contracts and result manifests;
5. an integration runbook that promotes only a passing model;
6. updated architecture, model card, final report, SIH requirement matrix, and
   seven-minute demo flow;
7. one-command local verification and a final evidence-boundary statement.

## Execution instruction

Read the existing reports, code, tests, and returned Iteration 9 artifacts.
Identify the largest measured bottleneck, implement the highest-value causal
fix, and verify every change. Continue through the full deliverable without
asking for avoidable choices. Separate three outcomes clearly:

- implemented and locally verified;
- ready for GPU evaluation but not yet empirically promoted;
- blocked by an external source, official IMD access, real maintenance labels,
  hardware energy measurement, or an unrun locked experiment.

Never convert the second or third category into a claimed result.

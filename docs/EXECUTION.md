# SkyGuard AI execution playbook

## Non-negotiable experiment rules

1. Raw NOAA files and the checksum manifest are immutable.
2. 2022 is training data, 2023 is validation data, and 2024 stays locked until final evaluation.
3. Hisar, Ramagundam, Chitradurga, and Pondicherry are station holdouts.
4. An entire injected episode belongs to exactly one split.
5. Every experiment records configuration, random seed, dataset hash, metrics, and model version.
6. Real observations and synthetic fault labels must remain visibly distinct in files, reports, and the dashboard.

## Delivery sprints

| Sprint | Main outcome | Completion gate |
|---|---|---|
| 0 — Data | Official multi-year benchmark | Complete: all validation checks pass |
| 1 — QC | Streaming-compatible deterministic checks | Complete: tests pass and corpus profile generated |
| 2 — Faults | Reproducible labelled anomaly episodes | Complete: 559 episodes; all integrity checks pass |
| 3 — Features | Causal temporal, multivariate, and neighbour features | Complete: 72 features; all leakage/coverage checks pass |
| 4 — Baselines | Rules, Hampel, EWMA, Isolation Forest | Complete: frozen 2023 thresholds and both 2024 reports validated |
| 5 — Classification | Fault type and genuine-event/individual-fault decision | Complete: calibrated frozen models, abstention, and unseen-station report |
| 6 — Repair | Corrected value, interval, explanation, health score | Complete: frozen correction metrics and validated incidents/health |
| 7 — Platform | Replay engine, API, persistence | Complete: four scenarios, stateful checks, SQLite, API and profiling pass |
| 8 — Dashboard | Judge-facing map, alerts, injection, metrics | Complete: responsive command centre, all evidence views, four scenarios, CSV export and browser QA |
| 9 — Final | Locked 2024 results and packaged submission | One-command startup and final evidence bundle |

## Parallel ownership for six members

| Member | Primary ownership | Must coordinate with |
|---|---|---|
| 1 | Data integrity, manifests, experiment datasets | Members 2 and 6 |
| 2 | QC rules and anomaly injection | Members 1, 3 and 6 |
| 3 | Features, baselines, ML and calibration | Members 2 and 6 |
| 4 | Streaming replay, FastAPI and storage | Members 3 and 5 |
| 5 | Dashboard, map, alert and explanation views | Members 4 and 6 |
| 6 | Tests, metrics, documentation and demo | Every member |

Each member should review one other member's module and be able to explain the complete runtime flow.

## Current commands

```powershell
python src/data/download_noaa_dataset.py
python src/data/normalize_noaa_isd.py
python src/data/validate_dataset.py
python -m unittest discover -s tests -v
python src/data/run_qc_baseline.py
python src/data/generate_labelled_faults.py
python src/data/validate_labelled_faults.py
python src/data/generate_features.py
python src/data/validate_features.py
python src/data/run_baseline_models.py
python src/data/validate_baseline_models.py
python src/data/run_fault_classifier.py
python src/data/validate_fault_classifier.py
python src/data/run_correction_health.py
python src/data/validate_correction_health.py
python src/data/run_safe_repair.py
python src/data/validate_safe_repair.py
python src/data/package_replay_scenarios.py
python src/data/profile_streaming_platform.py
python src/data/validate_streaming_platform.py
python src/data/validate_dashboard.py
```

## Completed Sprint 2 work order

1. Define the anomaly episode schema and clean-row eligibility rules.
2. Implement deterministic random-seed control.
3. Implement single-sensor faults: spike, drop, bias, drift, freeze, and noise.
4. Implement record/communication faults: dropout, duplicate, and timestamp disorder.
5. Implement unit/scaling and multi-sensor failures.
6. Generate separate 2022, 2023, and 2024 labelled datasets.
7. Verify no episode overlap and no station/time leakage.
8. Publish anomaly counts, duration/severity distributions, and example episodes.

## Completed Sprint 3 work order

1. Define a feature contract separating online-available features from offline-only audit fields.
2. Build station-local lag, rolling median/MAD, robust z-score, rate, EWMA, and seasonal/time features.
3. Build temperature-pressure-humidity cross-variable residual features.
4. Precompute geographic neighbours and distance weights from station metadata.
5. Align neighbour observations using backward-only time tolerance to prevent future leakage.
6. Produce feature tables for all four labelled splits.
7. Validate null coverage, feature ranges, deterministic generation, and no future timestamps.
8. Train simple baseline detectors only after the feature validator passes.

## Completed Sprint 4 work order

1. Define point-level and episode-level evaluation contracts.
2. Build deterministic rule-score and robust-z/Hampel baselines.
3. Train Isolation Forest using 2022 development data only.
4. Tune thresholds on 2023 validation without touching 2024 results.
5. Evaluate false alarms per station-day and detection latency.
6. Report performance separately for each fault type and regional weather hard negatives.
7. Freeze the selected baseline and run the 2024 time and unseen-station tests.
8. Publish confusion/error examples and resource usage.

## Completed Sprint 5 work order

1. Define the fault/event class taxonomy and an explicit unknown/abstain outcome.
2. Build episode-safe supervised training weights so long drift/freeze episodes do not dominate.
3. Train a lightweight gradient-boosted classifier on 2022 only.
4. Calibrate confidence and select abstention thresholds on 2023 validation.
5. Add regional neighbour agreement and persistence to the genuine-weather decision.
6. Report row and episode confusion matrices, macro F1, calibration error, and per-class recall.
7. Freeze the classifier and evaluate 2024 time and unseen-station holdouts.
8. Publish failure cases that Phase 6 explanations and health scoring must expose.

## Completed Sprint 6 work order

1. Define the incident, correction, uncertainty, explanation, and sensor-health contracts.
2. Build temporal and neighbour-based corrected-value estimators without using future data online.
3. Add historical two-sided interpolation as an offline evaluation-only benchmark.
4. Select correction methods by sensor and fault evidence on 2023 validation.
5. Evaluate corrected-value MAE/RMSE against preserved original clean values.
6. Generate readable evidence-based explanations and calibrated uncertainty intervals.
7. Aggregate repeated alerts into sensor health, degradation trend, and maintenance priority.
8. Validate complete incident records on both 2024 holdouts.

## Completed Sprint 7 work order

1. Define replay event, station state, alert, and API response contracts.
2. Replay rows in emitted timestamp order with configurable speed and deterministic controls.
3. Detect duplicate packets, out-of-order timestamps, and communication gaps statefully.
4. Load the strict three-parameter Phase 10 event/root artifact and compliant Phase 10 correction/health evidence once at startup.
5. Expose stations, readings, incidents, corrections, explanations, health, and metrics through FastAPI.
6. Add local persistence and a resettable demonstration scenario.
7. Measure replay throughput, latency, CPU, and memory on a normal laptop.
8. Pass offline end-to-end API and replay integration tests.

## Completed Sprint 8 work order

1. Build the offline dashboard shell and navigation.
2. Add station map, health colours, latest readings, and live replay controls.
3. Add alert queue, root-cause confidence, evidence, corrections, intervals, and maintenance action.
4. Add benchmark metrics and known-limitations pages.
5. Add pressure-drift, regional-weather, dropout, and packet-error scenario selectors.
6. Make the dashboard responsive and judge-readable without technical knowledge.
7. Add a downloadable incident report and deterministic 3–5 minute demo flow.
8. Pass browser-based end-to-end checks with the local API.

## Completed Sprint 9 work order

1. Audit the delivered system against every mandatory SIH 26073 software requirement.
2. Add an official public live-observation adapter with clear source semantics and cache fallback.
3. Normalize live temperature and QNH pressure and derive relative humidity from temperature/dew point.
4. Reuse the frozen causal feature and classification pipeline for live observations.
5. Add live status, refresh, readings and alerts endpoints plus dashboard mode switching.
6. Package one-click Windows startup, a final verification command and a seven-minute judge script.
7. Publish the complete accuracy, correction, safety, performance and limitations report.
8. Build and visually verify the final 10-slide SIH presentation.

## Completed Sprint 10 work order

1. Audit and remove forbidden dew-point features from the deployed detector path.
2. Switch live scoring, dashboard metrics, correction, health and safe repair to `SkyGuard-P10-compliant`.
3. Add multi-window slopes, CUSUM, climatology and regional neighbour-weather evidence.
4. Keep the causal TCN advisory after it failed the unseen-station false-alarm gate.
5. Add health trend, projected health and maintenance-horizon fields.
6. Measure complete inference throughput, latency, memory, artifact size and scale capacity.
7. Refresh genuine live data through the compliant model and verify the exact detector contract.
8. Pass 63 tests, dashboard validation, visual browser QA and 26 final-delivery checks.

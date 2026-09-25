# SkyGuard AI delivery plan

## Objective

Deliver an offline-first, live-capable SIH 26073 system that uses only temperature, pressure and relative humidity to detect, distinguish, diagnose, explain and safely correct abnormal AWS observations while monitoring sensor health.

## Completed phases

| Phase | Scope | Exit result |
|---:|---|---|
| 0 | genuine data foundation | 578,448 validated observations, 24 stations, 2022–2024, source hashes |
| 1 | deterministic QC | physical, temporal, frozen and communication checks over the full corpus |
| 2 | anomaly benchmark | 546 controlled fault episodes and regional-weather scenarios |
| 3 | causal feature pipeline | temporal, multivariate and neighbour feature tables |
| 4 | statistical/unsupervised baselines | reproducible rules, Hampel/EWMA, neighbour and Isolation Forest comparisons |
| 5 | initial event/root classification | calibrated LightGBM and weather/fault decision; now archived where noncompliant |
| 6 | correction/explanation/health | advisory values, intervals, explanations, health and maintenance |
| 7 | streaming/API | replay, stateful communication checks, SQLite and FastAPI |
| 8 | dashboard | judge-facing map, charts, alerts, metrics, provenance and exports |
| 9 | live mode/package | genuine METAR adapter, cache fallback and one-click startup |
| 10 | strict compliance/hardening | three-input Phase 10 deployment, trend/CUSUM/neighbour gate, full profiling and 63 passing tests |

## Current model freeze

- Production version: `SkyGuard-P10-compliant`.
- Detector inputs: temperature, pressure and relative humidity only.
- Production event/root model: calibrated LightGBM.
- Causal TCN: advisory, not automatic.
- 2024 is a benchmark comparison, not a pristine future final test.
- Correction is advisory; humidity is review-only.

## Remaining competition phases

### Phase 11 — GPU challenger development: complete

Iterations 4 and 5 were run on development blocks only. Iteration 4 was rejected because its causal incident state produced no safe gain. Iteration 5 passed the development safeguards with a small candidate gain: point F1 increased from 48.44% to 48.73%, event F1 from 60.00% to 60.95%, and weak-fault coverage improved without additional false-positive rows. It remains a candidate, not the deployed model.

### Phase 12 — New blind benchmark: built and sealed

Official NOAA/NCEI 2025 observations for all 24 stations were downloaded and hash-verified. Two non-overlapping evaluations are sealed: a later-time test on 20 known station identities and a later-time/unseen-station test on four reserved stations. The archive includes all fault families, genuine regional weather cases, causal Phase 10 features and operational communication scenarios. No final model was executed during the build.

### Phase 13 — One-time frozen challenger comparison: complete

The sealed 2025 comparison was opened once with all hashes and development locks passing. Iteration 5 improved future-time point F1 from 44.33% to 46.00% but produced no change on pseudo-unseen stations, where F1 remained 50.96%. It did not pass the frozen promotion or SIH readiness gates. The archive is now evidence and must not be used for further tuning.

### Phase 14 — Communication safety and station transfer: complete

Iteration 6 froze the safe heartbeat contract: unknown-cadence archival gaps remain advisory unless an adapter supplies expected cadence and a verified heartbeat SLA. Its weather and weak-fault challengers produced no confirmed gain, so the Iteration 5 development reference was retained. Iteration 7 then tested climate calibration, L1/L2 weather stacking and a causal TCN; it also failed the no-regression gates and was retained as a documented negative result.

### Phase 15 — Multi-climate Iterations 8–9: complete negative experiments

Iterations 8 and 9 used the official DWD corpus and domain-invariant calibration. They improved several DWD precision/weather measures but failed the complete no-regression, India weather, weak-fault, drift and root-cause gate set. They are archived as valid negative experiments; Iteration 5 remains the accepted development reference.

### Phase 16 — Final incident-intelligence Iteration 10: implementation complete, T4 evidence pending

The standalone Iteration 10 notebook combines corrected official India data and DWD development data without opening 2024/2025. It provides cadence-adaptive injection, 13 operational faults, six coherent weather families, 76 strict causal features, a three-way incident state, independent weather gate, elapsed-time k-of-n persistence, drift rescue, hierarchical root diagnosis, confidence calibration, correction/health evidence, three fresh seeds and strict promotion gates. Static verification and real-data curriculum smoke tests pass. Final empirical metrics remain pending until the user runs the T4 notebook and returns its result package.

### Phase 17 — Official IMD AWS integration: secure inspection implemented, live evidence pending

The portal contract is now implemented as a backend-only, static-IP, API-key + short-lived JWT download stage. Exact payload bytes, safe receipts and value-free schema fingerprints are supported, while operational normalization remains disabled until both real endpoint responses are reviewed for units, timezone, identifiers, missing codes, provider flags, revisions, coverage, history and request limits. No fallback provider impersonates IMD. See `docs/IMD_AWS_IMPLEMENTATION_PLAN.md` for gates and the exact remaining live test.

### Phase 18 — Final SIH freeze

Open the new blind test once, generate every report/dashboard/slide metric from one result block, run full verification, and rehearse internet and no-internet demos.

## Completion gates

The project is demonstration-complete now. A model improvement is complete only when:

- no forbidden input or future leakage exists;
- worst-block precision and false-alarm constraints pass;
- point and episode metrics improve without a weather regression;
- all model/policy artifacts and results are reproducible;
- all tests and visual checks pass;
- limitations and failed experiments remain documented.

See `docs/IMPROVEMENT_ROADMAP.md` for detailed targets and sequencing.

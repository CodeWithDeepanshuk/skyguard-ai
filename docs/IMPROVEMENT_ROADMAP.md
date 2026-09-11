# SkyGuard improvement roadmap

## Current baseline

Production is the compliant Phase 10 LightGBM path. The main benchmark F1 is 52.51% on unseen time and 47.20% on unseen stations. Episode recall is 79.17% and 63.33%. The model is precise but misses too many weak or station-specific faults.

## Phase A — Lock the honest baseline: complete

- Deploy only the three-parameter Phase 10 model.
- Regenerate correction, safe-repair, health, incidents and dashboard evidence from it.
- Refresh genuine live data through the compliant model.
- Measure complete inference rather than only replay storage.
- Preserve GPU Iteration 1–3 result artifacts.
- Pass all tests, dashboard checks and final-delivery checks.

Exit evidence: 63 tests pass, 26 final checks pass, full inference is 428.13 rows/s at 2.336 ms/row, and the 5.20 MiB deployed detector has a projected 77.1× single-process capacity factor for a 10,000-station network at a 30-minute cadence.

## Phase B — Development-only causal incident state: complete and rejected

The completed notebook is `notebooks/SkyGuard_AI_GPU_Iteration_04_Causal_Incident_State_Colab.ipynb`; its outputs remain retained as negative-result evidence.

Promotion requires every development block to satisfy:

- minimum point precision at least 75%;
- maximum false alarms at most 0.02 per station-day;
- no point-F1 regression;
- no event-F1 regression greater than one percentage point in any block;
- non-negative mean event-F1 gain.

Iteration 4 completed on the T4 and selected a zero-grace fallback. All selected metrics were identical to Iteration 3. Positive-grace candidates improved incident continuity only by violating the precision and point-F1 safeguards. The causal incident state is therefore not promoted.

## Phase B2 — Episode-balanced weak-fault consensus: complete, candidate only

`notebooks/SkyGuard_AI_GPU_Iteration_05_Weak_Fault_Consensus_Colab.ipynb` was completed on the T4 GPU with the former final tests locked.

It compares episode-balanced CatBoost and LightGBM weak-fault experts for frozen, bias and drift incidents. A rescue alert requires model consensus, causal persistence with a temporal-gap reset, and optional protection against the established genuine-weather channel.

Selection used May–September 2023 and October–December 2023 as an untouched internal confirmation block. The selected fixed policy is the minimum CatBoost/LightGBM consensus score of 0.35 sustained for four emitted readings, with a 180-minute gap reset and genuine-weather guard.

The aggregate development gain is real but small: point F1 increased from 48.44% to 48.73%, event F1 from 60.00% to 60.95%, and event recall from 74.12% to 75.29%. It recovered three additional fault rows and one additional episode without adding false-positive rows. Drift episode recall improved from 25.0% to 37.5%; frozen and bias remained weak. Iteration 5 is therefore frozen as a blind-test candidate, not promoted to production.

## Phase C — Create a genuinely blind benchmark: complete and sealed

The 2024 benchmark has been examined repeatedly. Download and normalize a later full year for the same stations, or reserve new stations/periods never used in any prior comparison.

Required split:

- training/development: existing historical years;
- calibration: a separate later block;
- blind time test: unopened complete year or season;
- blind station test: complete unseen stations;
- weather-event cases present in both tests;
- complete episodes kept within one split.

Completed evidence:

- 124,819 normalized observations from 24 official NOAA/NCEI 2025 station files;
- exact common interval 1 January–24 August 2025;
- 117,944 rows in the known-station future-time stream and 6,875 rows in the unseen-station stream;
- all 13 injected fault/communication families and regional genuine-weather cases in both tests;
- zero row overlap with the 2022–2024 development/benchmark corpus;
- 108 compliant causal features and no model scoring during construction;
- sealed archive SHA-256 `5f8bbad22342295f62c97d9b47628800eaa43df7aec5650ea91b814c6854d859`.

Exit criterion passed. The archive remains `SEALED_NOT_SCORED`.

## Phase D — One-time frozen challenger comparison: complete, promotion failed

`notebooks/SkyGuard_AI_GPU_Blind_2025_Final_Comparison_Colab.ipynb` was run once after all model hashes, policies and development confusion matrices reproduced exactly. The archive must not be reopened for tuning.

The notebook verifies exact model hashes, exact development confusion matrices, the 108-feature contract and the selected policy before reading blind rows. It then reports point metrics, episode metrics, per-fault recall, genuine-weather separation, duplicate replay and dropout replay for both blind tests.

Observed Iteration 5 results were 46.00% point F1 and 82.05% operational episode recall on future time, and 50.96% point F1 and 76.92% operational episode recall on unseen stations. Precision passed at 87.80% and 90.15%, but weather F1 was only 53.02% and 13.64%. The gap detector produced 3,240 and 106 apparent false dropout events on irregular archival streams. Iteration 5 therefore remains research evidence and is not promoted.

## Phase D2 — Iteration 6 communication safety and station transfer: next

Run `notebooks/SkyGuard_AI_GPU_Iteration_06_Communication_Weather_Transfer_Colab.ipynb` on the T4 using 2022–2023 development data only.

The notebook:

- tests whether arrival gaps alone support an automatic fault claim and requires an explicit heartbeat contract when they do not;
- keeps unknown-cadence archive gaps advisory rather than generating unsupported maintenance incidents;
- excludes raw station-identifying values from station-invariant weather and weak-fault challengers;
- balances training by station and episode;
- reserves one development station per regional cluster as pseudo-unseen confirmation;
- requires May–September discovery, October confirmation and pseudo-unseen safeguards before selecting any change.

The former 2025 benchmark is not read or scored by Iteration 6.

## Phase E — Fix weak faults and diagnosis

Priority faults:

1. unseen-station bias;
2. frozen values under natural sensor quantization;
3. gradual drift;
4. timestamp/duplicate faults in unified incident reporting.

Use incident-level targets and a hierarchy:

```text
normal / weather / fault
  -> affected sensor(s)
  -> communication / stuck / shift / noise / scale family
  -> fault subtype
  -> confidence gate or unknown
```

Add duration, station-macro and episode-balanced loss. Evaluate accepted root accuracy together with diagnostic coverage. Do not increase coverage by forcing low-confidence labels.

Exit target: at least 80% accepted root accuracy with at least 60% coverage on both blind tests.

## Phase F — Broaden genuine-weather protection

Current coherent warming is not enough. Inject physically plausible, neighbour-consistent:

- regional temperature rise and fall;
- pressure trough/passages;
- humidity fronts;
- multi-parameter storm-like transitions;
- localized genuine extremes where only a subset of nearby stations agree.

Place weather examples on unseen stations. Target weather F1 at least 80% and weather-to-fault rate no more than 1%.

## Phase G — Make maintenance genuinely predictive

Current health trend is transparent but heuristic. With real maintenance/failure outcomes, train a survival or time-to-event model using only prior alert history, incident severity, recurrence, correction disagreement, and sensor health trajectory.

Until those labels exist, retain the labels “risk trend,” “projected health,” and “maintenance horizon estimate”; do not call the output a calibrated failure probability.

## Phase H — Strengthen deployability evidence

- connect an authenticated IMD AWS stream through the existing adapter contract;
- run 24-hour sustained tests with concurrent station producers;
- report p50, p95 and p99 end-to-end latency;
- test process restart, malformed messages, queue backpressure and cache recovery;
- measure CPU/RAM under 1,000, 10,000 and 100,000 simulated stations;
- add a container or documented Linux service package;
- measure energy with a calibrated meter or supported hardware profiler;
- treat ESP32 as optional research unless hardware becomes available.

## Phase I — Final SIH freeze

Before submission:

- freeze model, thresholds, feature list, hashes and environment;
- open the blind tests once;
- rerun all verification;
- update dashboard, report, notebook and presentation from one generated result block;
- rehearse both internet and no-internet demonstrations;
- prepare answers for input compliance, false alarms, leakage, live labels, scale, energy and safety.

## Expected score path

| Stage | Internal readiness estimate |
|---|---:|
| Current compliant prototype | 78/100 |
| Robust GPU model + blind test | 84–87/100 |
| Diagnosis/weather expansion + load evidence | 88–91/100 |
| Real IMD pilot + maintenance/energy evidence | 92+/100 |

These are planning estimates, not guaranteed SIH scores.

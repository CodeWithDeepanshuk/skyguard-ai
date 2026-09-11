# SkyGuard AI — Iteration 7 Audit and Next Plan

Date: 2026-08-29  
Problem: SIH26073 — AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations

## Executive decision

Iteration 7 is a valid, leakage-safe experiment, but its new weather calibrator and causal TCN policy must **not** replace the accepted Iteration 5 detector. The frozen production candidate therefore remains unchanged. The communication heartbeat contract is valid and can be retained.

This is not a useless iteration. It isolates the dominant limitation: the development curriculum contains too few and too narrow genuine-weather episodes for climate transfer, and too few diverse weak-fault episodes for a sequence model to generalize. More architecture tuning on the same labels is unlikely to solve the problem.

## Reproducibility and integrity

- Executed on Tesla T4 (`cuda`).
- Notebook contains 54 code cells; all 54 were executed.
- No notebook error outputs were present.
- Only 2022 development training and 2023 development validation were used.
- Blind 2025 and former final-test partitions remained sealed.
- Future values, dew point, and evaluator-only `stream_action` were not detector features.
- Result and feature-contract hashes match the integrity receipt.
- Detector observation inputs remain temperature, pressure, and relative humidity. Station, timestamp, cluster, latitude/longitude and heartbeat fields are metadata/context.

## Promotion result

| Component | Iteration 7 outcome | Decision |
|---|---:|---|
| Communication-gap contract | Valid frozen contract | Retain |
| Weather-event calibrator | 0 feasible discovery candidates | Reject |
| Causal TCN weak-fault transfer | 26 discovery candidates, but confirmation failed | Reject |
| Final detector policy | Exactly equal to Iteration 5 reference | Keep Iteration 5 |

## Accepted fallback performance

These are the actual retained metrics. The Iteration 7 rows are identical because the unsafe candidate was correctly rejected.

| 2023 block | Precision | Recall | Point F1 | Event F1 | False-alarm episodes / station-day | Weak-fault episode recall |
|---|---:|---:|---:|---:|---:|---:|
| May–June | 80.15% | 44.86% | 57.52% | 62.96% | 0.01233 | 16.67% |
| July–September | 88.89% | 19.20% | 31.58% | 61.02% | 0.00762 | 41.67% |
| October–December | 83.26% | 41.19% | 55.11% | 59.79% | 0.01742 | 33.33% |

Interpretation: precision and false-alarm control are good, but row-level recall—especially July–September—and weak-fault coverage remain insufficient for a competition-ready claim of best performance.

## Weather calibrator audit

- No L1, L2, or blended climate-calibration policy passed discovery gates.
- Best mean weather F1 on the frontier was only about 8.58%, far below the accepted weather baseline.
- The station table represents the retained fallback, not a successful new calibrator.
- Weather confirmation is empty because no discovery candidate qualified; this is an intentional fail-closed result, not a broken file.

### Root cause

The model-selection scopes each contain only one injected regional weather event:

| Scope | Weather episodes | Climate represented |
|---|---:|---|
| Jan–April tune | 1 | Bengaluru |
| May–June discovery | 1 | Chennai |
| July–September discovery | 1 | Delhi |
| October–December confirmation | 1 | Hyderabad |

The 2022 training data contains only five weather episodes in total, and the current injector implements only a coherent regional temperature-rise event. Therefore the regularized calibrator is asked to learn “weather” from one narrow pattern and transfer to unseen clusters, seasons and event forms. That task is statistically under-identified.

## Causal TCN audit

- Seed 17 best tune AUPRC: 0.08557.
- Seed 41 best tune AUPRC: 0.11336.
- Tune weak-fault prevalence is about 0.47%, so the TCN learned non-random signal, but not enough transferable signal for deployment.
- Training loss continued to improve while AUPRC degraded after the first or second epoch. This is a classic overfitting/domain-transfer warning.

The strongest discovery policy increased mean weak-event recall by 16.67 percentage points, while preserving discovery gates. On October confirmation it instead:

- reduced point F1 by 0.60 percentage points;
- reduced event F1 by 2.90 percentage points;
- reached 0.02042 false alarms per station-day, above the 0.02 budget;
- produced no weak-recall gain.

On pseudo-unseen 2023 stations it produced no gain at all. The TCN policy is therefore not promoted.

## Fault-family position

| Fault family | Retained episode recall | Position |
|---|---:|---|
| Multi-sensor failure, corruption, scaling, spike, timestamp, unit error | 100% | Excellent |
| Sudden drop | 87.50% | Strong |
| Noise | 85.71% | Strong |
| Bias | 42.86% | Needs improvement |
| Drift | 37.50% | Needs improvement |
| Frozen | 16.67% | Critical weakness |
| Duplicate packet in row-level fault table | 0% | Evaluator representation mismatch; runtime duplicate path is separate |

## What Iteration 8 should change

Iteration 8 should be a **development-data curriculum and leave-event-out validation iteration**, not another architecture-only experiment.

1. Preserve the current detector, all Iteration 7 outputs, and sealed 2025 benchmark unchanged.
2. Create independent low-prevalence injection replicas instead of crowding many anomalies into one timeline.
3. Expand genuine-weather simulation to at least six physically coherent families:
   - regional warming/heatwave;
   - regional cooling/cold surge;
   - pressure-front rise/fall;
   - humidity surge/drop;
   - multivariate storm/front transition;
   - localized but genuine extreme with spatial lag.
4. Build at least 96 training weather episodes (4 clusters × 6 families × 4 independent replicas) and 48 validation episodes (4 clusters × 6 families × 2 replicas).
5. Put every climate and event family in each model-selection stage. Split by complete event, station group and time so no event leaks across stages.
6. Expand subtle bias, drift and frozen episodes using severity and duration ladders, plus hard negative natural trends and plateaus.
7. Refit the incident-level LightGBM/CatBoost baseline first. Add TCN only if it contributes independent out-of-fold signal beyond the tree models.
8. Evaluate per event family, climate, station and season—not only pooled rows.

## Iteration 8 acceptance gates

| Target | Minimum gate for promotion |
|---|---:|
| Precision | ≥ 80% in every confirmation block |
| False-alarm episodes / station-day | ≤ 0.02 in every block |
| Weather event F1 | ≥ 75% overall |
| Worst-climate weather event F1 | ≥ 65% |
| Fault-to-weather misclassification | ≤ 1% |
| Weak-fault episode recall | ≥ 65% overall and positive in every block |
| Overall point/event F1 | No regression in any confirmation block |
| Pseudo-unseen stations | Strict positive event-recall or F1 gain |

Only after those development gates pass should one final untouched benchmark be opened once. Neural networks such as a larger TCN, FT-Transformer or TabPFN should not be added before the curriculum is fixed; they cannot manufacture missing event diversity.

## Final conclusion

Iteration 7 is **rejected for model promotion but accepted as a rigorous diagnostic result**. SkyGuard remains strong at precision, false-alarm control, hard-fault detection, causal evaluation and communication safety. Its principal competitive weaknesses are climate/event transfer, subtle bias/drift/frozen detection and seasonal recall stability. The next measurable gain should come from richer, physically valid development episodes and event-level validation, followed by a restrained model comparison.

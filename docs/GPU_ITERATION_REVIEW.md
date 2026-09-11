# GPU iteration review

All three completed notebooks used a Tesla T4 and kept their notebook-level final tests closed. Imported result artifacts are stored under `reports/gpu_iterations/`.

## Iteration 1 — GPU detection ensemble

Methods:

- five-seed CatBoost fault ensemble;
- five-seed weather ensemble;
- causal TCN;
- isotonic versus Platt calibration;
- start/continue incident thresholds.

Selected development result:

- precision 85.15%;
- recall 36.52%;
- point F1 51.11%;
- event recall 80.56%;
- event F1 64.44%;
- false-alarm episodes 0.0136/station-day;
- weather F1 43.70%.

Interpretation: calibration and incident policy were useful, but point recall and weather classification remained weak. The TCN did not earn automatic deployment.

## Iteration 2 — Weak-fault rescue

Methods:

- CatBoost specialists for frozen, bias and drift faults;
- three development time blocks;
- robust policy search with minimum precision and maximum false-alarm constraints;
- weak-fault rescue allowed only after causal persistence.

Selected block results:

| Development block | Precision | Recall | Point F1 | Event recall | Event F1 | False alarms/station-day |
|---|---:|---:|---:|---:|---:|---:|
| May–June | 80.00% | 44.44% | 57.14% | 72.73% | 60.38% | 0.0123 |
| July–September | 88.61% | 18.67% | 30.84% | 66.67% | 60.00% | 0.0082 |
| October–December | 83.26% | 41.19% | 55.11% | 80.56% | 59.79% | 0.0174 |

The incident-level rescue improved event F1 over the fixed Phase 10 path in all three blocks. The worst-block point recall remained only 18.67%. Frozen episode recall was 16.67%, drift 25.00%, and bias 42.86% across development.

Verdict: **significant incident-policy improvement, but not a complete weak-fault solution**. The CatBoost ensemble is the most promising challenger for a future blind test.

## Iteration 3 — Frozen rules and communication replay

The frozen-value rule search found no configuration that generalized across all development blocks without violating safeguards. The correct decision was to keep the Iteration 2 model rather than force a misleading gain.

The communication replay was successful:

- 181,470 source rows and 181,486 emitted packets;
- 16 duplicate true positives;
- zero duplicate false positives and zero false negatives;
- duplicate precision and recall 100%;
- all 10 duplicate episodes detected;
- detector used station ID, timestamp, temperature, pressure and humidity only;
- injected `stream_action` was not used by the detector.

Verdict: **no main detection-score gain, but complete proof that duplicate packets are solved by the correct stateful layer**.

A later attempt to merge a simple non-positive-time rule into the row classifier was also rejected. It produced 35 validation false alarms; packet identity and order must remain stateful transport evidence.

## Is improvement significant across iterations?

Yes, but it is uneven:

- Iteration 1 established a calibrated high-precision GPU baseline.
- Iteration 2 materially improved incident-level robustness across three blocks.
- Iteration 3 correctly rejected a non-generalizing frozen rule and added strong communication-fault evidence.

This is scientifically better than claiming every iteration raised F1. A failed promotion test is useful because it prevents overfitting.

## Iteration 4 — causal incident-state coverage

Iteration 4 was completed on a Tesla T4 with no execution errors and with `final_tests_opened=false`. It tested alert persistence after a valid Iteration 3 trigger.

The result was a correct rejection:

- all three selected Iteration 4 block metrics were identical to Iteration 3;
- the four configurations that passed every safeguard had zero grace minutes, so they made no new predictions;
- the best non-zero-grace configuration gained 5.25 percentage points of mean event F1, but its minimum precision fell to 43.95% and its mean point F1 fell by 5.68 percentage points.

Verdict: **do not promote causal incident state**. It improves event continuity only by labelling too many normal observations as faulty.

## Should work continue?

Yes, but not with more alert-persistence tuning. Iteration 5 is a final development-only weak-fault experiment before building a fresh blind benchmark:

1. episode-balanced CatBoost and LightGBM weak-fault experts;
2. conservative model consensus, causal persistence with gap resets, and genuine-weather protection;
3. policy selection on May–September 2023 only;
4. independent October–December confirmation;
5. automatic fallback to the Iteration 3 detector if any safety gate fails.

Do not jump directly to larger transformers. The dataset has too few examples for reliable fault-by-sensor neural networks. After Iteration 5, create a new blind benchmark before promoting any GPU model to production.

# SkyGuard AI — Iteration 9 audit and Iteration 10 corrective plan

## Executive decision

Iteration 9 is a **valid, reproducible, non-promotable experiment**. The returned result passed 12 of 23 functional gates. JSON and CSV values reconcile exactly, all three stress seeds are present, confidence-interval means recompute correctly, all 57 notebook code cells completed with no saved runtime errors, model files load successfully, and no locked 2024/2025 data was opened.

The accepted Iteration 5 deployment must remain unchanged. Iteration 9 must not be integrated into the live API yet.

## What genuinely improved over Iteration 8

### Main confirmation

| Domain | Metric | Iteration 8 | Iteration 9 | Change |
| --- | --- | ---: | ---: | ---: |
| India | Precision | 0.8421 | 0.8565 | +0.0144 |
| India | Point F1 | 0.5494 | 0.5265 | -0.0229 |
| India | Event F1 | 0.6526 | 0.6279 | -0.0247 |
| India | Weather F1 | 0.3400 | 0.3782 | +0.0382 |
| DWD all | Precision | 0.6667 | 0.9118 | +0.2451 |
| DWD all | Point F1 | 0.2245 | 0.2226 | -0.0019 |
| DWD all | Event F1 | 0.3051 | 0.4000 | +0.0949 |
| DWD all | Weather F1 | 0.9084 | 0.9409 | +0.0326 |
| DWD holdout | Precision | 0.7656 | 0.9800 | +0.2144 |
| DWD holdout | Point F1 | 0.4516 | 0.4828 | +0.0311 |
| DWD holdout | Event F1 | 0.4211 | 0.6154 | +0.1943 |
| DWD holdout | Weather F1 | 0.9038 | 0.9389 | +0.0351 |

The residual-only contract successfully removed the obvious geography shortcut and produced excellent DWD precision, unseen-station event F1, weather recognition and false-alarm control. This is a meaningful improvement, not a failed iteration with no value.

### Three-seed DWD confirmation stability

| Metric | DWD all mean | DWD all 95% seed interval | DWD holdout mean |
| --- | ---: | ---: | ---: |
| Precision | 0.9275 | 0.9118–0.9576 | 0.9854 |
| Point F1 | 0.2841 | 0.2226–0.3792 | 0.4615 |
| Event F1 | 0.4527 | 0.3429–0.6154 | 0.5051 |
| False alarms/station/day | 0.00478 | 0.00359–0.00615 | 0.00342 |
| Weather F1 | 0.9354 | 0.9280–0.9409 | 0.9352 |
| Fault-to-weather rate | 0.01705 | 0.01382–0.02301 | 0.00218 |
| Drift episode recall | 0.1667 | 0.0–0.5 | 0.0 |

Precision, false-alarm control and DWD weather recognition are now stable across injection seeds. Point recall, drift and fault-versus-weather separation are not.

## Why Iteration 9 cannot be promoted

Eleven gates failed:

1. Main point F1 regressed versus Iteration 8.
2. Main event F1 regressed in India.
3. Weak-fault recall regressed in India from 0.5556 to 0.3333.
4. India confirmation weather F1 is 0.3782, below 0.65.
5. Worst supported climate weather F1 is below 0.65.
6. Main fault-to-weather rate exceeds 0.01.
7. Multi-seed point F1 regresses versus Iteration 8.
8. Multi-seed fault-to-weather rate exceeds 0.01.
9. Mean drift episode recall is below 0.50.
10. Detected-fault root-cause macro F1 is below 0.70.
11. Detected-fault root-cause accuracy is below 0.80 in India.

## The central modeling failure

Iteration 9 used a high row-level fault threshold (0.8909) to obtain precision and low false alarms. That made the detector conservative:

- India confirmation recall is approximately 0.38.
- DWD-all confirmation recall is approximately 0.13.
- DWD-holdout confirmation recall is approximately 0.32.

The detector is excellent when it raises an alert, but it misses too many affected rows and weak incidents. Lowering a single threshold is not sufficient because tune false alarms rise before weak-fault recall becomes reliable.

The second failure is architectural. Fault and weather are independent binary models followed by a weather veto. The weather calibrator assigns a positive coefficient to the fault residual score (+0.334). It therefore interprets some strong fault evidence as weather evidence. This explains why DWD weather F1 is high while 1.4–2.3% of fault rows are still routed to weather, and why India fault-to-weather rises to 3.4%.

The third failure is diagnosis granularity. Root cause is classified row by row. Detected-row accuracy appears reasonable (India 0.765, DWD 0.855), but macro F1 exposes class collapse (India 0.620, DWD 0.533). DWD detected drift has no true detected support; India noise and spike diagnosis are weak. SIH expects root cause for an alert/incident, so incident-level diagnosis is the correct target.

## Iteration 10: hierarchical incident-state solution

Iteration 10 should not add another generic neural network. The bottleneck is decision structure and event support, not insufficient model complexity.

### Stage A — high-recall candidate generator

Retain the Iteration 9 residual LightGBM ensemble and hard physical rules. Generate candidate evidence at a lower score threshold without immediately creating an alert. Preserve:

- residual score and causal z-score;
- Isolation Forest and LSTM scores;
- 3/6/12/24-hour slope and CUSUM;
- frozen-run and communication state;
- neighbour disagreement and regional agreement.

### Stage B — causal incident aggregation

Convert row scores into station/sensor incidents using causal windows:

- instant path for impossible values, severe spikes, unit/scaling errors and communication corruption;
- persistence path using k-of-n evidence for bias, drift, noise and frozen sensors;
- incident features: duration, score maximum/mean/slope, CUSUM growth, number of affected sensors, neighbour disagreement, regional spatial extent and recovery behaviour.

Persistence should recover weak faults while keeping false alarms low; it is safer than globally lowering the row threshold.

### Stage C — mutually exclusive fault/weather triage

Replace independent binary weather vetoes with an incident-level three-state classifier:

1. normal/advisory;
2. genuine regional weather;
3. sensor/data fault.

Alternatively use a pairwise `P(fault | candidate incident)` discriminator after Stage A. Train with episode-balanced weights and prohibit station/domain identifiers. The fault score must not act as positive evidence for weather unless spatial coherence independently supports it.

Core triage signals:

- fraction and count of nearby stations agreeing;
- fraction of sensors changing coherently;
- residual isolation of the target station;
- spatial extent and duration;
- pressure/temperature/humidity trend consistency;
- communication/timestamp evidence;
- severity of hard physical violations.

### Stage D — incident-level hierarchical root cause

First classify the broad state:

- communication/data-order fault;
- abrupt sensor fault;
- persistent sensor degradation;
- multi-sensor/power failure.

Then run family specialists:

- abrupt: spike, sudden drop, unit/scaling error;
- persistent: bias, drift, frozen, noise;
- communication: dropout, duplicate, timestamp disorder, corruption;
- multi-sensor: constant or corrupted multi-parameter failure.

Aggregate predictions across the full incident and evaluate macro F1 per incident, not per row.

### Stage E — targeted drift rescue

Build a dedicated drift state machine from neighbour-residual slope, CUSUM and monotonic persistence. Require sustained evidence and a recovery/reset condition. Evaluate detection latency and episode recall. The target remains at least 0.50 recall without exceeding 0.02 false alerts/station/day.

## Data required before Iteration 10

The current DWD weather curriculum is strong, but India regional-weather support remains too narrow. Add official 2022–2023 development-only Indian station clusters around Delhi, Hyderabad, Chennai and Bengaluru using public station observations. Each regional group needs multiple nearby stations so a genuine event can be distinguished from a single-station fault.

Use fresh injection seeds and station-season blocks. All Iteration 9 confirmation rows are now diagnostic evidence and may not be reused as an untouched final confirmation. The locked 2024/2025 data must remain closed until the new development gates pass.

## Iteration 10 acceptance gates

- Precision ≥ 0.80 in India, DWD and pseudo-unseen stations.
- False alerts ≤ 0.02 incidents/station/day.
- No point-F1 or event-F1 regression against the best retained baseline per domain.
- India and DWD genuine-weather F1 ≥ 0.75 where supported; minimum climate F1 ≥ 0.65.
- Fault-to-weather ≤ 0.01 in every confirmation domain.
- Drift episode recall ≥ 0.50, including unseen stations.
- Incident root-cause macro F1 ≥ 0.70 and accuracy ≥ 0.80.
- Three or more new confirmation seeds with seed-level intervals.
- No station/domain identifiers, future observations or locked-year data.

Only after all development gates pass should one locked confirmation be opened.

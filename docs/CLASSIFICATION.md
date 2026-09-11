# Phase 10 event, fault and root classification

## Operational decisions

Each detector-visible observation becomes:

- `normal`;
- `genuine_weather`;
- `sensor_fault`.

Fault incidents receive one of 12 probable root causes or `unknown_fault` when confidence is insufficient. Dropout is a stateful stream-gap event rather than a value-row class.

## Deployed method

- strict 108-feature three-parameter allowlist;
- calibrated regularized LightGBM event model;
- regional neighbour-weather evidence;
- separate validation-selected known/new-station thresholds;
- causal incident persistence;
- calibrated LightGBM root model with incident aggregation and abstention;
- deterministic duplicate/timestamp handling in the stream layer;
- advisory causal TCN, excluded from automatic alerts after failing the false-alarm gate.

L1/L2 regularization, multi-window slopes, CUSUM, monotonic runs, freeze evidence, climatology and neighbour-residual trends are already present.

## Current compliant results

| Split | Precision | Recall | F1 | AUCPR | Episode recall | False alarms/station-day |
|---|---:|---:|---:|---:|---:|---:|
| Unseen time | 71.47% | 41.50% | 52.51% | 48.45% | 79.17% | 0.0429 |
| Unseen stations | 89.89% | 32.00% | 47.20% | 41.95% | 63.33% | 0.0064 |

Unseen-time weather F1 is 67.71% and weather-to-fault rate is 1.335%. Accepted root accuracy is 69.98% at 26.24% coverage on unseen time, and 87.50% at 19.20% coverage on unseen stations.

## Historical Phase 5 warning

Phase 5 achieved higher unseen-station F1 but used `temperature_dewpoint_spread_c`. The SIH problem permits only temperature, pressure and relative humidity, so Phase 5 is exploratory history and not the deployment result.

## Remaining weaknesses

- unseen-station recall is 32%;
- unseen-station bias and duplicate row recall are 0%;
- frozen/drift weak-fault performance varies by station and season;
- weather cases are absent from the unseen-station benchmark;
- root coverage is below 27%;
- 2024 has been inspected repeatedly and needs replacement by a new blind holdout.

## Reproduction

```powershell
python src/data/generate_phase10_features.py
python src/data/finalize_phase10.py
python src/data/profile_competition_readiness.py
```

Source of truth: `reports/phase10_final.json`.

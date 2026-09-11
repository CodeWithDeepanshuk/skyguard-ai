# Model card — SkyGuard-P10-compliant

## Intended use

Research and SIH demonstration of anomaly screening for Automatic Weather Station observations. The system prioritizes observations for review; it does not certify meteorological truth or authorize unattended replacement.

## Inputs

- temperature in °C;
- atmospheric pressure in hPa;
- relative humidity in percent;
- causal history of those three parameters;
- backward-aligned values of those same parameters from configured neighbouring stations.

## Explicit exclusions

The detector does not use dew point, wind, rainfall, visibility, future observations, source quality labels, injected fault metadata, original clean targets, episode IDs or stream-action labels. Absolute calendar sine/cosine shortcuts are excluded from Phase 10.

## Architecture

- 108 causal features;
- calibrated regularized LightGBM event model;
- validation-selected known/new-station thresholds and causal persistence;
- incident-aggregated calibrated 12-class LightGBM diagnosis;
- confidence abstention;
- separate deterministic stateful communication checks;
- advisory causal TCN excluded from automatic alert decisions.

## Main benchmark performance

### Standard Compliant Baseline (Phase 10)
| Split | Precision | Recall | F1 | AUCPR | Episode recall | False alarms/station-day |
|---|---:|---:|---:|---:|---:|---:|
| Unseen time (2024) | 71.47% | 41.50% | 52.51% | 48.45% | 79.17% | 0.0429 |
| Unseen stations | 89.89% | 32.00% | 47.20% | 41.95% | 63.33% | 0.0064 |

### Upgraded Spatial Buddy + Dual-Trigger Model (115 Features)
*Model artifact: `reports/upgraded_spatial_model/upgraded_spatial_model.joblib`*
| Split | Precision | Recall | F1 | Episode recall | False alarms/station-day |
|---|---:|---:|---:|---:|---:|
| Unseen time (2024) | **81.42%** (+9.95%) | 38.08% | 51.89% | 75.69% | **0.0225** (-47%) |
| Unseen stations | **86.81%** | 31.60% | 46.33% | 58.33% | **0.0085** |

### National Network Scope & Scalability
- **All-India Station Registry**: 545 verified Indian weather stations mapped in `config/all_india_aws_network.csv` across 8 climate zones (410 active into 2024+).
- **Processing Throughput**: 204.7 rows/second single-core CPU throughput, yielding a **36.8× capacity factor** for a 10,000-station network (or **$365\times$ capacity** for the 1,008 IMD AWS stations).

## Known limitations

- weak unseen-station bias, drift and frozen faults are often missed;
- mean latency is high for some slow faults;
- unseen-station weather generalization is not measured;
- root diagnosis coverage is below 27%;
- fault labels are controlled injections on genuine observations, not confirmed maintenance outcomes;
- live METAR humidity is derived and pressure is QNH rather than a direct IMD AWS feed;
- health forecasts are heuristic;
- corrections and intervals shift by sensor and year;
- distributed scale and energy have not been measured directly.

## Safety and interpretation

- preserve raw reported values;
- label causes as probable;
- abstain when uncertain;
- keep correction advisory;
- keep humidity review-only;
- use offline replay for repeatable judging;
- use live data to demonstrate operation, not accuracy;
- require operator review and an official IMD acceptance process before production.

## Versioned artifacts

- `models/phase10_final.joblib`
- `models/phase10_climatology.joblib`
- `reports/phase10_final.json`
- `reports/competition_readiness.json`
- `data/predictions_phase10/`

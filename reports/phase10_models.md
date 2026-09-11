# SkyGuard Phase 10 compliant production result

The deployed detector uses only temperature, pressure, relative humidity, causal station history and same-parameter neighbour evidence. Dew point and absolute calendar shortcuts are excluded.

| Split | Precision | Recall | F1 | AUCPR | Episode recall | False alarms/station-day | Root coverage | Accepted root accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024 unseen time | 71.47% | 41.50% | 52.51% | 48.45% | 79.17% | 0.0429 | 26.24% | 69.98% |
| 2024 unseen stations | 89.89% | 32.00% | 47.20% | 41.95% | 63.33% | 0.0064 | 19.20% | 87.50% |

The causal TCN remains advisory because its unseen-station false alarms exceeded the deployment constraint. Phase 5 is retained only as a historical noncompliant comparison because its leading feature used measured dew point.

Machine-readable source of truth: `reports/phase10_final.json`.

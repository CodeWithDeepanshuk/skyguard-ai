# SkyGuard Phase 6.1 safe-repair improvement

Dedicated sensor-change models recover correction opportunities independently of root-cause classification. Review and auto-repair thresholds were frozen on 2023 before 2024 evaluation.

## Frozen 2024 results

| Test | Sensor | Tier | Precision | Coverage | Corrected MAE | Interval coverage | False corrections | Mean false-correction harm |
|---|---|---|---:|---:|---:|---:|---:|---:|
| time_test | temperature | review | 0.6379 | 0.3953 | 1.7797 | 0.9881 | 239 | 3.3126 |
| time_test | temperature | auto | 1.0000 | 0.0329 | 1.1569 | 0.9714 | 0 | 0.0000 |
| time_test | pressure | review | 0.6717 | 0.7504 | 1.5305 | 0.8816 | 260 | 2.5762 |
| time_test | pressure | auto | 1.0000 | 0.0056 | 2.2943 | 1.0000 | 0 | 0.0000 |
| time_test | humidity | review | 0.5994 | 0.7069 | 12.3332 | 0.8081 | 282 | 20.6090 |
| time_test | humidity | auto | 0.0000 | 0.0000 | n/a | n/a | 0 | 0.0000 |
| station_test | temperature | review | 0.7636 | 0.3559 | 1.3701 | 0.9048 | 13 | 3.9009 |
| station_test | temperature | auto | 1.0000 | 0.0678 | 1.9476 | 0.6250 | 0 | 0.0000 |
| station_test | pressure | review | 0.6790 | 0.8209 | 1.3313 | 0.8727 | 26 | 3.4314 |
| station_test | pressure | auto | 1.0000 | 0.0299 | 1.4638 | 1.0000 | 0 | 0.0000 |
| station_test | humidity | review | 0.6892 | 0.4722 | 5.8280 | 0.9412 | 23 | 13.2145 |
| station_test | humidity | auto | 0.0000 | 0.0000 | n/a | n/a | 0 | 0.0000 |

## Safety rule

Only the auto tier may be applied without review. It requires the high-precision sensor threshold, at least three causal estimates, and an adaptive interval narrower than the sensor-specific safety limit. Review-tier outputs remain advisory.

The test metrics are reported without changing thresholds after inspection. Confirmed operational deployment would still require real maintenance labels and operator approval.

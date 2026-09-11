# SkyGuard Phase 5 fault/event classifier

> Historical noncompliant experiment only. This model used a dew-point-derived feature and is not the SIH submission model. Use `reports/phase10_final.json` for current results.

The classifiers were trained on 2022, calibrated and frozen on 2023, then evaluated on the two untouched 2024 holdouts.

## Frozen-test results

| Split | Fault precision | Fault recall | Fault F1 | AUCPR | Episode recall | Weather recall | Weather false-alarm rate | Root accuracy (oracle) | Root accuracy (end-to-end) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| time_test | 0.7692 | 0.3982 | 0.5247 | 0.4677 | 0.7431 | 0.8653 | 0.0170 | 0.5041 | 0.1700 |
| station_test | 0.7857 | 0.4400 | 0.5641 | 0.5183 | 0.7500 | 0.0000 | 0.0000 | 0.4280 | 0.1800 |

## Interpretation

The binary fault metrics are directly comparable with Phase 4 because they use the same detector-visible rows, weather hard negatives, and station-day definition. Oracle root-cause accuracy measures diagnosis after a fault is known; end-to-end accuracy also includes missed detections and abstentions.

Dropout remains excluded from row-level classification and will be measured as a missing stream interval in Phase 7.

## Artifacts

- Model bundle: `models/phase5_classifiers.joblib`
- Frozen policy: `models/phase5_policy.json`
- Runtime: 179.23 seconds
- Random seed: 26073

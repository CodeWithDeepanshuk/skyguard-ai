# SkyGuard Phase 4 baseline report

Thresholds were selected on 2023 validation only, saved, and frozen before the 2024 time and unseen-station files were loaded.

## Test results

| Split | Detector | Precision | Recall | F1 | AUCPR | False alarms/station-day | Episode recall | Weather FPR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| time_test | qc_rules | 0.1996 | 0.1662 | 0.1814 | 0.0519 | 0.1728 | 0.4236 | 0.0000 |
| time_test | hampel | 0.0226 | 0.0516 | 0.0314 | 0.0163 | 0.5784 | 0.3889 | 0.0388 |
| time_test | ewma | 0.0590 | 0.0397 | 0.0474 | 0.0233 | 0.1639 | 0.3889 | 0.0024 |
| time_test | neighbor | 0.2071 | 0.1076 | 0.1416 | 0.1056 | 0.1067 | 0.5000 | 0.0000 |
| time_test | combined | 0.0730 | 0.1744 | 0.1030 | 0.0399 | 0.5736 | 0.4653 | 0.0049 |
| time_test | isolation_forest | 0.0702 | 0.2754 | 0.1119 | 0.0526 | 0.9451 | 0.6597 | 0.0376 |
| station_test | qc_rules | 0.3051 | 0.0720 | 0.1165 | 0.0970 | 0.0291 | 0.2833 | 0.0000 |
| station_test | hampel | 0.0556 | 0.1440 | 0.0802 | 0.0423 | 0.4337 | 0.4500 | 0.0000 |
| station_test | ewma | 0.0745 | 0.1240 | 0.0931 | 0.0805 | 0.2729 | 0.4167 | 0.0000 |
| station_test | neighbor | 0.6939 | 0.1360 | 0.2274 | 0.2292 | 0.0106 | 0.4833 | 0.0000 |
| station_test | combined | 0.0841 | 0.1080 | 0.0946 | 0.0662 | 0.2084 | 0.4167 | 0.0000 |
| station_test | isolation_forest | 0.1370 | 0.2560 | 0.1785 | 0.0914 | 0.2856 | 0.5833 | 0.0000 |

## What the baselines establish

- Best 2024 time-holdout point F1: qc_rules (0.1814).
- Best unseen-station point F1: neighbor (0.2274).
- Highest unseen-station episode recall: isolation_forest (0.5833).
- Neighbour comparison rejects the regional-weather hard negatives well and has the lowest unseen-station false-alarm rate.
- Bias, gradual drift, duplicate packets, and some frozen faults remain difficult; these are the main targets for the supervised fault classifier and stateful replay phases.

## Evaluation boundary

Point metrics include every detector-visible row. Dropout rows are excluded because no value reaches a row-level detector; dropout evaluation is deferred to the stateful replay/communication-gap evaluator in Phase 7. Regional weather scenarios remain negative hard cases and are included in false-positive metrics.

## Reproducibility

- Training rows used by Isolation Forest: 179,852
- Isolation Forest fit time: 5.917 seconds
- Saved model bytes: 5,287,191
- Total Phase 4 runtime: 155.576 seconds
- Random seed: 26073

# SkyGuard deterministic QC baseline

This is an alert-profile report on genuine observations, not an accuracy report. Precision and recall require the labelled fault-injection dataset built in Phase 2.

## Summary

- Observations processed: 578,448
- Alerts generated: 16,243
- Alerts per 1,000 observations: 28.080
- Processing time: 32.55 seconds
- Throughput: 17,769 observations/second

## Alerts by rule

| Rule | Alerts |
|---|---:|
| COMMUNICATION_GAP | 2,322 |
| FROZEN_SENSOR | 233 |
| MISSING_VALUE | 8,969 |
| RATE_OF_CHANGE | 3,873 |
| SOURCE_QUALITY_FLAG | 846 |

## Alerts by severity

| Severity | Alerts |
|---|---:|
| high | 3,873 |
| medium | 12,370 |

## Configured station cadence

| Station | Expected minutes |
|---|---:|
| 42131099999 | 180.00 |
| 42181099999 | 30.00 |
| 42182099999 | 180.00 |
| 42189099999 | 180.00 |
| 42348099999 | 30.00 |
| 42361099999 | 180.00 |
| 42705699999 | 30.00 |
| 43021099999 | 30.00 |
| 43086099999 | 180.00 |
| 43128099999 | 30.00 |
| 43128599999 | 30.00 |
| 43181099999 | 30.00 |
| 43213099999 | 180.00 |
| 43233099999 | 180.00 |
| 43245099999 | 180.00 |
| 43275099999 | 180.00 |
| 43278099999 | 180.00 |
| 43279099999 | 30.00 |
| 43284099999 | 30.00 |
| 43295099999 | 180.00 |
| 43302599999 | 30.00 |
| 43321099999 | 30.00 |
| 43329099999 | 180.00 |
| 43331099999 | 180.00 |

## Interpretation

Communication gaps and frozen-value warnings may include true reporting-schedule changes. They become anomaly labels only when created by the controlled injector or independently confirmed. Thresholds must be tuned on 2023 validation data, then frozen before 2024 testing.

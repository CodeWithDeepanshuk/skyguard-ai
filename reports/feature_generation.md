# SkyGuard feature-generation report

- Model feature columns: 72
- Label columns excluded from model inputs: True
- Total rows transformed: 556,624
- Generation time: 432.89 seconds

## Outputs

| Split | Rows | Compressed bytes | Neighbour context |
|---|---:|---:|---|
| train | 182,362 | 28,871,182 | train stations |
| validation | 181,470 | 28,777,918 | validation stations |
| time_test | 182,276 | 28,802,431 | time_test stations |
| station_test | 10,516 | 2,122,705 | time_test development stations |

All rolling and EWMA statistics use prior observations only. Neighbour alignment selects the latest observation at or before the query timestamp within 180 minutes. The station-holdout split uses 2024 development stations as value-only neighbour context.

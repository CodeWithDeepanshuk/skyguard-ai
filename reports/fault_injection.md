# SkyGuard labelled fault dataset

- Global seed: 26073
- Output splits: 4
- Fault types: 13
- Total fault episodes: 546
- Total genuine-weather scenarios: 13
- Total labelled fault rows: 6,545

## Split summary

| Split | Rows | Fault episodes | Weather scenarios | Anomaly rows | Anomaly % |
|---|---:|---:|---:|---:|---:|
| train | 182,362 | 195 | 5 | 2,510 | 1.3764% |
| validation | 181,470 | 130 | 4 | 1,696 | 0.9346% |
| time_test | 182,276 | 156 | 4 | 2,064 | 1.1323% |
| station_test | 10,516 | 65 | 0 | 275 | 2.6151% |

## Fault episodes by type

| Fault type | Episodes |
|---|---:|
| bias | 42 |
| communication_corruption | 42 |
| drift | 42 |
| dropout | 42 |
| duplicate_packet | 42 |
| frozen_sensor | 42 |
| multi_sensor_failure | 42 |
| noise | 42 |
| scaling_error | 42 |
| spike | 42 |
| sudden_drop | 42 |
| timestamp_error | 42 |
| unit_error | 42 |

## Label meaning

- `is_anomaly=1`: synthetic sensor, record, timestamp, unit, or communication fault.
- `is_weather_event=1`: coherent synthetic regional weather scenario and therefore a non-fault hard negative.
- `stream_action=drop|duplicate|timestamp_shift`: instruction for the later replay engine.
- Original values and timestamps are retained in dedicated columns for correction and audit.

No generated episode crosses a split boundary. The station-holdout test contains only the four stations excluded from development.

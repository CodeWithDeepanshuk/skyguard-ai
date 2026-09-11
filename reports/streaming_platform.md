# SkyGuard Phase 7 offline replay and API

## Replay profiles

| Scenario | Source rows | Emitted | Dropped | Alerts | Rows/second | Mean latency (ms) |
|---|---:|---:|---:|---:|---:|---:|
| pressure_drift | 483 | 483 | 0 | 0 | 11044.3 | 0.0905 |
| regional_weather | 432 | 432 | 0 | 1 | 12043.6 | 0.0830 |
| dropout | 67 | 24 | 43 | 1 | 33732.8 | 0.0296 |
| packet_errors | 12 | 12 | 0 | 2 | 5924.5 | 0.1688 |

## Stateful communication evidence

- Dropout detected from the next-packet gap: True
- Repeated packet detected: True
- Backward timestamp detected: True

All evidence, scenario, replay-control, readings, alerts, incident, repair, health, and metrics endpoints passed offline API smoke checks.

Start with `python src/data/run_api.py`, then open `http://127.0.0.1:8000/docs`.

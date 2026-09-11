# Phase 7 offline replay and API platform

## Packaged judge scenarios

- `pressure_drift`: 483 source rows from five Delhi-cluster stations, including the full pressure drift at Station 42181099999.
- `regional_weather`: 432 rows from five Bengaluru-cluster stations, including 229 coherent regional-temperature rows and no injected faults.
- `dropout`: 67 source rows surrounding a 43-packet, 21-hour communication outage.
- `packet_errors`: 12 rows containing a repeated transport packet and a backward emitted timestamp.

All scenario rows come from the frozen 2024 benchmark. Files are compressed and SHA-256 verified.

## Stateful checks

The replay engine processes simulator arrival order. It skips dropped rows, detects the resulting gap when the next packet arrives, tracks transport packet identity for duplicates, and compares emitted timestamps with station state for disorder. The packaged simulator supplies an explicit expected cadence and heartbeat SLA, so its dropout scenario may create an automatic `communication_gap` alert. A source without both contract fields produces only `unverified_data_gap`, never an automatic sensor-fault or maintenance claim.

Exact weather-value repetition is not treated as a duplicate. Duplicate detection requires repeated packet identity or a same-timestamp/value fallback.

## Local persistence

Normal API operation stores replay readings and alerts in `data/runtime/replay.db` using SQLite. Reset clears the active replay tables without modifying benchmark, model, incident, or report artifacts.

## API

Start the service:

```powershell
python src/data/run_api.py
```

Open `http://127.0.0.1:8000/docs` for the interactive offline API.

Endpoints cover health, scenarios, load/reset/step/status controls, latest readings, stateful alerts, station metadata, incidents, safe repair actions, sensor health, and frozen model metrics.

## Performance

The packaged scenarios process at approximately 5,900–33,700 source rows per second with mean per-row replay latency below 0.17 ms in the measured run. The profiler’s Python allocation peak is approximately 1.6 MB; model/data artifacts are served from local disk.

These figures profile replay and persistence, not fresh model training.

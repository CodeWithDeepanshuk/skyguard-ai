# Deterministic quality-control engine

## Implemented rules

- missing primary variables
- configured physical bounds
- NOAA source-quality flags
- dew-point/temperature consistency
- duplicate station timestamps
- out-of-order timestamps
- communication gaps based on station cadence
- temperature, pressure, and humidity rate-of-change
- per-sensor frozen values
- simultaneous multi-sensor freeze

The engine is stateful per station and processes one observation at a time, so the same implementation can be used for batch evaluation and the later streaming replay.

Pressure rate-of-change is only calculated when consecutive readings use the same pressure source. This prevents artificial alerts when data switch between sea-level pressure and altimeter-pressure fields.

## Full-corpus baseline

- Observations: 578,448
- Alerts: 16,243
- Alerts per 1,000 observations: 28.0803
- Throughput: approximately 17,700 observations/second
- Automated tests: 8 passing

Alert counts on genuine but unlabelled observations are an operational profile, not precision or recall. Accuracy metrics begin after controlled anomaly injection.

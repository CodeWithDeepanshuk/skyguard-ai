# Synthetic fault dataset design

## Why controlled injection is required

The NOAA/NCEI observations are genuine, but they do not include reliable confirmed sensor-failure labels. Controlled injection gives exact ground truth: original value, corrupted value, affected sensor, fault type, episode boundaries, severity, and seed.

Synthetic faults must always be described as simulated faults applied to real observations—not as historical failures recorded by NOAA or IMD.

## Fault classes

- spike
- sudden drop
- constant bias
- gradual drift
- excessive noise
- frozen sensor
- communication dropout
- duplicate packet
- timestamp error
- Celsius/Fahrenheit unit error
- pressure/humidity scaling error
- communication corruption
- multi-sensor failure

## Genuine-weather hard negatives

Regional temperature scenarios apply a coherent rise across at least three stations in one cluster. They are labelled `is_weather_event=1` and `is_anomaly=0`. These examples test whether the later neighbour model avoids calling region-wide agreement an individual sensor fault.

## Stream actions

Value faults are written directly into corrupted sensor columns. Record-level faults use instructions consumed by the replay engine:

- `drop`: omit the marked row
- `duplicate`: emit the marked row twice
- `timestamp_shift`: apply `timestamp_offset_seconds`
- `emit`: process normally

## Auditability

Every labelled row retains original temperature, pressure, humidity, and timestamp. The episode manifest records all episode metadata, and the generated-file manifest stores SHA-256 hashes and the fixed global seed `26073`.

## Generated result

- Fault episodes: 546
- Fault classes: 13, with 42 episodes of each class across all splits
- Regional weather scenarios: 13
- Fault-labelled rows: 6,545
- Total episodes in manifest: 559
- Automated tests after Phase 2: 12 passing
- Independent labelled-data validation errors: zero

# Iteration 13 Scientific Methodology

Iteration 13 evaluates anomaly detectors on copies of genuine authenticated IMD AWS observations. Source windows are split by station and time before independently seeded injection. This prevents one source row or derived copy from crossing train, validation, future-test or unseen-station-test boundaries.

The primary detector uses temperature, MSLP pressure and relative humidity. Station identity, timestamps, coordinates and neighbouring relationships are context only. Rolling features use current/prior observations while their baseline is shifted to prior observations; no centered windows or future neighbours are used.

The benchmark covers spike, frozen sensor, missing block, calibration drift, step bias, noise-burst/power-related signature, data corruption, multivariate inconsistency and slow degradation. Magnitudes depend on causal local MAD/IQR and severity. Raw measurements are immutable; modified values, originals, parameters, seed, partition and snapshot hash remain attached.

Model progression is range QC, robust temporal statistics, Isolation Forest, supervised HistGradientBoosting, then hybrid event-aware fusion. Supervised scores are calibrated only on validation data. Final reports separate future-time and unseen-station results, fault type/severity, point and event metrics, false alerts per station-day and delay.

The event gate treats coherent neighbour movement as evidence against an isolated sensor fault. It reports `possible_genuine_meteorological_event`, not a specific storm/heatwave fact. Spatial context is unavailable unless at least two exact-time neighbours within the configured radius exist.

Promotion criteria are frozen before final evaluation. Phase 10 is unchanged until same-benchmark paired evidence satisfies precision, recall, false-alarm, unseen-station, calibration and runtime requirements.

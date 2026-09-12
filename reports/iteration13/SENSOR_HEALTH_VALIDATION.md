# Sensor Health Validation

Status: **IMPLEMENTED, NOT VALIDATED ON IMD HISTORY**.

The transparent 0–100 score subtracts bounded penalties for short/long anomaly rates, drift, noise, missingness, freezing, residual bias and residual variance. Fewer than 24 historical rows returns `INSUFFICIENT_HISTORY`. It reports no remaining useful life.

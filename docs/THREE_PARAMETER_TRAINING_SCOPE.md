# SkyGuard three-parameter training scope

The Colab notebook `notebooks/SkyGuard_IMD_GPU_Training_Review.ipynb` trains separate outputs for temperature, pressure and relative humidity using multivariate station history. It compares persistence, LightGBM regression and causal TCN regression. Isolation Forest supplies an additional uncalibrated feature-space score.

## Data and evaluation

- User-selected dataset: 578,448 NOAA/ISD Indian station observations, 24 stations, 2022–2024. This is historical research data, not a continuous IMD AWS API archive.
- Pressure: the reviewed archive run accepts `ma1_altimeter` (QNH) observations; other pressure types break eligible sequences. A QNH model cannot be deployed directly on IMD MSLP inputs.
- Humidity may be derived from temperature/dew point in historical data. This does not validate detection of faults in direct IMD RH sensors.
- Train through June 2023; model selection July–September 2023; residual calibration October–December 2023; final evaluation in 2024, with four stations completely withheld from training.
- All three sensors have native-unit MAE/RMSE, separate residual thresholds and flagged fractions. Flagged fraction is not false-positive rate without ground-truth labels.
- No hardware-fault precision, recall, F1 or probability is invented. No new model is automatically promoted.

## Detection coverage

| Requirement | Current notebook evidence | Remaining validation |
|---|---|---|
| Temperature discrepancy | Temperature forecast residual and errors | Real temperature-fault labels and IMD transfer validation |
| Pressure discrepancy | QNH forecast residual and errors | Separate MSLP/station-pressure models and field semantics |
| Humidity discrepancy | Humidity forecast residual and errors | Direct RH observations and real sensor-fault labels |
| Spike | May produce a residual flag | Labelled event-level precision/recall |
| Drift | May produce persistent forecast residuals | Drift-event histories, thresholds, detection delay |
| Frozen sensor | Not validated by forecasting alone | Instrument resolution, persistence, corroborating evidence |
| Spatial discrepancy | Not enabled in this notebook | Time-aligned nearby stations, terrain/pressure compatibility |
| Communication failure | Not a weather-value prediction | Expected cadence and delivery/heartbeat observations |
| Physical root cause | Not established | Maintenance and technician verification |

## Run and deployment

Run on Colab GPU and upload the historical CSV when prompted. Return `SkyGuard_IMD_Training_Results.zip`; review forecast comparison and provenance before implementing a compatible backend inference adapter. The current Render model format is not automatically compatible. An IMD deployment must pass pressure/humidity domain checks, durable-history readiness, load/inference tests and shadow evaluation first.

Local training was not executed: permission to run the project Python environment check was declined. Syntax verification of the notebook is not a completed training run.

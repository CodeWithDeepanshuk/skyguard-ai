# SkyGuard AI architecture

## Repository structure

```text
config/
  stations.csv                    station identity, coordinates, clusters and holdouts
data/
  raw/                            immutable NOAA source files and documentation
  manifest/                       source URLs, sizes and SHA-256 hashes
  processed/                      canonical temperature/pressure/RH observations
  labelled/                       injected faults and genuine-weather scenarios
  features/                       original causal feature tables
  features_phase10/               strict three-parameter Phase 10 feature tables
  predictions_phase10/            compliant benchmark predictions
  incidents/                      incidents, correction actions and health forecasts
  demo/                           checksummed offline judge scenarios
  live/                           verified public live-data cache
  runtime/                        local SQLite replay state
models/
  phase10_final.joblib            deployed calibrated event/root bundle and policies
  phase10_climatology.joblib      clean 2022 station/cluster climatology
  phase10_tcn.pt                  advisory causal sequence model
  sensor_repair.joblib            supporting changed-value models
reports/                           generated metrics, validations and GPU results
src/
  data/                            pipeline, training, profiling and validation scripts
  skyguard/
    quality/                       physical and stateful QC
    faults/                        reproducible anomaly injection
    features/                      causal temporal, multivariate, neighbour and Phase 10 features
    models/                        baselines, LightGBM policy and causal TCN
    evaluation/                    point, episode, station and root metrics
    correction/                    estimates, uncertainty, incidents and sensor health
    streaming/                     replay engine and persistence
    live/                          public METAR adapter and Phase 10 scoring
    api/                           FastAPI application
dashboard/                         offline/live judge-facing web application
notebooks/                         full project and T4 GPU improvement notebooks
tests/                             unit, policy, API and integration tests
```

## End-to-end runtime

```text
NOAA replay / official live feed / future IMD adapter
                  |
                  v
      normalize timestamp and units
                  |
                  v
 deterministic QC and communication state
                  |
                  v
 causal station history + same-time/backward neighbours
                  |
                  v
 108-feature strict Phase 10 allowlist
                  |
                  v
 calibrated LightGBM event probabilities
        |                    |
        |                    +--> genuine-weather gate
        v
 station-aware threshold + causal persistence
                  |
                  v
 normal / genuine weather / sensor fault
                               |
                               v
                 incident-level root diagnosis
                               |
                               v
          confidence abstention / probable root
                               |
             +-----------------+-----------------+
             v                 v                 v
        explanation       correction + CI   health + forecast
             +-----------------+-----------------+
                               v
                  FastAPI + SQLite + dashboard
```

## Production model stack

1. **Deterministic safety layer** — range, missing, rate, frozen, gap, duplicate and order checks.
2. **Calibrated LightGBM event model** — regularized boosted trees for normal, genuine weather and sensor fault.
3. **Neighbour-weather gate** — prevents coherent regional change from becoming an individual fault.
4. **Known/new-station policy** — distinct validation-selected operating thresholds and causal persistence.
5. **Incident diagnosis** — calibrated 12-class LightGBM with deterministic packet/order overrides and `unknown_fault` abstention.
6. **Advisory TCN** — causal dilated convolutions trained with focal loss; retained for research because it failed the new-station false-alarm gate.
7. **Correction path** — robust causal estimate ensemble plus sensor-specific LightGBM correction-opportunity models.
8. **Maintenance path** — confidence/severity risk accumulation, decay and transparent recent health trajectory.

## Input boundary

Allowed detector sources are current/past temperature, pressure and relative humidity plus the same three values from backward-aligned neighbours. Forbidden sources include dew point, wind, rainfall, future observations, original clean targets, injection metadata, stream actions and labels.

## Deployment modes

- **Offline replay:** guaranteed judge demonstration with no internet.
- **Live public observations:** genuine METAR feed with verified cache fallback.
- **Future IMD adapter:** same normalized three-field contract; not yet connected.

Raw source observations are immutable. Generated datasets, policies and reports are reproducible from configuration, seeds and manifests.

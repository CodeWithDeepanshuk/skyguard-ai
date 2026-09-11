# Causal feature engineering

## Model-input boundary

The feature specification explicitly separates identity, model features, labels, and audit fields. Fault type, anomaly label, episode ID, original clean values, random seed, and stream action are not model inputs.

## Station-local features

For temperature, pressure, and humidity:

- missing indicator
- previous value
- one-step difference
- rate per hour
- prior 24-hour count, median, and MAD
- robust z-score using prior values
- prior EWMA and current residual
- frozen-value run length

The current observation is excluded from rolling median, MAD, and EWMA-prior calculations.

## Time and multivariate features

- hour sine/cosine
- day-of-year sine/cosine
- temperature/dew-point spread
- temperature/humidity interaction
- pressure/absolute-temperature ratio
- station cadence gap ratio
- out-of-order indicator

## Neighbour features

Stations are grouped by configured regional cluster and ranked by haversine distance. For each query, the latest neighbour reading at or before the query time is selected within a 180-minute tolerance. Up to five neighbours contribute:

- count
- inverse-distance weighted mean
- median and MAD
- station-to-neighbour residual
- maximum absolute difference
- agreement fraction
- neighbour age and nearest distance

For the unseen-station test, 2024 development stations provide neighbour values. Their labels and audit fields are never accessed by feature calculations.

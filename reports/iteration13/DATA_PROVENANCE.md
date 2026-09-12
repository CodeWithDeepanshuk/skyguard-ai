# Data Provenance

Expected source: `IMD_AUTHORIZED_AWS_API` produced by Iteration 12.

Genuine IMD rows locally available for Iteration 13: **0**. This is not a claim that IMD has no data; private authenticated observations are intentionally absent from Git.

Every accepted row must contain `source_is_genuine=true`, `source_snapshot_hash`, station ID, timestamp, coordinates, temperature, MSLP pressure and direct RH. Raw observations remain outside Git and are never overwritten. Every injected row retains original values, parameters, seed, partition and source identity.

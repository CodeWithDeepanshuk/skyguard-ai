# Iteration 8 reference-prompt audit

Reviewed: 2026-08-29  
Scope: the user-supplied Google research note proposing Kaggle/NOAA/MPI data, Isolation Forest, autoencoders, LSTM and ESP32 export

## Useful findings retained

- The official MPI-BGC Jena archive is a genuine useful source: 10-minute air temperature, air pressure and relative humidity are available, with CC-BY-4.0 terms. It is now listed in the SkyGuard source catalog.
- Isolation Forest is a valid unsupervised anomaly baseline.
- An autoencoder trained only on clean/normal sequences can provide a reconstruction-error novelty score.
- A recurrent model can represent frozen values, drift and temporal inconsistency better than a raw three-column point detector.

## Problems in the pasted sample code

1. It fits Isolation Forest on the same corrupted stream that it evaluates. This contaminates the normal model and is not a valid held-out benchmark.
2. `contamination=0.06` is chosen from the injected anomaly proportion, which leaks benchmark prevalence into the operating threshold.
3. It randomly synthesizes only 1,000 rows and has no station, time, season or climate holdout.
4. Isolation Forest receives only raw T/P/RH values. A valid frozen humidity value can remain invisible without run-length, slope and temporal-residual features.
5. A pressure dip is labelled “communication drop.” A real dropout is missing packet arrival and must be detected using a verified cadence/heartbeat contract.
6. Min/max scaling over the evaluated stream is not calibrated alert confidence.
7. The reported “SHAP-like” explanation is a global z-score heuristic, not SHAP or a local model attribution.
8. The printed ESP32 C header contains independent three-sigma bounds; it does not export the fitted Isolation Forest and discards temporal, multivariate and neighbour logic.
9. No false-alarm rate, point/event F1, latency, unseen-station transfer or genuine-weather discrimination is measured.

## Safe Iteration 8 decision

SkyGuard will not replace its supervised tree detector with the pasted implementation. Iteration 8 adds two controlled challenger channels:

- a clean-only, robust-scaled Isolation Forest score;
- a clean-only causal LSTM reconstruction autoencoder score using current-and-prior permitted observations/features.

The existing CatBoost/LightGBM detector remains the anchor. Tree-only, tree+Isolation-Forest, tree+LSTM-AE and three-model consensus variants are compared under the same tune-only threshold search. Discovery, confirmation, DWD climate groups and pseudo-unseen target stations remain untouched during selection. A challenger can advance only if it satisfies all existing precision, false-alarm, event/point F1 and genuine-weather gates.

MPI-Jena is recorded as a future independent single-site reconstruction check, not mixed into the current DWD development benchmark and not represented as a spatial-neighbour network.


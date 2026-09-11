# SkyGuard AI Iteration 8 — New-data runbook

Date prepared: 2026-08-29  
Status: ready for T4 development run; no Iteration 8 model score is claimed before Colab output is returned

## Purpose

Iteration 7 established that adding a causal TCN did not solve the weak weather-transfer result. The limiting factor was data support: the previous development corpus had only a few regional-weather episodes and narrow climate coverage. Iteration 8 therefore starts directly from the frozen Iteration 5 development reference, does not rerun Iterations 6 or 7, and changes the training evidence before adding more model complexity.

## New genuine observation corpus

The primary new source is the official Deutscher Wetterdienst (DWD) Climate Data Center 10-minute station product. The selected station contract contains 16 stations in four neighbour/climate groups: north coastal, east continental, west lowland and south upland.

| Year | Role | Full 10-minute rows | Stations | Minimum exact-cadence ratio |
|---:|---|---:|---:|---:|
| 2022 | development training | 838,126 | 16 | 99.95% |
| 2023 | development validation | 838,307 | 16 | 99.98% |
| 2024 | separately locked external confirmation | 841,805 | 16 | 99.99% |

Only temperature, pressure and relative humidity are detector observation inputs. DWD's station pressure, provider quality fields, station elevation, source URL, hashes and transform description are retained for audit. The normalized pressure used by the cross-network model is an explicitly recorded sea-level reduction; the unmodified station-pressure value is preserved separately.

## Authenticity and validation controls

- Files were downloaded from the official DWD HTTPS archive.
- Sixteen observation archives plus official station metadata and the English product description are retained.
- Every raw and processed file has a URL/role, byte count and SHA-256 manifest entry.
- All 16 selected stations have usable temperature, pressure and humidity records.
- Physical range, missingness, timestamp order, duplicate, cadence, station count and split-role checks pass.
- 2022 and 2023 are the only development years in the Colab bundle.
- The development ZIP contains no file whose name includes 2024 or 2025; the notebook asserts this again before training.
- DWD 2024 is in a different ZIP and must stay unopened until model, features and thresholds are frozen.

Detailed evidence is in `iteration8_dwd_data_validation.json`, `iteration8_dwd_data_validation.md`, `dwd_raw_files.csv` and `dwd_processed_files.csv`.

## Multi-climate curriculum

The full 10-minute observations remain in the bundle. Exact hour marks are sampled for compatibility with the accepted 108-feature contract.

| Partition | Hourly rows | Weather episodes | Fault episodes | Event-row fraction |
|---|---:|---:|---:|---:|
| DWD 2022 training | 139,684 | 96 | 160 | 8.23% |
| DWD 2023 validation | 139,716 | 72 | 60 | 5.18% |

Weather families: regional heatwave, regional cold surge, pressure front, humidity surge, dry intrusion and multivariate storm.

Fault families: bias, drift, frozen sensor, spike and noise. Existing communication, timestamp, duplicate and hard-physics paths from the accepted pipeline are retained and remain part of the India reference evaluation.

The 2023 validation curriculum is split before evaluation into tune, discovery and confirmation. Every scope contains every weather/fault family and every DWD climate. The exact downloaded-data smoke test covers 132 required scope–climate–class–family cells with at least one independent event in each.

## Models evaluated

1. Frozen Iteration 5 development detector as the India reference and unadapted DWD transfer baseline.
2. Domain-balanced CatBoost fault detector.
3. Domain-balanced LightGBM fault ensemble, seeds 17 and 41.
4. CatBoost + LightGBM geometric-consensus fault score.
5. Clean-only robust-scaled Isolation Forest novelty score.
6. Clean-only 24-step causal LSTM reconstruction autoencoder.
7. Tune-only ablation of tree-only, tree+Isolation-Forest, tree+LSTM-AE and three-model consensus scores.
8. Domain-balanced CatBoost weather detector.
9. Domain-balanced LightGBM weather ensemble, seeds 17 and 41.
10. CatBoost root-cause classifier on detected fault rows.

The failed Iteration 7 supervised TCN is not retrained. The new recurrent challenger is a smaller normal-only causal reconstruction model, not the former classifier. It can be rejected automatically because the tree-only score remains one of the four candidate variants.

## Evaluation and promotion gates

Thresholds are selected only on the tune scope. Discovery and confirmation are untouched during threshold search. The final comparison contains India, all DWD stations and four pseudo-unseen DWD target stations (one from each climate group).

Promotion requires all gates to pass:

- point precision at least 80% in every discovery/confirmation domain;
- false-alert episodes no more than 0.02 per station-day;
- no point-F1 regression in any discovery/confirmation domain;
- no confirmation event-F1 regression;
- non-negative weak-fault episode-recall delta everywhere and positive mean gain;
- confirmation weather F1 at least 0.75 in every domain;
- worst supported climate weather F1 at least 0.65;
- at most 1% of true fault rows misrouted as weather;
- a separately reported DWD holdout-station confirmation slice.

If any gate fails, the decision is automatically `retain Iteration 5 development reference`. Passing every gate only makes Iteration 8 eligible for one locked DWD 2024 confirmation; it does not replace the deployed Phase 10 model. A saved challenger is not the same as a promoted production model.

## Colab procedure

1. Put `SkyGuard_GPU_Data_Bundle.zip` and `SkyGuard_Iteration8_Development_Data_Bundle.zip` in `/content/drive/MyDrive/SkyGuard_AI_GPU/`.
2. Do not upload or extract `SkyGuard_Iteration8_Locked_2024_Confirmation.zip` during development.
3. Open `SkyGuard_AI_GPU_Iteration_08_MultiClimate_Data_Curriculum_Colab.ipynb` in Colab.
4. Select a T4 GPU and run all cells in order.
5. Keep `UNLOCK_FINAL_TESTS=False` and `REUSE_SAVED_MODELS=True`.
6. Return the eleven files printed by the final cell.

Expected first-run time is approximately 90–180 minutes with the LSTM autoencoder. The notebook caches generated DWD features and trained challengers in Drive, so an interrupted rerun can reuse completed work.

## Required returned files

- `iteration8_result_block.json`
- `iteration8_data_curriculum_receipt.json`
- `iteration8_feature_contract.json`
- `iteration8_training_history.csv`
- `iteration8_unsupervised_training_history.csv`
- `iteration8_multidomain_confirmation.csv`
- `iteration8_fault_episode_recall.csv`
- `iteration8_weather_by_cluster.csv`
- `iteration8_feature_importance.csv`
- `iteration8_weather_policy_frontier.csv`
- `iteration8_fault_policy_frontier.csv`

## Integrity identifiers

| Artifact | SHA-256 |
|---|---|
| Original GPU data bundle | `9329f02c1a05241b109c50b0ed3ba5bc59761eb92652f77509bda7409faf182a` |
| Iteration 8 development data bundle | `7f47466805309faf528d6abc8f04a588c4accbaf454989e36a2b4ff5b31681d4` |
| Locked DWD 2024 confirmation bundle | `cdc1983d26bb08565dc35448dfa1fd89d47e37fdb2eb1a4e075295f7ef915901` |
| Iteration 8 Colab notebook | `7c72f6862c393610e1cbc894745ea7d35bf0e1f04db2de3ae8b57ffbc616416b` |

## Local verification completed

- DWD source validation: PASS.
- Exact DWD curriculum smoke test: PASS.
- Notebook JSON/static Python syntax/integrity audit: PASS (87 cells, 44 code cells, no stale outputs).
- Isolation Forest + causal LSTM-AE notebook-cell CPU smoke test: PASS (34 features, four score variants).
- Full repository test suite: 66 passed; one third-party deprecation warning only.

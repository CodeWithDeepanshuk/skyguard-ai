# SkyGuard AI — Iteration 6 Audit and Iteration 7 Runbook

Date: 29 August 2026  
Problem: SIH 26073 — AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations

## Pre-Iteration-7 preservation

- Downloaded Colab candidates inspected: 68
- Unique downloaded artifacts archived: 56
- Duplicate-content copies recorded but not duplicated: 12
- Workspace code/notebook/model/report files checksummed: 224
- Compact code/artifact snapshot: `deliverables/SkyGuard_PreIteration7_Code_Artifacts_Snapshot_2026-08-29.zip`
- Snapshot SHA-256: `475234e9185e601b880ab8cf156e730a0bf01914f176c57e2a9d2a930b73d639`
- Raw/generated NOAA files remain in the OneDrive workspace and are represented by data manifests; the 1.4 GB data tree was not copied a second time.

The archive is under `reports/gpu_iterations/archive_pre_iteration7_2026-08-29/`. Its two CSV manifests contain source path, size, UTC modification time and SHA-256 for every preserved artifact.

## Iteration 6 audit decision

### Execution and leakage

- Executed code cells: 39/39
- Error outputs: 0
- GPU: Tesla T4
- Development years used: 2022 and 2023 only
- 2025 blind benchmark opened: no
- Former final tests opened: no
- Observation contract: temperature, pressure and relative humidity only

### Communication

The best timestamp-gap policy produced 75.00% precision, 42.86% recall and 54.55% F1. It failed the predeclared 80% precision and 80% recall gates. Automatic dropout fault alerts are therefore unsupported unless an adapter supplies verified expected cadence and heartbeat SLA. Unknown-cadence gaps remain advisories; exact duplicate packets remain automatic.

### Weather transfer

No weather candidate passed the complete discovery gate. The closest station-balanced candidate improved mean F1 but its worst station-macro delta was -2.58%, slightly outside the allowed -2.00%. It was correctly rejected instead of relaxing the gate after observing the result.

### Weak-fault transfer

Twelve candidates passed May–September discovery. The strongest candidate failed October confirmation: false alarms reached 0.02110 per station-day, point-F1 fell 0.77 percentage points, event-F1 fell 3.59 points and weak-fault recall did not improve. Pseudo-unseen stations also showed zero gain. The Iteration 6 no-op fallback is therefore correct.

## Iteration 7 design

Notebook: `notebooks/SkyGuard_AI_GPU_Iteration_07_Climate_Calibration_Causal_TCN_Colab.ipynb`

### Experiment A — climate-calibrated weather transfer

1. Preserve station-invariant CatBoost/LightGBM weather scores from Iteration 6.
2. Learn empirical score distributions from clean discovery-station history only.
3. Convert model scores to climate-cluster percentiles; pseudo-unseen stations receive cluster fallback only.
4. Fit sparse L1 and L2 logistic meta-calibrators using regional agreement, neighbour agreement, causal slopes and robust residuals.
5. Search thresholds only on May–September discovery blocks.
6. Confirm once on October and pseudo-unseen stations.

Weather promotion requires all of the following:

- no discovery block F1 regression;
- positive mean F1 improvement;
- station-macro F1 delta at least -2.00%;
- fault-to-weather error at most 1.00%;
- no October or pseudo-unseen F1 regression;
- October and pseudo-unseen station-macro delta at least -2.00%.

### Experiment B — causal TCN weak-fault consensus

1. Use a 24-observation causal window with left padding and no future rows.
2. Exclude raw temperature, raw pressure, raw humidity, raw lags, dew point and calendar encodings.
3. Train two compact TCN seeds on relative residuals, slopes, CUSUM, frozen runs, communication gaps and neighbour disagreement.
4. Balance training by station and fault episode and include weather/fault hard negatives.
5. Combine TCN probability with Iteration 6 CatBoost/LightGBM evidence.
6. Require incident persistence and the selected weather gate before adding a rescue alert.

Weak-fault promotion requires all of the following:

- minimum precision at least 75%;
- false alarm episodes at most 0.02 per station-day;
- no point-F1 regression;
- event-F1 delta at least -1 percentage point in every scope;
- positive mean point-F1 and non-negative mean event-F1 gain;
- non-negative weak-fault recall gain everywhere;
- strictly positive weak-fault recall gain on pseudo-unseen stations.

## Colab procedure

1. Upload/open the Iteration 7 notebook.
2. Verify `SkyGuard_GPU_Data_Bundle.zip` is at `/content/drive/MyDrive/SkyGuard_AI_GPU/`.
3. Select a T4 GPU.
4. Keep `UNLOCK_FINAL_TESTS=False` and `REUSE_SAVED_MODELS=True`.
5. Run all cells from the beginning without skipping historical reconstruction cells.
6. Do not open any 2024/2025 label or result file.
7. Return the twelve files printed by the final cell.

## Required returned files

1. `iteration7_result_block.json`
2. `iteration7_integrity_receipt.json`
3. `iteration7_communication_contract.json`
4. `iteration7_weather_policy_frontier.csv`
5. `iteration7_weather_confirmation.csv`
6. `iteration7_weather_station_metrics.csv`
7. `iteration7_tcn_training_history.csv`
8. `iteration7_weak_policy_frontier.csv`
9. `iteration7_weak_confirmation.csv`
10. `iteration7_multiblock_ablation.csv`
11. `iteration7_fault_episode_recall.csv`
12. `iteration7_feature_contract.json`

No production promotion is authorized by a successful Colab execution alone. Promotion is decided only after these artifacts are independently audited against the frozen gates above.

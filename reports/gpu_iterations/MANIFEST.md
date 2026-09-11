# Imported T4 iteration artifacts

These files were copied from the team’s returned Colab outputs on 29 August 2026. The JSON result blocks state `final_tests_opened=false`.

| File | SHA-256 |
|---|---|
| `iteration_result_block.json` | `5f8a57b8e79ad185594f1325daddb096e8c3badc27c0a890559c7f9f6cb5197c` |
| `development_ablation.csv` | `357601233be3f7c4e2514ba1910c79038f11128fa694cf3c4b4649a65fa771b2` |
| `development_fault_episode_recall.csv` | `e237f8fce4fe8c09e402f0820bf7225f41630c7326f12368a7ae29a563aa7b75` |
| `iteration2_result_block.json` | `cf90b12e1184bddda0a7bd921fdf8a9f902d65f3c76dd740cec76ac5fd29b3bd` |
| `iteration2_multiblock_ablation.csv` | `89f6f15eff97c0fccd287e1aa4c74d8bc24f60509076479e7d6ee86a395aae65` |
| `iteration2_fault_episode_recall.csv` | `50268b927ed023143c14b15775f4b0efc756c7128c102a9983fae14ea775ef8d` |
| `iteration2_weather_frontier.csv` | `6639c6c646a512be6fa89a1a5bbc836f9fe830a57cddca0b90ebaa2e8ac79aa0` |
| `iteration3_result_block.json` | `97b3511e95ebd4cd42269f4fbf3565f3e1f8806996a3b915e5a5061804b3aac0` |
| `iteration3_multiblock_ablation.csv` | `1c2ba5c0b06301cc81a17018f3f3d837a7b34f4fb2ddfb899e90798ea1601115` |
| `iteration3_fault_episode_recall.csv` | `50268b927ed023143c14b15775f4b0efc756c7128c102a9983fae14ea775ef8d` |
| `iteration3_frozen_frontier.csv` | `be161c4a4e7daa13af90fa525b71aad13bb576c4bfbc6336fb528bea9559f6c2` |
| `iteration3_communication_replay.csv` | `ddc7178021cb026647610c2fd6bed903610b9780fddac0aff5f3af212e133661` |

## Pre-Iteration-7 sealed archive

The directory `archive_pre_iteration7_2026-08-29/` preserves the returned executed notebooks, result tables, JSON receipts and trained Iteration 5 model files through Iteration 6.

- Download candidates audited: 68
- Unique artifacts archived: 56
- Duplicate-content copies recorded: 12
- Workspace code/artifact files checksummed: 224
- Compact snapshot: `deliverables/SkyGuard_PreIteration7_Code_Artifacts_Snapshot_2026-08-29.zip`
- Snapshot SHA-256: `475234e9185e601b880ab8cf156e730a0bf01914f176c57e2a9d2a930b73d639`

Iteration 7 is defined in `notebooks/SkyGuard_AI_GPU_Iteration_07_Climate_Calibration_Causal_TCN_Colab.ipynb`. Its 2024 and 2025 benchmark locks must remain closed.

## Iteration 8 controlled new-data phase

Iteration 8 starts from the frozen Iteration 5 development reference and does not rerun Iterations 6 or 7. It adds the official DWD 10-minute T/P/RH corpus for 16 stations across four climate groups, a balanced multi-climate weather/fault curriculum, clean-only Isolation Forest and causal LSTM-autoencoder challenger channels, and India/DWD/pseudo-unseen-station promotion gates.

| Artifact | SHA-256 |
|---|---|
| `deliverables/SkyGuard_Iteration8_Development_Data_Bundle.zip` | `7f47466805309faf528d6abc8f04a588c4accbaf454989e36a2b4ff5b31681d4` |
| `deliverables/SkyGuard_Iteration8_Locked_2024_Confirmation.zip` | `cdc1983d26bb08565dc35448dfa1fd89d47e37fdb2eb1a4e075295f7ef915901` |
| `notebooks/SkyGuard_AI_GPU_Iteration_08_MultiClimate_Data_Curriculum_Colab.ipynb` | `7c72f6862c393610e1cbc894745ea7d35bf0e1f04db2de3ae8b57ffbc616416b` |

The development bundle contains only DWD 2022–2023 observations. DWD 2024 remains in the separate locked archive. The executable notebook is `notebooks/SkyGuard_AI_GPU_Iteration_08_MultiClimate_Data_Curriculum_Colab.ipynb`; the procedure and promotion policy are documented in `reports/ITERATION_08_NEW_DATA_RUNBOOK.md`.

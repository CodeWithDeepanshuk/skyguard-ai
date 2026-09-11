# SkyGuard 2025 blind evaluation runbook

## Purpose

This is the next phase after Iteration 5. It tests whether the small development improvement generalizes to later 2025 observations and to four never-trained station identities. It is a final measurement, not another tuning dataset.

## Required files

Upload these files to `MyDrive/SkyGuard_AI_GPU/`:

1. `SkyGuard_Blind_2025_Bundle.zip`
2. the normal SkyGuard GPU bundle already used by Iterations 1–5

Keep the saved Iteration 1–5 model folders in their existing Drive locations. In particular, the six Iteration 5 weak-union models must be present under `experiments/iteration_05_weak_fault_consensus/`.

Open `notebooks/SkyGuard_AI_GPU_Blind_2025_Final_Comparison_Colab.ipynb` in Google Colab and select a T4 GPU runtime.

## Exact procedure

1. Leave `UNLOCK_BLIND_2025=False`.
2. Run the notebook from the top through **DEVELOPMENT LOCK: PASS**.
3. If any model hash, policy, feature contract or development confusion matrix fails, stop. Do not open the blind archive.
4. Change only `UNLOCK_BLIND_2025=True`.
5. Run sections 24–27 once.
6. Do not change thresholds, models, features, seeds or policies after seeing the result.
7. Download and return all files printed under `SEND BACK THESE FILES`.

The archive must have this SHA-256:

`5f8bbad22342295f62c97d9b47628800eaa43df7aec5650ea91b814c6854d859`

## Tests performed

The notebook compares the frozen Iteration 3 reference and Iteration 5 candidate on:

- `blind_time`: later 2025 data from 20 known station identities;
- `blind_station`: later 2025 data from four stations never used for training;
- all sensor/fault families in the benchmark;
- neighbour-consistent regional weather events;
- duplicate-packet stream replay;
- missing-packet/dropout stream replay.

Reported metrics include precision, recall, point F1, AUCPR, accuracy, balanced accuracy, specificity, event precision/recall/F1, operational episode recall, false-alert episodes per station-day, latency, per-fault recall, weather F1 and weather-to-fault rate.

## Frozen acceptance criteria

Each blind test must independently meet:

| Criterion | Target |
|---|---:|
| Precision | at least 80% |
| Point F1 | at least 65% |
| Operational episode recall | at least 85% |
| False-alert episodes per station-day | at most 0.02 |
| Genuine-weather F1 | at least 80% |
| Weather rows incorrectly flagged as faults | at most 1% |

Iteration 5 must also avoid point-F1 and event-F1 regression against Iteration 3 on both tests. Passing only the relative gate means Iteration 5 is an honest improvement; passing every strict target means the detector is ready for final integration and deployment testing.

## Files to return

- `blind_2025_result_block.json`
- `blind_2025_comparison.csv`
- `blind_2025_fault_episode_recall.csv`
- `blind_2025_point_fault_recall.csv`
- `blind_2025_weather_metrics.csv`
- `blind_2025_communication_replay.csv`
- `blind_2025_readiness_checks.csv`
- `blind_2025_open_receipt.json`

Do not rerun the blind notebook to search for a better result. If a target fails, the next improvement must be designed using development data and tested later on a newly sealed benchmark.

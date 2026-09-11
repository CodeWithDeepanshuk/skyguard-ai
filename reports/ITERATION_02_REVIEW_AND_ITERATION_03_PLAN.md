# SkyGuard AI — Iteration 2 Review and Iteration 3 Plan

## Decision

Iteration 2 is a valid improvement in incident-level operation, but it is not the final model. Retain the two-tier CatBoost policy provisionally. Do not claim that the learned frozen, bias, or drift specialists generalize yet.

The 2024 station-held-out and time-held-out tests remain sealed.

## Iteration 2 selected policy

- Base alert start threshold: 0.30
- Base continuation threshold: 0.22
- Weak-fault rescue threshold: 0.50
- Required rescue persistence: 2 observations
- Development constraints: point precision at least 75% and false-alarm episodes at most 0.02 per station-day in every block

## Development-block results

| Block | Precision | Recall | Point F1 | AUCPR | Event precision | Event recall | Event F1 | False alarms / station-day | Mean delay | P90 delay |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| May–June | 80.00% | 44.44% | 57.14% | 52.55% | 51.61% | 72.73% | 60.38% | 0.0123 | 86.3 min | 300 min |
| July–September | 88.61% | 18.67% | 30.84% | 24.41% | 54.55% | 66.67% | 60.00% | 0.0082 | 190.0 min | 630 min |
| October–December | 83.26% | 41.19% | 55.11% | 49.52% | 47.54% | 80.56% | 59.79% | 0.0174 | 93.1 min | 444 min |

## What improved

Compared with the robust CatBoost-only operating point, the selected rescue policy improved event recall, event F1, detection delay, and false-alarm rate in every development block. It passed the formal precision and false-alarm constraints in all three blocks.

## Remaining weaknesses

- July–September point recall and F1 are weak. The detector catches many episodes but misses many individual anomalous observations inside them.
- Frozen-sensor episode recall is 16.67%.
- Drift episode recall is 25.00%.
- Bias episode recall is 42.86%.
- Duplicate-packet recall appears as zero in the static-table evaluation because `stream_action=duplicate` is a replay instruction; the static feature table intentionally contains only one row until the simulator emits the second packet.
- The weather-versus-fault classifier has a worst-block F1 of 43.70%, so genuine-weather discrimination still requires improvement.
- The learned specialists are unstable across time: frozen AUPRC fell from 45.55% in July–September to 0.29% in October–December.

## Iteration 3 experiment

Iteration 3 adds only two controlled changes:

1. Sensor-specific frozen rules based on causal constant-value run length and disagreement with neighbouring stations.
2. Full-stream communication replay in which duplicate-labelled source rows emit an identical second packet and the detector identifies it without reading the hidden label or `stream_action` field.

The frozen rule is promoted only when all development blocks retain at least 75% point precision, at most 0.02 false-alarm episodes per station-day, no block loses more than 0.01 event F1, the mean event F1 does not decrease, and frozen recall genuinely improves. Otherwise Iteration 2 remains active.

The duplicate replay reports packet precision, packet recall, false positives, false negatives, and episode recall across the complete 181,470-row validation stream. A local deterministic replay check produced 16/16 duplicate-packet detections, zero false positives, and 10/10 detected duplicate episodes. Colab will reproduce this result from the uploaded project bundle.

## Files to return after running Iteration 3

- `iteration3_result_block.json`
- `iteration3_multiblock_ablation.csv`
- `iteration3_fault_episode_recall.csv`
- `iteration3_communication_replay.csv`

Do not unlock or run the final 2024 tests during Iteration 3.

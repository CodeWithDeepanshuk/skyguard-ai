# SkyGuard AI — Iteration 3 Review and Iteration 4 Plan

## Decision

Iteration 3 ran correctly on a Tesla T4. All 17 code cells completed without errors, and the final-test flag remained false.

Promote the full-stream duplicate-packet detector. Do not promote any frozen-sensor rule. Retain the Iteration 2 two-tier detector as the main anomaly policy.

## Main anomaly policy

Because the frozen rule was rejected, Iteration 3 correctly reproduces the selected Iteration 2 results:

| Block | Precision | Recall | Point F1 | Event recall | Event F1 | False alarms / station-day |
|---|---:|---:|---:|---:|---:|---:|
| May–June | 80.00% | 44.44% | 57.14% | 72.73% | 60.38% | 0.0123 |
| July–September | 88.61% | 18.67% | 30.84% | 66.67% | 60.00% | 0.0082 |
| October–December | 83.26% | 41.19% | 55.11% | 80.56% | 59.79% | 0.0174 |

## Communication replay result

The detector processed the complete 181,470-row validation stream. Duplicate-labelled rows caused the simulator to emit 16 additional packets.

- Duplicate packet true positives: 16
- False positives: 0
- False negatives: 0
- Packet precision: 100%
- Packet recall: 100%
- Duplicate episodes detected: 10/10
- `stream_action` used by detector: no

This is a valid operational result. The zero duplicate recall in static row-level reports must be labelled as non-operational because the second packet does not exist until replay.

## Frozen-rule result

No fixed frozen rule generalized across all three development blocks.

- The best humidity candidate increased mean frozen recall from 16.67% to 44.44%, but minimum block recall remained zero and mean event F1 decreased.
- Temperature frozen rules caused severe false alarms: worst-block precision fell to roughly 27%–48%, depending on the threshold.
- Pressure rules produced little or no frozen-recall gain and slightly reduced event performance.
- The safe selector therefore returned all sensor rules as `None`.

This rejection is a successful experiment because it prevents deployment of a brittle rule that would look good on selected episodes but fail seasonally.

## Remaining bottleneck

Event recall is 66.67%–80.56%, while point recall is only 18.67%–44.44%. The detector often identifies an incident but marks too few observations within long bias, drift, frozen, or noise episodes. July–September is the clearest example: event F1 is 60.00%, but point F1 is only 30.84%.

## Iteration 4

Iteration 4 tests a causal incident-state controller. A validated strong trigger starts an alert; weaker evidence may only continue an existing alert. It cannot create an incident independently and uses no future observations.

Promotion requires all development blocks to retain:

- Point precision of at least 75%
- False-alarm episodes of at most 0.02 per station-day
- Non-decreasing point F1
- No more than 0.01 event-F1 loss in any block
- Non-decreasing mean event F1
- Positive mean point-F1 improvement

If no configuration satisfies every condition, Iteration 3/2 remains deployed.

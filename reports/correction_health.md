# SkyGuard Phase 6 correction, explanation, and health report

Correction methods and 90% uncertainty widths were selected on 2023 validation and frozen before either 2024 split was loaded.

## Causal correction results

| Test | Mode | Sensor | Changed points | Correction coverage | Reported MAE | Corrected MAE | Corrected RMSE | MAE reduction | Interval coverage |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| time_test | oracle_policy | temperature | 1065 | 1.0000 | 6.1117 | 1.8334 | 2.4008 | 70.0024% | 0.8535 |
| time_test | oracle_policy | pressure | 709 | 1.0000 | 76.5580 | 1.5303 | 2.0681 | 98.0012% | 0.7588 |
| time_test | oracle_policy | humidity | 597 | 1.0000 | 24.7251 | 10.7249 | 14.9689 | 56.6235% | 0.8425 |
| time_test | operational | temperature | 1065 | 0.3549 | 10.2127 | 1.7594 | 2.3266 | 82.7725% | 0.9868 |
| time_test | operational | pressure | 709 | 0.6728 | 111.4616 | 1.4947 | 1.9938 | 98.6590% | 0.8742 |
| time_test | operational | humidity | 597 | 0.5812 | 29.7511 | 13.0011 | 17.3066 | 56.3006% | 0.7839 |
| station_test | oracle_policy | temperature | 118 | 1.0000 | 10.4129 | 1.4406 | 2.0954 | 86.1652% | 0.9237 |
| station_test | oracle_policy | pressure | 67 | 1.0000 | 41.8565 | 1.2814 | 1.5023 | 96.9387% | 0.8657 |
| station_test | oracle_policy | humidity | 108 | 1.0000 | 50.9966 | 6.3127 | 8.1315 | 87.6213% | 0.9630 |
| station_test | operational | temperature | 118 | 0.2712 | 22.0745 | 1.4836 | 2.2392 | 93.2793% | 0.8750 |
| station_test | operational | pressure | 67 | 0.7015 | 58.6938 | 1.2720 | 1.5781 | 97.8328% | 0.8723 |
| station_test | operational | humidity | 108 | 0.3704 | 106.2445 | 6.4979 | 9.1068 | 93.8840% | 0.9250 |

## Scope

Oracle-policy results isolate corrected-value quality using the known affected sensor and fault family. Operational results include Phase 10 misses, inferred affected sensors, root-cause uncertainty, and candidate availability. Original clean values are used only for offline metrics and never appear in incident files.

Generated incidents: validation 856, time test 1,069, unseen stations 89.

Communication-only and timestamp faults receive an explanation but no fabricated physical correction. Dropout remains a Phase 7 stream-gap task.

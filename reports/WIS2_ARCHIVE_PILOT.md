# IMD WIS2 Resumable Archive — 3-Day Pilot

Window: 2026-09-09 through 2026-09-11 UTC

| Measure | Result |
|---|---:|
| Complete daily partitions | 3/3 |
| Partial/failed partitions | 0 |
| Direct SYNOP reports | 4,281 |
| Distinct reporting stations | 328 |
| Complete T/P/RH reports | 4,134 |
| Temperature non-null | 4,277 |
| Pressure non-null | 4,140 |
| Humidity non-null | 4,275 |
| Duplicate station-timestamps | 0 |
| Station-days | 979 |
| Reports/station median | 11 |
| Reports/station maximum | 24 |
| Median cadence gap | 180 minutes |
| P90 cadence gap | 720 minutes |
| Maximum observed gap | 2,880 minutes |

The first pilot exposed 262 midnight duplicates because OGC intervals include both endpoints. The collector was corrected to end each daily query at 23:59:59 UTC and the partitions were regenerated; final duplicate count is zero.

## Modelling consequence

The data are not a dense hourly tensor. TCN/GAT training must include elapsed-time and availability masks, must never forward-fill labels across long gaps, and must evaluate stations/days with insufficient neighbours as unavailable. This pilot validates the archive mechanism, not neural-model accuracy.


# SkyGuard labelled dataset validation

**Ready for feature engineering: YES**

- Episodes: 559
- Generated files covered by checksum manifest: 5
- Validation errors: 0

## Checks

| Check | Result |
|---|---|
| generated file hashes match | PASS |
| episode ids globally unique | PASS |
| all fault types present | PASS |
| split year and role rules hold | PASS |
| no row leakage between splits | PASS |
| station test contains only holdouts | PASS |
| episode manifest counts match rows | PASS |
| original values and timestamps preserved | PASS |
| stream actions match fault types | PASS |
| fault and weather labels are exclusive | PASS |

## Splits

| Split | Rows | Fault rows | Weather rows | Fault % | Stations |
|---|---:|---:|---:|---:|---:|
| train | 182,362 | 2,510 | 498 | 1.3764% | 20 |
| validation | 181,470 | 1,696 | 511 | 0.9346% | 20 |
| time_test | 182,276 | 2,064 | 824 | 1.1323% | 20 |
| station_test | 10,516 | 275 | 0 | 2.6151% | 4 |

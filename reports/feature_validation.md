# SkyGuard feature validation

**Ready for baseline models: YES**

- Rows: 556,624
- Model features: 72
- Overall neighbour coverage: 99.9014%
- Validation errors: 0

## Checks

| Check | Result |
|---|---|
| feature hashes match manifest | PASS |
| model features exclude labels and audit | PASS |
| source rows and labels preserved | PASS |
| row ids unique | PASS |
| all model features numeric and finite | PASS |
| dropped rows hidden from detector | PASS |
| first lags are causal | PASS |
| neighbor alignment is backward only | PASS |
| neighbor coverage above 70 percent | PASS |

## Split coverage

| Split | Rows | Detector rows | Neighbour coverage | Robust-z coverage |
|---|---:|---:|---:|---:|
| train | 182,362 | 182,122 | 99.9495% | 99.5080% |
| validation | 181,470 | 181,308 | 99.9217% | 99.6729% |
| time_test | 182,276 | 182,053 | 99.8275% | 99.4128% |
| station_test | 10,516 | 10,491 | 100.0000% | 98.5797% |

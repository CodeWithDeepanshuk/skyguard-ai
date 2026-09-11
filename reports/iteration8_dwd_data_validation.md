# Iteration 8 DWD data validation

- Status: **PASS**
- Provider: Deutscher Wetterdienst (DWD)
- Product: CDC 10-minute station observations
- Raw integrity files: 18 (16 station archives)
- Balanced station contract: 16 stations across 4 clusters
- Model observation inputs: temperature, pressure, relative humidity
- DWD 2024 role: external confirmation locked
- 2025 loaded: no

| Year | Role | Rows | Stations | Minimum exact 10-minute ratio |
|---:|---|---:|---:|---:|
| 2022 | development_train | 838,126 | 16 | 99.95% |
| 2023 | development_validation | 838,307 | 16 | 99.98% |
| 2024 | external_confirmation_locked | 841,805 | 16 | 99.99% |

## Errors

- None

# SkyGuard AI data validation report

**Ready for anomaly injection: YES**

## Authenticity and integrity

- Provider: NOAA/NCEI
- Product: Global Hourly / Integrated Surface Database (ISD)
- Files in checksum manifest: 74
- Station-year observation files: 72
- Raw bytes covered by manifest: 257,260,122

## Processed corpus

- Rows: 578,448
- Stations: 24
- Years: 2022, 2023, 2024
- Regional clusters: 4
- Clean candidate rows: 569,633 (98.4761%)
- Duplicate station/timestamps: 0

## Missingness

| Variable | Missing rows | Missing % |
|---|---:|---:|
| temperature_c | 104 | 0.0180% |
| pressure_hpa | 8,619 | 1.4900% |
| relative_humidity_pct | 246 | 0.0425% |

## Validation checks

| Check | Result |
|---|---|
| official source urls only | PASS |
| all expected files present | PASS |
| all sha256 checks pass | PASS |
| official station metadata matches | PASS |
| raw schema valid | PASS |
| processed schema valid | PASS |
| all stations present | PASS |
| all years present | PASS |
| all station year pairs present | PASS |
| minimum 1500 rows per station year | PASS |
| no processed duplicate timestamps | PASS |
| temperature missing below 0 1 percent | PASS |
| humidity missing below 0 1 percent | PASS |
| pressure missing below 5 percent | PASS |

## Known source-value flags

Physical-bound violations detected: 0

Violating rows, if present in a future refresh, remain auditable in the normalized source table and are excluded from the clean candidate pool used for synthetic fault injection.

## Important limitation

ISD observations are genuine, but confirmed sensor-fault labels are not included. Controlled fault injection is required for supervised evaluation.

## Station-year coverage

| Station | Year | Rows | Median interval (min) | Tier |
|---|---:|---:|---:|---|
| 42131099999 | 2022 | 2,822 | 180.0 | medium |
| 42131099999 | 2023 | 2,791 | 180.0 | medium |
| 42131099999 | 2024 | 2,703 | 180.0 | medium |
| 42181099999 | 2022 | 17,175 | 30.0 | high |
| 42181099999 | 2023 | 17,118 | 30.0 | high |
| 42181099999 | 2024 | 16,769 | 30.0 | high |
| 42182099999 | 2022 | 4,005 | 180.0 | medium |
| 42182099999 | 2023 | 2,893 | 180.0 | medium |
| 42182099999 | 2024 | 2,860 | 180.0 | medium |
| 42189099999 | 2022 | 3,011 | 180.0 | medium |
| 42189099999 | 2023 | 3,239 | 180.0 | medium |
| 42189099999 | 2024 | 4,496 | 120.0 | medium |
| 42348099999 | 2022 | 17,367 | 30.0 | high |
| 42348099999 | 2023 | 17,327 | 30.0 | high |
| 42348099999 | 2024 | 16,765 | 30.0 | high |
| 42361099999 | 2022 | 2,973 | 180.0 | medium |
| 42361099999 | 2023 | 3,280 | 180.0 | medium |
| 42361099999 | 2024 | 4,388 | 150.0 | medium |
| 42705699999 | 2022 | 17,532 | 30.0 | high |
| 42705699999 | 2023 | 17,359 | 30.0 | high |
| 42705699999 | 2024 | 16,778 | 30.0 | high |
| 43021099999 | 2022 | 2,015 | 30.0 | medium |
| 43021099999 | 2023 | 2,846 | 30.0 | medium |
| 43021099999 | 2024 | 3,521 | 30.0 | medium |
| 43086099999 | 2022 | 2,880 | 180.0 | medium |
| 43086099999 | 2023 | 2,852 | 180.0 | medium |
| 43086099999 | 2024 | 2,746 | 180.0 | medium |
| 43128099999 | 2022 | 11,986 | 30.0 | high |
| 43128099999 | 2023 | 11,484 | 30.0 | high |
| 43128099999 | 2024 | 10,650 | 30.0 | high |
| 43128599999 | 2022 | 17,119 | 30.0 | high |
| 43128599999 | 2023 | 16,363 | 30.0 | high |
| 43128599999 | 2024 | 15,698 | 30.0 | high |
| 43181099999 | 2022 | 12,656 | 30.0 | high |
| 43181099999 | 2023 | 12,096 | 30.0 | high |
| 43181099999 | 2024 | 11,769 | 30.0 | high |
| 43213099999 | 2022 | 2,883 | 180.0 | medium |
| 43213099999 | 2023 | 2,861 | 180.0 | medium |
| 43213099999 | 2024 | 2,736 | 180.0 | medium |
| 43233099999 | 2022 | 2,877 | 180.0 | medium |
| 43233099999 | 2023 | 1,945 | 180.0 | medium |
| 43233099999 | 2024 | 2,516 | 180.0 | medium |
| 43245099999 | 2022 | 2,870 | 180.0 | medium |
| 43245099999 | 2023 | 2,825 | 180.0 | medium |
| 43245099999 | 2024 | 2,730 | 180.0 | medium |
| 43275099999 | 2022 | 1,797 | 180.0 | medium |
| 43275099999 | 2023 | 1,768 | 180.0 | medium |
| 43275099999 | 2024 | 1,562 | 180.0 | medium |
| 43278099999 | 2022 | 2,156 | 180.0 | medium |
| 43278099999 | 2023 | 2,096 | 180.0 | medium |
| 43278099999 | 2024 | 2,006 | 180.0 | medium |
| 43279099999 | 2022 | 17,314 | 30.0 | high |
| 43279099999 | 2023 | 17,311 | 30.0 | high |
| 43279099999 | 2024 | 16,779 | 30.0 | high |
| 43284099999 | 2022 | 17,107 | 30.0 | high |
| 43284099999 | 2023 | 16,652 | 30.0 | high |
| 43284099999 | 2024 | 16,256 | 30.0 | high |
| 43295099999 | 2022 | 2,846 | 180.0 | medium |
| 43295099999 | 2023 | 2,828 | 180.0 | medium |
| 43295099999 | 2024 | 2,762 | 180.0 | medium |
| 43302599999 | 2022 | 10,620 | 30.0 | high |
| 43302599999 | 2023 | 12,727 | 30.0 | high |
| 43302599999 | 2024 | 15,627 | 30.0 | high |
| 43321099999 | 2022 | 16,047 | 30.0 | high |
| 43321099999 | 2023 | 15,556 | 30.0 | high |
| 43321099999 | 2024 | 15,410 | 30.0 | high |
| 43329099999 | 2022 | 2,883 | 180.0 | medium |
| 43329099999 | 2023 | 2,841 | 180.0 | medium |
| 43329099999 | 2024 | 2,714 | 180.0 | medium |
| 43331099999 | 2022 | 2,866 | 180.0 | medium |
| 43331099999 | 2023 | 2,791 | 180.0 | medium |
| 43331099999 | 2024 | 2,551 | 180.0 | medium |

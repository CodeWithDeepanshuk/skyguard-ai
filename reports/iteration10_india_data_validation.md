# Iteration 10 India development-data validation

Status: **PASS**

The bundle contains only official NOAA/NCEI-derived 2022–2023 observations. It does not contain or open a 2024/2025 observation file.

## Summary

- Rows: 385,656
- Stations: 24
- Clusters: 4
- Complete T/P/RH rows: 99.930%
- Duplicate station timestamps: 0
- Development bundle: `deliverables/SkyGuard_Iteration10_India_Development_Data_Bundle.zip`

## Causal neighbour support

| Cluster | Tolerance | >=1 neighbour | >=2 neighbours | Mean |
| --- | ---: | ---: | ---: | ---: |
| bengaluru | 180 min | 99.99% | 99.94% | 4.73 |
| chennai | 180 min | 99.75% | 99.63% | 4.50 |
| delhi | 180 min | 100.00% | 99.75% | 4.93 |
| hyderabad | 180 min | 99.95% | 99.78% | 4.47 |

## Interpretation

The India corpus is genuine and sizeable, but its station cadences are mixed. The model must therefore use elapsed-time windows and expose stale/absent neighbour evidence; it must not assume a DWD-like uniform 10-minute network.

## Checks

- PASS — `48_station_year_raw_files_verified`
- PASS — `all_raw_hashes_match`
- PASS — `official_source_urls_only`
- PASS — `exactly_24_stations_and_4_clusters`
- PASS — `both_development_years_present`
- PASS — `all_48_station_year_pairs_present`
- PASS — `minimum_1500_rows_per_station_year`
- PASS — `minimum_90_percent_complete_triples_per_station_year`
- PASS — `no_duplicate_station_timestamps`
- PASS — `temperature_missing_below_0_1_percent`
- PASS — `humidity_missing_below_0_1_percent`
- PASS — `pressure_missing_below_5_percent`
- PASS — `temperature_range_plausible`
- PASS — `humidity_range_valid`
- PASS — `pressure_range_plausible`
- PASS — `source_labels_only_2022_2023`
- PASS — `locked_observation_years_not_loaded`

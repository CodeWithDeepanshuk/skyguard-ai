# Independent training-data verdict — SIH 26073

## Conclusion

The data sources are relevant and useful, but the current training-data contract is not yet reliable enough to support a claim of a completed operational Indian AWS fault detector. Keep the observations. Fix pressure semantics, labels/unknown states, cadence and evaluation before replacing the model or downloading indiscriminately. This is an engineering judgment based on the checks below, not a quality percentage or an accuracy ceiling.

The biggest observed issue is not simply “India has bad data and Germany has good data.” The stored Indian archive originally lost usable station-pressure values during normalization. A later copy recovers many values but pools pressure conventions into one stream. The currently deployed baseline and the latest Colab challenger also follow different data paths.

## What was actually inspected

- All 385,656 original Indian development rows for 2022–2023 and the corresponding 385,656 revised Iteration 10 rows.
- All 1,676,433 stored DWD development rows for 2022–2023, across 16 stations.
- Both original labelled development files and both actual Phase 10 feature tables; feature allowlist, visibility masks and label sources.
- Representative raw NOAA records for Delhi and Bangalore and the 2022–2023 raw DWD Hamburg product. These raw spot checks are not a full audit of every upstream record.
- Normalizers, fault injector, feature builder, neighbour lookup, deployed-model loading, saved training script and Iteration 10R notebook data-loading code.
- Byte comparison of the actual India starter and DWD development ZIP members against the audited local development files: all three matched.

No training, threshold tuning or fresh labelled-test scoring was performed. The combined original Indian archive contains 578,448 rows including 2024; descriptive analysis was restricted to its 2022–2023 records. No labelled 2024/2025 test was opened. The local ZIP checks cannot prove which copy a remote Colab runtime actually executed.

## Data inventory and role

| Stored data | Actual contents | Role / verdict |
|---|---|---|
| `data/processed/aws_observations_2022_2024.csv` | 578,448 rows, 24 Indian stations; 385,656 rows in 2022–2023 | Genuine Indian surface/airport observations obtained through NOAA/NCEI. Original baseline lineage, not proof of raw IMD AWS telemetry. |
| `data/iteration10/processed/india_aws_2022_2023.csv.gz` | 385,656 rows, 24 stations; 385,386 complete T/P/RH triples | Better completeness, but pressure-datum mixing still needs repair. |
| `data/iteration8/processed/dwd_aws_10min_2022.csv.gz` | 838,126 rows, 16 German stations | Useful regular external-domain series; source missing/invalid triples have already been filtered. |
| `data/iteration8/processed/dwd_aws_10min_2023.csv.gz` | 838,307 rows, 16 German stations | Useful development validation domain, not evidence of Indian operational performance. |
| `data/labelled/train.csv` | 182,362 rows, 20 stations; 2,510 injected fault rows in 195 fault episodes and 498 synthetic weather rows | Reproducible supervised simulator benchmark; not verified real fault/maintenance labels. |
| `data/labelled/validation.csv` | 181,470 rows; 1,696 injected fault rows and 511 synthetic weather rows | Same limitation; label validity must not be inferred from a `normal` default. |
| `data/features_phase10/train_features.csv.gz`, `validation_features.csv.gz` | 182,122 / 181,308 detector-visible rows after omitting injected dropped packets; Indian station IDs only | Data path referenced by the saved deployed-baseline training code. Not the DWD/revised-India challenger data. |
| `data/live/latest.json` | Mutable METAR observation/scoring cache | Live-source operation/demo, not independently labelled model evaluation data. |

NOAA documents ISD as combined hourly/synoptic surface observations, with temperature, dew point and multiple pressure fields, already subject to QC. NOAA is the archive provider here; these are Indian stations, not US stations. [NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database).

## Critical findings

### 1. Missing Indian pressure was partly a pipeline problem

In 2022–2023, the old normalized copy contains 5,764 missing pressure values. The revised copy contains 96: 5,668 previously missing pressures became available; five existing pressure values changed by more than 0.01 hPa. Complete triples increased from 379,741 to 385,386.

Bangalore station `43295099999` is the clearest example: only 17 of 5,674 original rows had pressure, with 0.30% complete triples. The revised copy has 99.30% complete triples. A raw 2022 record contains `MA1=99999,9,09133,1`: the altimeter field is missing but station pressure is 913.3 hPa. The earlier normalized table discarded this useful field. The current parser reads the four MA1 components. NOAA's format defines these distinct pressure fields. [NOAA ISD format](https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf).

### 2. Filling pressure introduced an unresolved meaning change

The revised Indian pressure column contains 275,113 altimeter values, 104,774 sea-level values, 5,673 station-pressure values and 96 missing values. The parser chooses SLP first, then altimeter, then station pressure, row by row.

Actual consecutive Bangalore records:

| UTC | Pressure hPa | Recorded type |
|---|---:|---|
| 2022-05-22 12:00 | 903.7 | station pressure |
| 2022-05-22 15:00 | 1048.3 | sea-level pressure |
| 2022-05-22 18:00 | 906.1 | station pressure |

There are 32 adjacent valid pressure-source switches at this station; median absolute jump at those switches is 141.3 hPa. These values cannot be treated as a single comparable pressure stream or automatically interpreted as real sensor faults. Station normalization alone does not remove an abrupt datum change. The source values themselves also deserve review; the audit does not certify either value as physically correct.

DWD raw `PP_10` is station-altitude pressure. Our stored `pressure_hpa` is a temperature/elevation-based approximate sea-level reduction; original station pressure is preserved separately. This creates different semantics and an additional temperature dependency. Use compatible pressure streams, or split/reset state at source changes, before multivariate or spatial comparisons. [DWD field definitions](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/DESCRIPTION_obsgermany_climate_10min_air_temperature_en.pdf).

### 3. RH and sampling are materially different

- All available Indian legacy RH values match the project's temperature/dew-point Magnus conversion within 0.001 percentage point. This is a derived humidity channel, not evidence of independent RH sensor measurements.
- DWD `RF_10` is reported RH. The DWD specification describes its dew point as calculated from temperature and RH, the opposite direction to the Indian preprocessing.
- In India, 11 station series have a median 30-minute report gap and 13 have a median 180-minute gap. There are 3,102 gaps longer than six hours across those 24 station series over two years. These are archive report gaps, NOT verified communication faults.
- Stored DWD is overwhelmingly 10-minute sampling; only 25 gaps exceed six hours across the two development years and 16 stations. These counts have different denominators and are not directly a fault-rate comparison.
- 79.28% of nonmissing Indian temperature values are integer-valued; about 9.97% / 9.96% in DWD 2022 / 2023. Integer-valued readings are an observed quantization pattern, not a measured sensor accuracy specification. It makes repeated-value tests more ambiguous.

The 10R notebook selects `minute == 0` DWD records, not all six reports/hour: 139,684 in 2022 and 139,716 in 2023, total 279,400. It does not average the six reports. With 385,386 complete Indian rows, this explains the 664,786-row combined complete development pool before later splits/injections. A richer archive does not mean every raw record is used by the model.

### 4. Default labels are not independently verified healthy observations

All 2,510 original training fault rows are labelled `synthetic_fault`; no real maintenance-confirmed sensor-fault labels were found in these labelled files. The fault injector initially labels all source records normal, then modifies selected clean records. Its clean eligibility check protects injection placement, not the truth of every untouched negative.

There are 2,948 training rows and 2,923 validation rows labelled normal while missing at least one primary input. There are also 279 / 238 normal-labelled rows carrying suspect/error NOAA temperature or pressure QC codes (2, 3, 6, 7). Missing reports or a suspect QC flag do not themselves prove hardware faults. They also should not be advertised as confirmed healthy negatives. An explicit unknown/review state is needed.

The original training file has only 15 spike rows and 15 sudden-drop rows; many thousands of archive rows do not imply many independent examples of each failure type. Synthetic regional weather scenarios also do not establish verified real storm/heatwave discrimination. The supplied SIH statement permits injected-anomaly evaluation, so synthetic labels are useful and allowed when disclosed, but are not field validation.

### 5. Geographic support needs a physical contract

Configured Indian cluster pairs extend to 402.7 km in the Delhi group and 463.7 km in the Hyderabad group. DWD clusters are not all local either; the north-coastal group reaches 330.6 km. These are cluster-pair distances, not a claim that every pair is used for every row.

The existing neighbour implementation chooses nearby candidates within a named cluster and checks observation age, but does not enforce a physical maximum radius, elevation compatibility or pressure-datum compatibility. A nonzero neighbour count therefore does not prove suitable meteorological support.

### 6. Model lineage and evaluation remain separate issues

The live service loads `models/phase10_final.joblib` and `models/phase10_climatology.joblib`, not the Iteration 10R models. Its event feature list has 108 entries and no explicit label, episode, original-target or dew-point feature names. That allowlist check is helpful but not a full leakage audit.

The saved `train_phase10_full_data.py` loads the old India feature tables. It fits on 2022 plus January–June 2023 and calibrates on July–December 2023; the same latter block is used for threshold/persistence selection. With the current visible feature tables those blocks contain 269,028 fit rows and 94,402 calibration/selection rows. Script contents alone cannot prove precisely which version produced an older binary; use the R0 manifest as the frozen comparator and record an execution receipt for the next training run.

A saved notebook's success assertion, many downloaded files, or a large DWD score does not establish leak-free Indian performance. No maximum achievable accuracy or fraction of the current recall loss attributable to each data issue was measured in this audit.

## What to do next

1. Keep original observations and current model frozen. Resolve the pressure contract first; preserve original pressure values/type, split incompatible series and avoid unsupported conversions.
2. Build a source-specific data acceptance/unknown policy. Preserve QC flags and reported/derived RH provenance; do not reuse NOAA code meanings for DWD QN levels. DWD QN=3 means automated control/correction, not the NOAA error-code meaning.
3. Define cadence-aware temporal windows and physically compatible neighbours. Missing support means unavailable evidence, not a healthy or faulty station.
4. Rebuild one versioned development dataset and features from those decisions. Separate fit, early stopping, calibration, policy selection and confirmation; retain an actually untouched final set.
5. Retrain/compare the existing rule + tree baseline on those fixed conditions. Only then test a small neural challenger or acquire specific missing station/time periods. Prefer authorized Indian AWS observations with measured T/P/RH and heartbeat/maintenance information where available.

## Reproducible evidence

Computed results: `reports/TRAINING_DATA_AUDIT_2026_09_11.json`.
Read-only audit utility: `tools/audit_training_data_readonly.py`.
No source data or model weights were changed during this audit. Separate R0 work fixed the dashboard/evidence presentation and failure-aware verification; it did not improve model accuracy.

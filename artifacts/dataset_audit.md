# SkyGuard AI: Ground-Truth Dataset Audit Report

**Audit Execution Time**: `2026-09-26T10:00:05.641109+00:00`  
**Audit Verification System**: `SkyGuard AI Production MLOps Verifier`  

## 1. Primary Historical Dataset (NOAA ISD Surface Archive)

- **File Path**: `data\archive\legacy_noaa_aws\aws_observations_2022_2024.csv`
- **Physical File Size**: `109.35 MB` (114,660,436 bytes)
- **Total Audited Observations**: **578,448 rows**
- **Temporal Span**: `2022-01-01` to `2024-12-31` (3 Complete Years)
- **Unique Station Count**: **24 stations**
- **Scientific Provenance**: `HISTORICAL_SURFACE_OBSERVATIONS (NOAA ISD exchanged via WMO GTS)`

### Spatial Holdout Stations Breakdown

| Station WMO ID | Name / Description | Observations in Dataset | Role in Training |
| :--- | :--- | :--- | :--- |
| `42131099999` | HISSAR | 8,316 | Unseen Spatial Holdout Test |
| `43086099999` | RAMGUNDAM | 8,478 | Unseen Spatial Holdout Test |
| `43233099999` | CHITRADURGA | 7,338 | Unseen Spatial Holdout Test |
| `43331099999` | M.O. PONDICHERRY | 8,208 | Unseen Spatial Holdout Test |
| **TOTAL HOLDOUT** | **4 Stations** | **32,340 rows** | **Zero Spatial Data Leakage** |

## 2. All-India AWS Master Catalog

- **File Path**: `data\stations\imd_aws_master.csv`
- **Total Catalog Stations**: **1,153 stations** across 37 states/UTs
- **Provenance**: `METADATA_CATALOG (Official IMD AWS Master Station List)`

## 3. Labelled Synthetic Benchmark Splits

- **Provenance Classification**: `SYNTHETIC_FAULT_BENCHMARK (Controlled offline injection for ML comparator testing)`
- **Scientific Disclaimer**: *Labels are synthetically injected anomalies over historical weather observations. Not certified field failure tags.*

| Split File | Rows | Size (MB) | Columns |
| :--- | :--- | :--- | :--- |
| `episodes.csv` | 559 | 0.11 MB | 13 |
| `manifest.csv` | 5 | 0.0 MB | 4 |
| `station_test.csv` | 10,516 | 2.88 MB | 35 |
| `time_test.csv` | 182,276 | 50.49 MB | 35 |
| `train.csv` | 182,362 | 49.85 MB | 35 |
| `validation.csv` | 181,470 | 50.43 MB | 35 |

---
*Report generated deterministically by `scripts/verify_dataset.py` with zero simulated numbers.*

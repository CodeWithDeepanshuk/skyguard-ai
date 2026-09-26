# SkyGuard AI: Meteorological Data Provenance & Ground-Truth Registry

**Document ID**: `docs/DATA_PROVENANCE.md`  
**System Version**: `1.2.0`  
**SIH Problem Statement**: 26073 (Automated Quality Control and Fault Detection for Automated Weather Stations)  
**Last Verified**: 2026-09-26  

---

## 1. Architectural Mandate: Unambiguous Data Provenance

In meteorological machine learning, data provenance integrity is paramount. Models trained or evaluated without clear separation between **physical field observations** and **controlled synthetic benchmarks** produce unscientific and untrustworthy results before operational agencies (IMD/MoES).

SkyGuard AI enforces a formal taxonomy of **Four Data Provenance Tiers**:

```
+--------------------------------------------------------------------------------------------------+
|                                  SKYGUARD AI DATA PROVENANCE TIERS                               |
+--------------------------------------------------------------------------------------------------+
                                                   |
       +--------------------+----------------------+--------------------+--------------------+
       |                    |                                           |                    |
+------v-------------+ +----v----------------+                 +--------v-----------+ +------v-------------+
|   TIER 1: REAL     | |    TIER 2: REAL     |                 |  TIER 3: SYNTHETIC | |  TIER 4: REANALYSIS|
|   OPERATIONAL      | |    HISTORICAL       |                 |  BENCHMARK         | |  REFERENCE         |
|   (IMD AWS / WIS2) | | (NOAA ISD Archive)  |                 | (Controlled Injs)  | | (Open-Meteo Grid)  |
+--------------------+ +---------------------+                 +--------------------+ +--------------------+
```

---

## 2. Master Dataset Inventory & Verification Summary

The table below reflects the exact physical datasets present on disk, audited deterministically by [`scripts/verify_dataset.py`](../scripts/verify_dataset.py):

| Dataset Name | Physical Disk Path | Provenance Classification | Volume / Rows | Temporal Range | Operational Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **All-India AWS Master Catalog** | `data/stations/imd_aws_master.csv` | `METADATA_CATALOG` | 1,153 Stations | Static (37 States/UTs) | Ground-truth station coordinates, elevations, and district mappings. |
| **Primary Historical Surface Archive** | `data/archive/legacy_noaa_aws/aws_observations_2022_2024.csv` | `REAL_HISTORICAL` | **578,448 rows** (109.35 MB) | `2022-01-01` to `2024-12-31` | Baseline historical training and temporal evaluation across 24 Indian stations. |
| **Spatial Holdout Split** | Extracted from `aws_observations_2022_2024.csv` | `REAL_HISTORICAL_HOLDOUT` | **32,340 rows** | `2022-01-01` to `2024-12-31` | 4 completely unseen stations (Hissar, Ramgundam, Chitradurga, Pondicherry) for spatial generalizability validation. |
| **Official IMD Telemetry** | `data/processed/official_imd_aws_observations.csv` | `REAL_OPERATIONAL` | Streamed batches | Real-time | Live direct Aspirated 2m AWS telemetry ingested via official IMD API and WIS 2.0 endpoints. |
| **Controlled Synthetic Fault Benchmark** | `data/labelled/` (`station_test.csv`, `time_test.csv`, `train.csv`, `validation.csv`) | `SYNTHETIC_BENCHMARK` | 567,145 total rows | Controlled seeds | Offline comparative benchmark for measuring detection latency, precision, and recall under known injected fault episodes. |
| **Numerical Reanalysis Context** | Runtime Open-Meteo API | `REANALYSIS_REFERENCE` | Dynamically cached | Dynamic | Mesoscale spatial context for boundary checks. Explicitly marked: *Context only — not direct anomaly model input*. |

---

## 3. Strict Three-Parameter Physical Contract

SkyGuard AI enforces a strict three-parameter scope for all anomaly detection and quality control algorithms:

1. **Air Temperature ($T$) [$^\circ\text{C}$]**: Aspirated dry-bulb air temperature at 2.0m standard agrometeorological height.
2. **Atmospheric Pressure ($P$) [$\text{hPa}$]**: Station barometer pressure ($P_{\text{stn}}$) or Altimeter Sea-Level Pressure ($P_{\text{msl}}$/QNH).
3. **Relative Humidity ($\text{RH}$) [$\%$]**: Capacitive thin-film polymer hygrometer reading.

### Rules Governing Parameters:
- **Zero Supplementary Feature Contamination**: Wind speed, wind direction, solar radiation, and tipping-bucket rainfall are **never** introduced into the core anomaly-detection neural network.
- **Explicit Pressure Semantics**:
  - `STATION_PRESSURE`: Absolute pressure at station elevation.
  - `MEAN_SEA_LEVEL_PRESSURE`: Hydrostatically reduced pressure to mean sea level.
  - `ALTIMETER_QNH`: Pressure setting for aviation altimeters.
  - Stations reporting MSLP are flagged `is_mslp = True` to prevent false physical violation triggers on high-elevation stations (e.g., Chitradurga at 733m ASL).
- **Explicit Humidity Semantics**:
  - `DIRECT`: Measured directly by capacitive RH sensor.
  - `DERIVED_FROM_DEWPOINT`: Computed using the Magnus-Tetens formula when only dry-bulb and dew-point temperatures are available from METAR:
    $$\text{RH} = 100 \cdot \frac{\exp\left(\frac{17.625 \cdot T_d}{243.04 + T_d}\right)}{\exp\left(\frac{17.625 \cdot T}{243.04 + T}\right)}$$

---

## 4. Scientific Truth & Non-Fabrication Standards

1. **Zero Data Hallucination**: If a station has not transmitted an observation in the current reporting cycle, the platform explicitly renders:  
   `"No live observation available"`  
   rather than synthesizing an interpolated or plausible value.
2. **Catalog Membership $\ne$ Operational Health**: Presence of a station in the 1,153 master station list does not grant it "Healthy" status. Catalog-only stations without verified live telemetry are flagged:  
   `quality_state: "UNVERIFIED"`, `catalog_only: true`.
3. **Causal History Guarantee**: Feature calculations use strictly causal backward rolling windows ($t-H \dots t$). Future observations are never accessed during feature calculation, preventing temporal data leakage.
4. **Synthetic Benchmark Separation**: Synthetic benchmark results from `data/labelled/` are strictly designated as **algorithmic comparator metrics**, and must never be portrayed as certified field hardware failure records from IMD technicians.

---
*Verified against active repository storage by `scripts/verify_dataset.py`.*

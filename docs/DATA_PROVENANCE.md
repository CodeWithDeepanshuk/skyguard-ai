# SkyGuard AI — Meteorological Data Provenance & Scientific Contracts
**Document ID:** `docs/DATA_PROVENANCE.md`  
**Author:** Meteorological Visualization Engineer & ML Platform Architect  
**Project:** SkyGuard AI · SIH Problem Statement 26073  
**Status:** OFFICIAL CONTRACT  

---

## 1. Strict Three-Parameter Physical Contract

SkyGuard AI enforces a strict, unalterable physical contract for its anomaly detection models:
1. **Air Temperature ($T$) [°C]**
2. **Station Atmospheric Pressure ($P$) [hPa]**
3. **Relative Humidity ($\text{RH}$) [%]**

Under competition guidelines and physical principles:
- **No Extra Meteorological Variables**: Wind speed, wind direction, solar radiation, and precipitation are **never** introduced into the anomaly-detection neural network.
- **Context Layers Disclaimers**: External radar, precipitation, and satellite layers displayed on maps are visually marked:  
  `"Context only — not anomaly-model input"`.

---

## 2. Telemetry Ingestion Sources & Priority Hierarchy

| Provider | Data Origin | Station Fleet | Ingestion Method | Role & Contract |
|---|---|---|---|---|
| **IMD AWS** | Direct physical AWS/ARG loggers | 410 Active | IMD API / WIS 2.0 | **Primary Ground Truth**. Direct aspirated 2m sensor readings. |
| **IMD WIS 2.0** | WMO Global Exchange (SYNOP) | 133 Principal | MQTT / OAPI | **Official Public Fallback**. Global standardized meteorological observations. |
| **Aviation METAR** | Airport ICAO Observatories | 52 Airports | NOAA MADIS / AviationWeather | **Airport Calibration Baseline**. Explicitly marked: RH derived from dew point; Pressure is QNH. |
| **MOSDAC / Reanalysis** | Satellite & Numerical Model | Regional Grid | Open-Meteo Reanalysis | **Environmental Context Only**. Never persisted as station observation. |
| **Evaluation Archive** | Frozen Benchmark (2022–2024) | 543 Stations | Local Durable Parquet/CSV | **Scientific Holdout Truth**. 578,450 immutable observations. |

---

## 3. Pressure & Humidity Semantics

### Pressure Semantics
Atmospheric pressure exhibits extreme sensitivity to terrain elevation (approx. $-1.2\,\text{hPa} / 10\,\text{m}$ in standard atmosphere).
- **Rule 1**: Station pressure ($P_{\text{stn}}$) and Sea-Level Pressure ($P_{\text{msl}}$ / QNH) are **never silently mixed**.
- **Rule 2**: Spatial buddy checks apply elevation-invariant pressure tendencies ($\Delta P / \Delta t$) rather than raw pressure differences between stations at differing altitudes.

### Relative Humidity Semantics
- When ingesting physical capacitive sensors, raw relative humidity is recorded.
- When ingesting METAR reports that provide only temperature and dew point ($T, T_d$), relative humidity is derived using the Magnus-Tetens approximation:
  $$\text{RH} = 100 \cdot \frac{\exp\left(\frac{17.625 \cdot T_d}{243.04 + T_d}\right)}{\exp\left(\frac{17.625 \cdot T}{243.04 + T}\right)}$$
- The record is explicitly stamped: `humidity_observation_type: "DERIVED_FROM_DEWPOINT"`.

---

## 4. Scientific Truth & Non-Fabrication Rules

1. **Zero Fabrication**: If a station has not transmitted an observation in the current reporting cycle, the UI explicitly renders:  
   `"No live observation available"`  
   instead of synthesizing an interpolated or plausible number.
2. **Catalog Membership $\ne$ Operational Health**: A station being present in `all_india_aws_network.csv` does not grant it "Healthy" status. Catalog-only stations without verified live telemetry are flagged:  
   `quality_state: "UNVERIFIED"`, `catalog_only: true`.
3. **Causal History Guarantee**: Feature calculations use strictly causal backward rolling windows ($t-H \dots t$). Future observations are never accessed during feature calculation or model inference.

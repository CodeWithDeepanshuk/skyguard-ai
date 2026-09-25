# SkyGuard AI — Phase 6 Causal Correction & Sensor Health Audit
**Smart India Hackathon 2026 | Problem Statement 26073: Automatic Weather Station Intelligence**
**Generated:** 2026-09-25T05:18:28Z | **Provider:** Official IMD AWS Portal (1,172 Observations)

## 1. Executive Summary & Health Distribution
- **Total Monitored Stations:** 1172
- **Healthy Stations (Score >= 70):** 1157 (98.72%)
- **Degraded Stations (Score 30-69):** 3
- **Critical Failure Stations (Score < 30):** 11
- **Safe Auto-Repair Eligible (Tier 1):** 4
- **Human Field Verification Required (Tier 2):** 11

## 2. Phase 6 Causal Spatial Correction Table
| Incident ID | Station Name | State | Parameter | Reported | IDW Estimate | 90% Uncertainty [L, U] | Safe Repair Tier | Health | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `INC-IMD-WBDJL000` | **DARJEELING_MO** | WEST_BENGAL | `temperature` | `13.9` | **`18.52`** | `[12.23, 24.82]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-UTWAI000` | **TH_KOSIYAKUTOLI** | UTTARAKHAND | `pressure` | `948.6` | **`1007.35`** | `[991.18, 1023.52]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-NAWOK000` | **WOKHA** | NAGALAND | `pressure` | `1077.9` | **`1010.09`** | `[984.04, 1036.14]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-ORPLU000` | **PHULBANI** | ODISHA | `pressure` | `1007.6` | **`994.46`** | `[971.48, 1017.44]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-PJSSB000` | **SRI_ANADPUR_SAHIB_IMDJINDWADI** | PUNJAB | `pressure` | `971.3` | **`994.71`** | `[969.58, 1019.84]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-KEKOU000` | **KOVILKADAVU** | KERALA | `relative_humidity` | `52.0` | **`85.57`** | `[59.56, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KEPAV000` | **PAMPADUMPARA** | KERALA | `pressure` | `904.4` | **`997.92`** | `[962.26, 1033.58]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-HPHAV000` | **HAMIRPUR_NERI** | HIMACHAL_PRADESH | `pressure` | `968.8` | **`996.65`** | `[975.23, 1018.07]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-MATOD000` | **TONDAPUR_AWS400** | MAHARASHTRA | `pressure` | `954.7` | **`999.72`** | `[983.41, 1016.03]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-MPAAK000` | **AMARKANTAK_CRCH** | MADHYA_PRADESH | `pressure` | `871.6` | **`1000.26`** | `[997.21, 1003.3]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-JKPNC000` | **POONCH** | JAMMU_AND_KASHMIR | `pressure` | `857.5` | **`1000.14`** | `[975.67, 1024.61]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-JHNTT000` | **NETARHAT** | JHARKHAND | `pressure` | `943.0` | **`999.66`** | `[974.2, 1025.13]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-KAAGB000` | **AGUMBE** | KARNATAKA | `pressure` | `948.3` | **`1010.25`** | `[1003.83, 1016.66]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-MPAHP000` | **AHMADPUR_IITM** | MADHYA_PRADESH | `temperature` | `31.4` | **`25.24`** | `[23.57, 26.91]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A3EACA` | **HINGOLI** | MAHARASHTRA | `pressure` | `984.1` | **`992.35`** | `[956.15, 1028.56]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |

## 3. Scientific Methodology & Compliance Guardrails
- **Lapse-Rate Compensated IDW:** All spatial consensus estimations account for vertical lapse rate (6.5°C/km for temperature, 12 hPa/100m for barometric pressure).
- **Adaptive 90% Uncertainty Intervals:** Normal quantile bounds ($1.645\sigma$) computed dynamically from regional peer dispersion.
- **Data Integrity Rule:** The raw reported observation is NEVER modified in-place or deleted; corrections are offered as calibrated imputation streams with cryptographic audit provenance.
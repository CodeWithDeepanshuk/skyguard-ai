# SkyGuard AI — Phase 6 Causal Correction & Sensor Health Audit
**Smart India Hackathon 2026 | Problem Statement 26073: Automatic Weather Station Intelligence**
**Generated:** 2026-09-25T07:04:39Z | **Provider:** Official IMD AWS Portal (1,172 Observations)

## 1. Executive Summary & Health Distribution
- **Total Monitored Stations:** 1172
- **Healthy Stations (Score >= 70):** 1157 (98.72%)
- **Degraded Stations (Score 30-69):** 4
- **Critical Failure Stations (Score < 30):** 11
- **Safe Auto-Repair Eligible (Tier 1):** 4
- **Human Field Verification Required (Tier 2):** 11

## 2. Phase 6 Causal Spatial Correction Table
| Incident ID | Station Name | State | Parameter | Reported | IDW Estimate | 90% Uncertainty [L, U] | Safe Repair Tier | Health | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `INC-IMD-A0AEF408` | **CHINTAPALLI_AMFU** | ANDHRA_PRADESH | `pressure` | `995.3` | **`894.99`** | `[883.57, 906.4]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0A1C9D2` | **KEYLONG** | HIMACHAL_PRADESH | `temperature` | `12.5` | **`6.05`** | `[-2.01, 14.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A1D476` | **SHIMALA_CPRI** | HIMACHAL_PRADESH | `pressure` | `None` | **`780.97`** | `[734.36, 827.57]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 10% | Sensor data missing or dead-lettered. Physica... |
| `INC-IMD-A0B4F2C4` | **RAMBAGH** | JAMMU_AND_KASHMIR | `pressure` | `None` | **`859.0`** | `[765.08, 952.92]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 10% | Sensor data missing or dead-lettered. Physica... |
| `INC-IMD-KEVNJ000` | **VENKURINJI** | KERALA | `pressure` | `1010.2` | **`903.6`** | `[848.7, 958.51]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-LDPDO000` | **PADUM_KVK** | LADAKH | `temperature` | `10.8` | **`27.77`** | `[19.35, 36.2]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty TEMPERATURE sen... |
| `INC-IMD-LDNYO000` | **NYOMA_KVK** | LADAKH | `pressure` | `None` | **`561.75`** | `[493.68, 629.82]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 10% | Sensor data missing or dead-lettered. Physica... |
| `INC-IMD-A0A59C94` | **PARALAKHEMUNDI** | ODISHA | `temperature` | `41.4` | **`27.39`** | `[23.56, 31.22]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55D635B4` | **KALPA** | HIMACHAL_PRADESH | `pressure` | `None` | **`787.86`** | `[734.8, 840.92]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 10% | Sensor data missing or dead-lettered. Physica... |
| `INC-IMD-55D65052` | **MOORANG** | HIMACHAL_PRADESH | `temperature` | `None` | **`14.61`** | `[10.38, 18.84]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 10% | Sensor data missing or dead-lettered. Physica... |
| `INC-IMD-55D64DF6` | **SANGLA** | HIMACHAL_PRADESH | `temperature` | `None` | **`13.39`** | `[9.99, 16.79]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 10% | Sensor data missing or dead-lettered. Physica... |
| `INC-IMD-55E67808` | **FAGU** | HIMACHAL_PRADESH | `pressure` | `None` | **`783.64`** | `[734.34, 832.93]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 10% | Sensor data missing or dead-lettered. Physica... |
| `INC-IMD-55D2E6E6` | **RAJPURA** | PUNJAB | `pressure` | `None` | **`928.8`** | `[888.83, 968.77]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 10% | Sensor data missing or dead-lettered. Physica... |
| `INC-IMD-ARZIO000` | **ZIRO_MANIPOLYANG** | ARUNACHAL_PRADESH | `temperature` | `15.6` | **`21.64`** | `[17.27, 26.01]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-TEDLL000` | **DULLAPALLY** | TELANGANA | `temperature` | `39.3` | **`26.39`** | `[25.25, 27.54]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |

## 3. Scientific Methodology & Compliance Guardrails
- **Lapse-Rate Compensated IDW:** All spatial consensus estimations account for vertical lapse rate (6.5°C/km for temperature, 12 hPa/100m for barometric pressure).
- **Adaptive 90% Uncertainty Intervals:** Normal quantile bounds ($1.645\sigma$) computed dynamically from regional peer dispersion.
- **Data Integrity Rule:** The raw reported observation is NEVER modified in-place or deleted; corrections are offered as calibrated imputation streams with cryptographic audit provenance.
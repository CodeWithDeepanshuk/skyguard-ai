# SkyGuard AI — Phase 6 Causal Correction & Sensor Health Audit
**Smart India Hackathon 2026 | Problem Statement 26073: Automatic Weather Station Intelligence**
**Generated:** 2026-09-25T07:50:26Z | **Provider:** Official IMD AWS Portal (1,172 Observations)

## 1. Executive Summary & Health Distribution
- **Total Monitored Stations:** 1172
- **Healthy Stations (Score >= 70):** 1120 (95.56%)
- **Degraded Stations (Score 30-69):** 18
- **Critical Failure Stations (Score < 30):** 33
- **Safe Auto-Repair Eligible (Tier 1):** 19
- **Human Field Verification Required (Tier 2):** 33

## 2. Phase 6 Causal Spatial Correction Table
| Incident ID | Station Name | State | Parameter | Reported | IDW Estimate | 90% Uncertainty [L, U] | Safe Repair Tier | Health | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `INC-IMD-A0B24184` | **PALAMPUR_AMFU** | HIMACHAL_PRADESH | `pressure` | `1082.3` | **`907.56`** | `[852.79, 962.33]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-NAWOK000` | **WOKHA** | NAGALAND | `pressure` | `1077.9` | **`1060.81`** | `[936.8, 1184.83]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0AEF408` | **CHINTAPALLI_AMFU** | ANDHRA_PRADESH | `pressure` | `995.3` | **`894.99`** | `[883.57, 906.4]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0A1840A` | **JAGDISHPUR** | HARYANA | `pressure` | `1005.5` | **`928.96`** | `[900.46, 957.46]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-KEVNJ000` | **VENKURINJI** | KERALA | `pressure` | `1010.2` | **`903.6`** | `[848.7, 958.51]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-KEPOD000` | **PONMUDI** | KERALA | `pressure` | `942.6` | **`997.39`** | `[990.5, 1004.29]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-MICAW000` | **CHAWNHU** | MIZORAM | `pressure` | `888.1` | **`1010.7`** | `[1000.99, 1020.41]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0A59C94` | **PARALAKHEMUNDI** | ODISHA | `temperature` | `41.4` | **`27.39`** | `[23.56, 31.22]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-B48A9436` | **MATHURA** | UTTAR_PRADESH | `pressure` | `963.3` | **`1007.66`** | `[1005.21, 1010.12]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-TEDLL000` | **DULLAPALLY** | TELANGANA | `temperature` | `39.3` | **`26.39`** | `[25.25, 27.54]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-ARSEL000` | **SEPPA_PAMPOLI** | ARUNACHAL_PRADESH | `pressure` | `1013.1` | **`716.14`** | `[672.05, 760.22]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-ASNWI000` | **NERIWALAM** | ASSAM | `temperature` | `37.6` | **`26.92`** | `[24.83, 29.01]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55C071EE` | **LIKERA** | ODISHA | `temperature` | `15.4` | **`25.21`** | `[24.35, 26.06]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55EDE604` | **CHAMATA** | ASSAM | `temperature` | `34.5` | **`27.74`** | `[27.0, 28.48]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55FC7602` | **MEHADRIGADDA_DAM** | ANDHRA_PRADESH | `temperature` | `39.4` | **`26.93`** | `[25.41, 28.45]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0AAA14E` | **SHEOPUR** | MADHYA_PRADESH | `temperature` | `13.6` | **`26.86`** | `[23.92, 29.81]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55C7CE86` | **KHINJARSARAI** | BIHAR | `temperature` | `36.2` | **`25.16`** | `[22.33, 27.99]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0AA6A82` | **SATNA** | MADHYA_PRADESH | `pressure` | `1004.6` | **`982.06`** | `[952.04, 1012.08]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-WBMNE000` | **MAL** | WEST_BENGAL | `pressure` | `1014.3` | **`889.93`** | `[832.18, 947.67]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-55CAE5DE` | **LENGPUI** | MIZORAM | `temperature` | `12.2` | **`24.23`** | `[21.36, 27.11]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-MPAHP000` | **AHMADPUR_IITM** | MADHYA_PRADESH | `temperature` | `31.4` | **`25.0`** | `[23.43, 26.58]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-RAHAH000` | **HANUMANGARH 1_KVK** | RAJASTHAN | `temperature` | `32.7` | **`27.44`** | `[26.35, 28.53]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-DENCU000` | **NORTHCAP_UNIVERSITY** | DELHI | `pressure` | `1024.1` | **`1006.71`** | `[1001.9, 1011.52]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0B51D1E` | **RANCHI_AMFU** | JHARKHAND | `pressure` | `1003.1` | **`943.24`** | `[889.89, 996.6]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0A6B3A4` | **COIMBATORE_AMFU** | TAMIL_NADU | `pressure` | `1008.8` | **`971.2`** | `[953.92, 988.48]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-UTWAI000` | **TH_KOSIYAKUTOLI** | UTTARAKHAND | `pressure` | `948.6` | **`814.43`** | `[771.0, 857.87]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0A65E84` | **PAIYUR_AMFU** | TAMIL_NADU | `temperature` | `30.7` | **`25.34`** | `[22.04, 28.64]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-56187A86` | **TENALI** | ARUNACHAL_PRADESH | `temperature` | `13.7` | **`25.9`** | `[18.08, 33.72]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-BIKON000` | **BEGUSARAI_KVK** | BIHAR | `temperature` | `31.1` | **`24.67`** | `[23.47, 25.86]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55C927CE` | **DENKANIKOTTAI** | TAMIL_NADU | `temperature` | `21.7` | **`27.87`** | `[24.81, 30.94]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-KAMAK000` | **MANDYA_KVK** | KARNATAKA | `temperature` | `15.4` | **`23.55`** | `[20.07, 27.02]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55ED9E46` | **THARALI** | UTTARAKHAND | `relative_humidity` | `53.0` | **`95.43`** | `[86.64, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0AD68B6` | **KOZHIKODE** | KERALA | `relative_humidity` | `49.0` | **`99.89`** | `[96.89, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0ACFF2E` | **KHUSINAGAR** | UTTAR_PRADESH | `temperature` | `19.3` | **`24.21`** | `[21.95, 26.46]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MPDAO000` | **MADIYAHAR_KVK** | MADHYA_PRADESH | `relative_humidity` | `55.0` | **`98.57`** | `[95.57, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-BIDNP000` | **DANAPUR_DPS** | BIHAR | `temperature` | `32.3` | **`25.47`** | `[21.62, 29.32]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-MAGIR000` | **GIRIVAN** | MAHARASHTRA | `temperature` | `22.0` | **`27.62`** | `[25.64, 29.6]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A13784` | **MANDKOLA** | HARYANA | `relative_humidity` | `18.0` | **`75.81`** | `[44.39, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KEMUC000` | **MUNAKKAL** | KERALA | `relative_humidity` | `9.0` | **`91.3`** | `[76.59, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-MISED000` | **SERCHHIP** | MIZORAM | `relative_humidity` | `10.0` | **`88.38`** | `[46.65, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0A078A6` | **MOHALI** | PUNJAB | `relative_humidity` | `15.0` | **`88.0`** | `[76.63, 99.37]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0B2741E` | **MASSOURI** | UTTARAKHAND | `relative_humidity` | `22.0` | **`97.46`** | `[89.75, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-UPINT000` | **INTEGRAL_UNIVERSITY** | UTTAR_PRADESH | `relative_humidity` | `27.0` | **`96.12`** | `[70.08, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55C474D4` | **YINGKIONG** | ARUNACHAL_PRADESH | `relative_humidity` | `10.0` | **`95.13`** | `[84.55, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55E24EBC` | **KODANGAL** | TELANGANA | `relative_humidity` | `7.0` | **`73.93`** | `[58.23, 89.63]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-JHLOA000` | **LOHARDAGA_KVK** | JHARKHAND | `relative_humidity` | `11.0` | **`93.29`** | `[78.83, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-MPGUB000` | **ARON_KVK** | MADHYA_PRADESH | `relative_humidity` | `24.0` | **`92.87`** | `[75.67, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-ORSHY000` | **MAYURBHANJ_KVK** | ODISHA | `relative_humidity` | `24.0` | **`99.72`** | `[95.75, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-5B761DD2` | **COLABA_TEST** | MAHARASHTRA | `relative_humidity` | `35.0` | **`94.49`** | `[77.81, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-WBTAR000` | **DEGREE_COLLEGE_TARAKESWAR** | WEST_BENGAL | `relative_humidity` | `66.0` | **`97.8`** | `[92.14, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-ASAGG000` | **AGIA_AEGCL** | ASSAM | `relative_humidity` | `66.0` | **`95.83`** | `[73.59, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-ASUMP000` | **UMPANAI_APDCL** | ASSAM | `relative_humidity` | `48.0` | **`97.52`** | `[91.06, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |

## 3. Scientific Methodology & Compliance Guardrails
- **Lapse-Rate Compensated IDW:** All spatial consensus estimations account for vertical lapse rate (6.5°C/km for temperature, 12 hPa/100m for barometric pressure).
- **Adaptive 90% Uncertainty Intervals:** Normal quantile bounds ($1.645\sigma$) computed dynamically from regional peer dispersion.
- **Data Integrity Rule:** The raw reported observation is NEVER modified in-place or deleted; corrections are offered as calibrated imputation streams with cryptographic audit provenance.
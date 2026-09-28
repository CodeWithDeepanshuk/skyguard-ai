# SkyGuard AI — Phase 6 Causal Correction & Sensor Health Audit
**Smart India Hackathon 2026 | Problem Statement 26073: Automatic Weather Station Intelligence**
**Generated:** 2026-09-27T12:37:44Z | **Provider:** Official IMD AWS Portal (1,172 Observations)

## 1. Executive Summary & Health Distribution
- **Total Monitored Stations:** 1153
- **Healthy Stations (Score >= 70):** 839 (72.77%)
- **Degraded Stations (Score 30-69):** 72
- **Critical Failure Stations (Score < 30):** 61
- **Safe Auto-Repair Eligible (Tier 1):** 253
- **Human Field Verification Required (Tier 2):** 61

## 2. Phase 6 Causal Spatial Correction Table
| Incident ID | Station Name | State | Parameter | Reported | IDW Estimate | 90% Uncertainty [L, U] | Safe Repair Tier | Health | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `INC-IMD-55C9C43C` | **LOWER_KOTHAIYAR** | TAMIL_NADU | `relative_humidity` | `100.0` | **`80.96`** | `[59.96, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55CE0316` | **MEENANGADI** | KERALA | `relative_humidity` | `100.0` | **`97.55`** | `[90.76, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CE4ECE` | **PALLURUTHY** | KERALA | `relative_humidity` | `100.0` | **`59.64`** | `[33.58, 85.7]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55D7E126` | **ASIFABAD** | TELANGANA | `relative_humidity` | `100.0` | **`78.12`** | `[55.98, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55D94B64` | **LORMI** | CHHATTISGARH | `relative_humidity` | `100.0` | **`90.03`** | `[60.0, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55D97EFE` | **BEMETARA_DURG** | CHHATTISGARH | `relative_humidity` | `100.0` | **`98.08`** | `[80.29, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55D99D0C` | **SAKTI** | CHHATTISGARH | `relative_humidity` | `100.0` | **`80.53`** | `[38.49, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55D9A644` | **NAWAGARH** | CHHATTISGARH | `relative_humidity` | `100.0` | **`71.05`** | `[22.35, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55DA3AFA` | **MULTAI** | MADHYA_PRADESH | `relative_humidity` | `100.0` | **`86.16`** | `[59.38, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55E95E62` | **ENAMAKKAL** | KERALA | `relative_humidity` | `100.0` | **`64.69`** | `[28.22, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55E9BD90` | **ISLAMNAGAR** | MADHYA_PRADESH | `relative_humidity` | `100.0` | **`89.17`** | `[70.96, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55EDE604` | **CHAMATA** | ASSAM | `relative_humidity` | `13.0` | **`91.13`** | `[75.18, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-5618EFE4` | **NANCOWRY** | ANDAMAN_AND_NICOBAR | `temperature` | `40.7` | **`29.47`** | `[27.33, 31.62]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A3F76E` | **NANDED** | MAHARASHTRA | `relative_humidity` | `100.0` | **`54.17`** | `[32.91, 75.43]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0A4B882` | **BOLANGIR** | ODISHA | `relative_humidity` | `100.0` | **`86.6`** | `[60.49, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A5BA78` | **JHARSUGUDA** | ODISHA | `relative_humidity` | `100.0` | **`90.16`** | `[64.3, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A8A4BA` | **GOVINDPURA** | JAMMU_AND_KASHMIR | `temperature` | `38.0` | **`34.45`** | `[28.48, 40.42]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A8F4C6` | **DHAMTARI** | CHHATTISGARH | `relative_humidity` | `7.0` | **`97.97`** | `[86.63, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0A92E86` | **KAWARDHA** | CHHATTISGARH | `relative_humidity` | `100.0` | **`84.05`** | `[52.72, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0A93DF0` | **MAHASAMUND** | CHHATTISGARH | `relative_humidity` | `100.0` | **`82.67`** | `[31.27, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0A94B60` | **RAIGARH** | CHHATTISGARH | `relative_humidity` | `100.0` | **`88.34`** | `[56.76, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A95816` | **RAJNANDGAON** | CHHATTISGARH | `relative_humidity` | `100.0` | **`84.86`** | `[33.37, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0A97EFA` | **BETUL** | MADHYA_PRADESH | `relative_humidity` | `99.0` | **`87.47`** | `[60.0, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0AA342C` | **NARSINGHPUR** | MADHYA_PRADESH | `relative_humidity` | `100.0` | **`91.84`** | `[67.78, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0AA6450` | **SAGAR** | MADHYA_PRADESH | `relative_humidity` | `99.0` | **`85.83`** | `[53.77, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0ADADA8` | **CHIKKANAKALLI** | KARNATAKA | `relative_humidity` | `100.0` | **`69.29`** | `[46.94, 91.65]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-AAAE49D2` | **JHARGRAM** | WEST_BENGAL | `relative_humidity` | `99.0` | **`84.95`** | `[40.57, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-ARKBR000` | **LONGDING** | ARUNACHAL_PRADESH | `pressure` | `1082.8` | **`935.27`** | `[934.07, 936.47]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-ARPSG000` | **PASHIGHAT** | ARUNACHAL_PRADESH | `temperature` | `39.6` | **`32.84`** | `[27.23, 38.45]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-ASBCL000` | **BCPL_DIBRUGARH** | ASSAM | `relative_humidity` | `16.0` | **`49.87`** | `[18.15, 81.59]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-ASBTB000` | **LAKHIMPUR** | ASSAM | `temperature` | `39.1` | **`34.02`** | `[29.38, 38.66]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-ASPNC000` | **PANCHGRAM_AEGCL** | ASSAM | `temperature` | `39.6` | **`31.15`** | `[27.11, 35.18]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-B48A9436` | **MATHURA** | UTTAR_PRADESH | `pressure` | `966.6` | **`965.77`** | `[964.57, 966.97]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-CGBBO000` | **BALOD_AWS400** | CHHATTISGARH | `relative_humidity` | `100.0` | **`63.94`** | `[0.0, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-CGBEM000` | **BEMETARA** | CHHATTISGARH | `relative_humidity` | `100.0` | **`98.08`** | `[80.2, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-CGBMB000` | **BALRAMPUR_AWS400** | CHHATTISGARH | `relative_humidity` | `100.0` | **`80.25`** | `[39.36, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-CGDAC000` | **DAV_SCHOOL** | CHANDIGARH | `pressure` | `966.8` | **`974.09`** | `[959.15, 989.03]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-HPHAV000` | **HAMIRPUR_NERI** | HIMACHAL_PRADESH | `pressure` | `966.2` | **`966.51`** | `[958.28, 974.74]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-JHBQA000` | **BAHRAGORA** | JHARKHAND | `relative_humidity` | `100.0` | **`77.79`** | `[21.59, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-JHKVB000` | **KV_BOKARO** | JHARKHAND | `relative_humidity` | `100.0` | **`72.21`** | `[9.29, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-JHRME000` | **RAMGARH_KVK** | JHARKHAND | `relative_humidity` | `100.0` | **`83.77`** | `[34.25, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-JHSKA000` | **SARAIKELA** | JHARKHAND | `relative_humidity` | `99.0` | **`83.75`** | `[37.45, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KAAGB000` | **AGUMBE** | KARNATAKA | `relative_humidity` | `100.0` | **`81.35`** | `[63.87, 98.83]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KAHSA000` | **HASSAN** | KARNATAKA | `relative_humidity` | `100.0` | **`82.25`** | `[62.69, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KECER000` | **CHERUVANCHERY** | KERALA | `relative_humidity` | `100.0` | **`95.82`** | `[83.38, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEKUE000` | **KUPPADI** | KERALA | `relative_humidity` | `100.0` | **`97.31`** | `[88.61, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEMAX000` | **MANNARKKAD** | KERALA | `relative_humidity` | `100.0` | **`75.04`** | `[53.05, 97.04]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KEMUF000` | **MUNDERI** | KERALA | `relative_humidity` | `100.0` | **`96.07`** | `[80.96, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEPDM000` | **PADAMALA** | KERALA | `relative_humidity` | `100.0` | **`93.68`** | `[80.0, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-KEPIY000` | **PINARAYI** | KERALA | `relative_humidity` | `100.0` | **`93.22`** | `[73.44, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-KEPLB000` | **PALEMAD** | KERALA | `relative_humidity` | `100.0` | **`95.63`** | `[80.99, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEPOD000` | **PONMUDI** | KERALA | `relative_humidity` | `100.0` | **`79.48`** | `[58.97, 99.99]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KEPUN000` | **PUNALUR** | KERALA | `relative_humidity` | `100.0` | **`88.58`** | `[72.17, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-KESEF000` | **SECRETARIAT** | TRIPURA | `relative_humidity` | `7.0` | **`56.58`** | `[9.42, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KEURU000` | **URUMI** | KERALA | `relative_humidity` | `100.0` | **`88.64`** | `[64.04, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-KEVAM000` | **VANNAMADA** | KERALA | `relative_humidity` | `100.0` | **`75.14`** | `[49.28, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-KEVIA000` | **VILANGAD** | KERALA | `relative_humidity` | `100.0` | **`96.21`** | `[85.21, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MACID000` | **NEW_CHHINDWARA** | MADHYA_PRADESH | `relative_humidity` | `100.0` | **`89.62`** | `[68.47, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-MAREK000` | **RAMTEK_AWS400** | MAHARASHTRA | `relative_humidity` | `100.0` | **`83.44`** | `[64.08, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-MISED000` | **SERCHHIP** | MIZORAM | `relative_humidity` | `10.0` | **`80.93`** | `[41.38, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-MPPAC000` | **PACHMARHI_AEC** | MADHYA_PRADESH | `relative_humidity` | `100.0` | **`93.3`** | `[73.35, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-MPSHC000` | **KALYANPUR_KVK** | MADHYA_PRADESH | `relative_humidity` | `100.0` | **`91.16`** | `[70.11, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-ORSHY000` | **MAYURBHANJ_KVK** | ODISHA | `relative_humidity` | `13.0` | **`95.29`** | `[90.27, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-ORSUG000` | **SUNDERGARH** | ODISHA | `relative_humidity` | `100.0` | **`89.09`** | `[55.98, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-PJSSB000` | **SRI_ANADPUR_SAHIB_IMDJINDWADI** | PUNJAB | `pressure` | `969.4` | **`970.17`** | `[961.28, 979.06]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-PUMHC000` | **MAHE_JNV** | PUDUCHERRY | `relative_humidity` | `99.0` | **`94.24`** | `[75.59, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRLAU000` | **LAMBUCHERRA_AGRI_COLLEGE** | TRIPURA | `relative_humidity` | `6.0` | **`58.11`** | `[11.69, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-WBCCA000` | **BCKV_College** | WEST_BENGAL | `relative_humidity` | `99.0` | **`74.28`** | `[24.94, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-WBDUA000` | **KZI_AIRPORT** | WEST_BENGAL | `relative_humidity` | `99.0` | **`65.22`** | `[12.96, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-WBKVH000` | **KVK_HOWRAH_JAGATBALLAVAPUR** | WEST_BENGAL | `relative_humidity` | `100.0` | **`86.74`** | `[72.63, 100.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-5618C7DA` | **MAYABUNDER** | ANDAMAN_AND_NICOBAR | `pressure` | `1014.5` | **`995.25`** | `[994.05, 996.45]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0A078A6` | **MOHALI** | PUNJAB | `pressure` | `1013.6` | **`995.8`** | `[994.6, 997.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0A77A92` | **PANTNAGAR_AMFU** | UTTARAKHAND | `pressure` | `1015.2` | **`996.18`** | `[993.24, 999.12]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0A7DA6A` | **CHITTAURGARH** | RAJASTHAN | `pressure` | `1016.3` | **`995.61`** | `[993.77, 997.45]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0ACB710` | **JHANSI** | UTTAR_PRADESH | `pressure` | `1035.0` | **`995.29`** | `[994.09, 996.49]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-A0B24184` | **PALAMPUR_AMFU** | HIMACHAL_PRADESH | `temperature` | `23.9` | **`34.51`** | `[29.01, 40.02]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0B4DAFA` | **GULMARG** | JAMMU_AND_KASHMIR | `temperature` | `11.2` | **`26.54`** | `[23.92, 29.15]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty TEMPERATURE sen... |
| `INC-IMD-ARDDE000` | **DEED** | ARUNACHAL_PRADESH | `temperature` | `25.8` | **`31.05`** | `[25.3, 36.8]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-ASUMP000` | **UMPANAI_APDCL** | ASSAM | `pressure` | `1014.3` | **`996.55`** | `[990.35, 1002.74]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-DENCU000` | **NORTHCAP_UNIVERSITY** | DELHI | `pressure` | `1023.7` | **`995.28`** | `[994.08, 996.48]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-HACRS000` | **CANAL_RESTHOUSE_SARAGTHAL** | HARYANA | `temperature` | `9.9` | **`31.91`** | `[29.73, 34.1]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty TEMPERATURE sen... |
| `INC-IMD-KEAYY000` | **AYYANKUNNU** | KERALA | `pressure` | `1015.6` | **`995.3`** | `[994.1, 996.5]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-KEMYZ000` | **MULIYAR** | KERALA | `pressure` | `1015.7` | **`995.77`** | `[990.56, 1000.98]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-MALVZ000` | **CHRIST_UNIVERSITY_LAVASA** | MAHARASHTRA | `pressure` | `1016.7` | **`995.62`** | `[994.42, 996.82]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-TEKVE000` | **KAVERI_SIDDIPET** | TELANGANA | `pressure` | `1017.3` | **`995.3`** | `[994.1, 996.5]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-TNJYA000` | **JAYA_ENGINEERING_CLG** | TAMIL_NADU | `pressure` | `1020.5` | **`995.27`** | `[994.07, 996.47]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-WBBJU000` | **BIJPUR** | WEST_BENGAL | `pressure` | `1014.9` | **`995.28`** | `[994.08, 996.48]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-TEHOR000` | **HORTICULTURAL_UNIVERSITY_MOJER** | TELANGANA | `pressure` | `1014.8` | **`996.53`** | `[988.19, 1004.88]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-ASBJA000` | **BAJALI_UNIVERSITY** | ASSAM | `temperature` | `28.4` | **`32.11`** | `[25.46, 38.76]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-NAWOK000` | **WOKHA** | NAGALAND | `pressure` | `1044.4` | **`995.78`** | `[994.05, 997.51]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-ASGHM000` | **GHORAMARA_AEGCL** | ASSAM | `temperature` | `31.5` | **`34.02`** | `[28.41, 39.63]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASBOO000` | **BOKO_AEGCL** | ASSAM | `pressure` | `1019.1` | **`997.94`** | `[986.47, 1009.41]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty PRESSURE sensor... |
| `INC-IMD-55C071EE` | **LIKERA** | ODISHA | `temperature` | `14.2` | **`25.93`** | `[23.79, 28.07]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55E2A39C` | **DEVARAKONDA** | TELANGANA | `temperature` | `37.7` | **`28.07`** | `[26.32, 29.81]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-TEDLL000` | **DULLAPALLY** | TELANGANA | `temperature` | `19.0` | **`31.45`** | `[28.45, 34.46]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-4952C57C` | **PUROLA** | UTTARAKHAND | `temperature` | `29.6` | **`25.73`** | `[18.35, 33.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-49530298` | **GUWAHATI** | ASSAM | `temperature` | `25.2` | **`29.48`** | `[26.89, 32.08]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-558004A2` | **BANDRA** | MAHARASHTRA | `temperature` | `32.7` | **`30.9`** | `[24.66, 37.14]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55800A70` | **MAHALAXMI** | MAHARASHTRA | `temperature` | `29.9` | **`30.36`** | `[24.19, 36.52]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55C6BAEC` | **TELIAMURA** | TRIPURA | `temperature` | `36.2` | **`31.58`** | `[26.86, 36.29]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55C7163C` | **SORENG** | SIKKIM | `temperature` | `16.4` | **`15.94`** | `[11.42, 20.46]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55C8DB62` | **CHEYYAR** | TAMIL_NADU | `temperature` | `34.7` | **`32.23`** | `[28.45, 36.02]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55C8EEF8` | **POONAMALLEE** | TAMIL_NADU | `temperature` | `34.6` | **`34.33`** | `[31.83, 36.83]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55C91C86` | **PERIYA_KALAPET** | PUDUCHERRY | `temperature` | `29.2` | **`34.67`** | `[32.21, 37.13]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55C97960` | **NAGERCOIL** | TAMIL_NADU | `temperature` | `21.1` | **`28.95`** | `[27.21, 30.7]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55CA4BF4` | **NYAPIN** | ARUNACHAL_PRADESH | `temperature` | `22.2` | **`26.76`** | `[23.66, 29.86]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CA7E6E` | **ANNA_UNIVERSITY** | TAMIL_NADU | `temperature` | `29.1` | **`34.96`** | `[33.61, 36.3]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55CA8038` | **LMOIS__KOLAPAKKAM** | TAMIL_NADU | `temperature` | `35.2` | **`34.08`** | `[31.35, 36.8]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CA934E` | **PUZHAL** | TAMIL_NADU | `temperature` | `34.3` | **`34.49`** | `[31.94, 37.03]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CAB5A2` | **SATHYABAMA__UNIVERSITY** | TAMIL_NADU | `temperature` | `34.1` | **`34.53`** | `[31.42, 37.65]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55D4CE16` | **MALAN** | HIMACHAL_PRADESH | `temperature` | `26.6` | **`18.14`** | `[10.18, 26.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55D6A0D6` | **MAJHOULI** | HIMACHAL_PRADESH | `temperature` | `29.8` | **`22.51`** | `[18.36, 26.66]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55D80446` | **ZAINAPORA** | JAMMU_AND_KASHMIR | `temperature` | `31.3` | **`25.95`** | `[23.01, 28.9]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55D81730` | **KHUDWANI** | JAMMU_AND_KASHMIR | `temperature` | `26.3` | **`27.06`** | `[22.3, 31.81]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55D906BC` | **GOLKONDA** | TELANGANA | `temperature` | `25.7` | **`27.17`** | `[21.89, 32.45]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55DA51CE` | **BERASIA** | MADHYA_PRADESH | `temperature` | `27.9` | **`22.85`** | `[16.09, 29.6]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55E28570` | **SERILINGAMPALLY** | TELANGANA | `temperature` | `26.8` | **`27.11`** | `[21.33, 32.89]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55E28BA2` | **KUKATPALLY_JNTU** | TELANGANA | `temperature` | `30.8` | **`25.48`** | `[18.55, 32.41]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55E29606` | **UPPAL** | TELANGANA | `temperature` | `31.1` | **`27.04`** | `[22.54, 31.54]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55E67808` | **FAGU** | HIMACHAL_PRADESH | `temperature` | `15.4` | **`22.26`** | `[17.84, 26.67]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55EDDD4C` | **TIHU** | ASSAM | `temperature` | `28.5` | **`26.83`** | `[19.86, 33.8]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55FE9ED6` | **LONGDING** | ARUNACHAL_PRADESH | `temperature` | `33.5` | **`29.12`** | `[25.3, 32.94]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-5B761DD2` | **COLABA_TEST** | MAHARASHTRA | `temperature` | `26.8` | **`34.09`** | `[29.73, 38.44]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A028DA` | **FARIDKOT_AMFU** | PUNJAB | `temperature` | `37.3` | **`31.8`** | `[30.24, 33.35]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A199AE` | **DIBRUGARH** | ASSAM | `temperature` | `24.5` | **`36.33`** | `[33.2, 39.46]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A1AC34` | **UDAIPUR** | HIMACHAL_PRADESH | `temperature` | `27.2` | **`24.67`** | `[19.32, 30.02]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A1D476` | **SHIMALA_CPRI** | HIMACHAL_PRADESH | `temperature` | `20.8` | **`19.97`** | `[12.05, 27.89]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A45B70` | **KARJAT** | MAHARASHTRA | `temperature` | `30.5` | **`28.84`** | `[20.66, 37.01]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0AAF132` | **MALANGPURA** | JAMMU_AND_KASHMIR | `temperature` | `26.2` | **`27.64`** | `[22.97, 32.31]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0AD5D2C` | **CHERUTHONI** | KERALA | `temperature` | `26.1` | **`27.89`** | `[22.92, 32.85]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B2028E` | **DALHOUSIALHA** | HIMACHAL_PRADESH | `temperature` | `20.3` | **`24.95`** | `[18.95, 30.94]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B3284A` | **THIRUPATHISARAM_AMFU** | TAMIL_NADU | `temperature` | `29.0` | **`24.09`** | `[17.49, 30.69]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B3A08C` | **MEENAMBAKKAM_ISRO** | TAMIL_NADU | `temperature` | `34.7` | **`32.8`** | `[28.49, 37.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B4B1CE` | **KHOWAI** | TRIPURA | `temperature` | `33.4` | **`38.39`** | `[34.28, 42.51]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B4EF60` | **KULGAM_AMFU** | JAMMU_AND_KASHMIR | `temperature` | `23.4` | **`26.84`** | `[23.11, 30.58]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-AAACA106` | **PUDUCHERRY** | PUDUCHERRY | `temperature` | `35.9` | **`32.05`** | `[28.59, 35.51]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-AAACECDE` | **KALAVAI** | TAMIL_NADU | `temperature` | `29.0` | **`34.13`** | `[32.82, 35.45]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-AAACF17A` | **NEYYOOR** | TAMIL_NADU | `temperature` | `28.4` | **`26.26`** | `[19.98, 32.53]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ARKOQ000` | **KOLORAING** | ARUNACHAL_PRADESH | `temperature` | `28.4` | **`25.59`** | `[19.96, 31.21]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ARLOD000` | **LONGDING_NEW** | ARUNACHAL_PRADESH | `temperature` | `28.1` | **`32.91`** | `[29.73, 36.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASAMN000` | **AMINGAON** | ASSAM | `temperature` | `25.5` | **`29.29`** | `[26.24, 32.34]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASBRB000` | **BARPETA_KVK** | ASSAM | `temperature` | `29.1` | **`27.26`** | `[20.77, 33.75]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASDCO000` | **DC_OFC_DIBRUGARH** | ASSAM | `temperature` | `33.0` | **`22.81`** | `[15.65, 29.97]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-ASGUT000` | **GUWAHATI_CITY** | ASSAM | `temperature` | `25.5` | **`29.08`** | `[25.46, 32.69]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASGUV000` | **GAUHATI_UNIVERSITY** | ASSAM | `temperature` | `26.2` | **`24.34`** | `[20.49, 28.18]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASHIL000` | **ALGAPUR_CIRCLE** | ASSAM | `temperature` | `32.1` | **`35.12`** | `[26.31, 43.92]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASISS000` | **IASST_KAMRUP** | ASSAM | `temperature` | `26.6` | **`24.68`** | `[20.92, 28.45]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASKLO000` | **KALAKSHETRA** | ASSAM | `temperature` | `27.2` | **`24.04`** | `[19.94, 28.14]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASNWI000` | **NERIWALAM** | ASSAM | `temperature` | `38.6` | **`32.33`** | `[29.81, 34.85]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-B489804E` | **MUMBAI_SANTA_CRUZ** | MAHARASHTRA | `temperature` | `30.4` | **`35.81`** | `[31.24, 40.39]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-B4898E9C` | **CHENNAI** | TAMIL_NADU | `temperature` | `34.0` | **`33.97`** | `[30.1, 37.84]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-B48A64B2` | **HYDERABAD** | TELANGANA | `temperature` | `31.0` | **`29.46`** | `[21.48, 37.43]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-BIDEI000` | **DEHRI** | BIHAR | `temperature` | `32.4` | **`25.96`** | `[23.16, 28.77]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-BIDNP000` | **DANAPUR_DPS** | BIHAR | `temperature` | `33.4` | **`26.19`** | `[24.58, 27.8]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-BIIIB000` | **IIT_PATNA** | BIHAR | `temperature` | `25.7` | **`28.77`** | `[23.03, 34.52]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-BIPUM000` | **PURNEA_IMD** | BIHAR | `temperature` | `35.8` | **`27.25`** | `[25.35, 29.16]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-BISIE000` | **AURANGABAD_KVK** | BIHAR | `temperature` | `25.6` | **`29.7`** | `[24.09, 35.3]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-HACCV000` | **CANAL_COLONY_VILLAGE_OTTU** | HARYANA | `temperature` | `27.3` | **`31.98`** | `[29.46, 34.51]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-HPSUD000` | **SUNDERNAGAR_KVK** | HIMACHAL_PRADESH | `temperature` | `26.7` | **`25.0`** | `[19.28, 30.72]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-JKBML000` | **BARAMULLA_KVK** | JAMMU_AND_KASHMIR | `temperature` | `26.6` | **`23.14`** | `[12.24, 34.04]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEKNZ000` | **ATHIRAPPILLY** | KERALA | `temperature` | `29.6` | **`28.98`** | `[24.33, 33.63]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEKOU000` | **KOVILKADAVU** | KERALA | `temperature` | `27.2` | **`24.96`** | `[18.18, 31.73]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEKUN000` | **KUNDALA DAM** | KERALA | `temperature` | `19.4` | **`26.15`** | `[22.2, 30.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-KELWR000` | **LOWER_SHOLAYAR** | KERALA | `temperature` | `23.4` | **`29.38`** | `[26.57, 32.18]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-KEPAV000` | **PAMPADUMPARA** | KERALA | `temperature` | `23.6` | **`18.67`** | `[14.27, 23.07]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MABYC000` | **BYCULLA_MUMBAI** | MAHARASHTRA | `temperature` | `31.9` | **`29.78`** | `[23.99, 35.57]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MAIIG000` | **IIGHQ_NEWPANVEL** | MAHARASHTRA | `temperature` | `31.8` | **`28.49`** | `[21.02, 35.95]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MAMTE000` | **MATHERAN** | MAHARASHTRA | `temperature` | `24.2` | **`32.32`** | `[27.6, 37.04]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-MAMUM000` | **MUMBAI AIRPORT** | MAHARASHTRA | `temperature` | `36.1` | **`30.14`** | `[25.83, 34.46]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-MAVIH000` | **VIKHROLI** | MAHARASHTRA | `temperature` | `31.0` | **`30.94`** | `[24.82, 37.06]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MEUMT000` | **UMTREWDAM** | MEGHALAYA | `temperature` | `29.1` | **`24.66`** | `[21.0, 28.32]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MPAHP000` | **AHMADPUR_IITM** | MADHYA_PRADESH | `temperature` | `21.1` | **`29.61`** | `[27.72, 31.51]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-PJHAV000` | **ROPAR_KVK** | PUNJAB | `temperature` | `31.9` | **`33.99`** | `[26.57, 41.41]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-PJIMD000` | **BHAKRA_DAM_IMDNAGAL** | PUNJAB | `temperature` | `25.3` | **`32.15`** | `[27.41, 36.89]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-TEGAC000` | **ESCI_GACHIBOWLI** | TELANGANA | `temperature` | `29.4` | **`30.07`** | `[24.65, 35.49]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TNACS000` | **ACS MEDICAL COLLEGE** | TAMIL_NADU | `temperature` | `36.2` | **`33.57`** | `[30.04, 37.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TNGOV000` | **MAHABALIPURAM** | TAMIL_NADU | `temperature` | `30.0` | **`34.31`** | `[31.71, 36.91]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TNVIL000` | **GOOD WILL SCHOOL VILLIVAKKAM** | TAMIL_NADU | `temperature` | `34.5` | **`34.39`** | `[31.53, 37.24]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRAGG000` | **AGARTALA_AIRPORT** | TRIPURA | `temperature` | `33.3` | **`30.99`** | `[26.07, 35.91]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRAGJ000` | **MET_AGARTALA** | TRIPURA | `temperature` | `31.4` | **`36.94`** | `[34.35, 39.54]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-TRCIT000` | **CTI** | TRIPURA | `temperature` | `32.5` | **`32.29`** | `[28.05, 36.53]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRDHH000` | **DHOLAI_KVK** | TRIPURA | `temperature` | `33.2` | **`36.37`** | `[32.02, 40.72]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRGHJ000` | **Ghilatali** | TRIPURA | `temperature` | `35.4` | **`32.86`** | `[27.83, 37.89]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRHRC000` | **HRC_NAGICHERRA** | TRIPURA | `temperature` | `34.7` | **`32.29`** | `[28.46, 36.13]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRTEL000` | **TELIAMURA_BARRAGE** | TRIPURA | `temperature` | `33.0` | **`38.63`** | `[34.83, 42.44]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-TRTUS000` | **Tulashikhar** | TRIPURA | `temperature` | `36.3` | **`31.0`** | `[27.0, 34.99]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-UTBBR000` | **CHAUBATIA_RANIKHET** | UTTARAKHAND | `temperature` | `18.0` | **`22.57`** | `[14.29, 30.86]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-UTWAI000` | **TH_KOSIYAKUTOLI** | UTTARAKHAND | `temperature` | `30.3` | **`25.25`** | `[18.33, 32.17]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-WBDJL000` | **DARJEELING_MO** | WEST_BENGAL | `temperature` | `14.5` | **`21.27`** | `[15.89, 26.66]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-MPDAO000` | **MADIYAHAR_KVK** | MADHYA_PRADESH | `relative_humidity` | `55.0` | **`97.54`** | `[89.43, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55D80A94` | **LARNOO** | JAMMU_AND_KASHMIR | `relative_humidity` | `99.0` | **`40.79`** | `[32.46, 49.13]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-55D9E54E` | **CHILPI** | CHHATTISGARH | `relative_humidity` | `63.0` | **`97.08`** | `[78.74, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0A14FC6` | **PANCHKULA** | HARYANA | `relative_humidity` | `100.0` | **`69.38`** | `[53.46, 85.3]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-A0A9086A` | **JANJGIR** | CHHATTISGARH | `relative_humidity` | `37.0` | **`95.75`** | `[79.44, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-APETC000` | **SKY_COLLEGE_ETCHERLA** | ANDHRA_PRADESH | `relative_humidity` | `40.0` | **`88.23`** | `[80.28, 96.18]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-JHLOA000` | **LOHARDAGA_KVK** | JHARKHAND | `relative_humidity` | `11.0` | **`90.94`** | `[72.92, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-UPFAR000` | **FARRUKHABAD** | UTTAR_PRADESH | `relative_humidity` | `17.0` | **`92.72`** | `[66.73, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-UPINT000` | **INTEGRAL_UNIVERSITY** | UTTAR_PRADESH | `relative_humidity` | `33.0` | **`98.7`** | `[82.13, 100.0]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty RELATIVE_HUMIDI... |
| `INC-IMD-49530C4A` | **SECHU** | NAGALAND | `temperature` | `26.4` | **`24.2`** | `[19.58, 28.82]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-49534192` | **PASHAN_AWS_LAB** | MAHARASHTRA | `temperature` | `29.6` | **`31.64`** | `[29.6, 33.69]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-4953848C` | **MAHABALESHWAR** | MAHARASHTRA | `temperature` | `19.7` | **`27.91`** | `[25.74, 30.09]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-495397FA` | **DIMAPUR** | NAGALAND | `temperature` | `35.4` | **`30.01`** | `[25.2, 34.82]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55802C9C` | **RAM_MANDIR** | MAHARASHTRA | `temperature` | `31.5` | **`30.86`** | `[24.73, 37.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55C12DBA` | **RAJPURA_MANDI** | JAMMU_AND_KASHMIR | `temperature` | `24.5` | **`25.43`** | `[15.68, 35.17]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55C474D4` | **YINGKIONG** | ARUNACHAL_PRADESH | `temperature` | `36.2` | **`27.86`** | `[22.02, 33.71]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55CA8EEA` | **CHEMBARAMBAKKAM** | TAMIL_NADU | `temperature` | `33.9` | **`34.43`** | `[32.08, 36.79]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CA9D9C` | **HINDUSTAN_UNIVERSITY** | TAMIL_NADU | `temperature` | `34.5` | **`34.16`** | `[30.91, 37.4]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CAE5DE` | **LENGPUI** | MIZORAM | `temperature` | `26.7` | **`26.58`** | `[22.46, 30.7]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CB04D6` | **GOPAL_NAGAR** | KARNATAKA | `temperature` | `29.3` | **`26.46`** | `[24.39, 28.53]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CE5DB8` | **THENMALA** | KERALA | `temperature` | `25.2` | **`28.26`** | `[25.94, 30.59]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55CF3476` | **CHINCHWAD_PUNE** | MAHARASHTRA | `temperature` | `29.4` | **`28.28`** | `[25.55, 31.02]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55D00E32` | **SRINAGAR_ARG** | UTTARAKHAND | `temperature` | `34.6` | **`26.58`** | `[15.57, 37.59]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55D31A4A` | **TANGLA** | ASSAM | `temperature` | `30.2` | **`26.19`** | `[22.27, 30.11]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55D5BA7C` | **RAMSHAR** | HIMACHAL_PRADESH | `temperature` | `25.4` | **`23.77`** | `[16.17, 31.37]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55D66B1A` | **BALRAMPUR** | CHHATTISGARH | `temperature` | `25.1` | **`23.08`** | `[21.54, 24.62]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55D819E2` | **TRAL** | JAMMU_AND_KASHMIR | `temperature` | `29.6` | **`26.01`** | `[21.46, 30.56]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55E35F30` | **VIJAYARAI** | ANDHRA_PRADESH | `temperature` | `29.8` | **`32.01`** | `[28.64, 35.39]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55E403AA` | **DEVPRAYAG** | UTTARAKHAND | `temperature` | `31.3` | **`26.25`** | `[13.18, 39.31]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-55E6BB02` | **DIRANG** | ARUNACHAL_PRADESH | `temperature` | `27.2` | **`24.19`** | `[21.52, 26.87]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-55ED9E46` | **THARALI** | UTTARAKHAND | `temperature` | `6.6` | **`24.47`** | `[15.57, 33.37]` | `TIER_2_HUMAN_FIELD_VERIFICATION_REQUIRED` | 15% | Replace or recalibrate faulty TEMPERATURE sen... |
| `INC-IMD-55FBD4CE` | **TRIMBAKESHWAR** | MAHARASHTRA | `temperature` | `27.9` | **`26.54`** | `[23.38, 29.69]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-561268A2` | **SONEMARG** | JAMMU_AND_KASHMIR | `temperature` | `19.5` | **`25.94`** | `[21.19, 30.69]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-5B760076` | **CHAMOLI** | UTTARAKHAND | `temperature` | `31.2` | **`26.26`** | `[10.43, 42.09]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A13956` | **NUH** | HARYANA | `temperature` | `31.4` | **`32.27`** | `[25.2, 39.35]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A17A5C` | **SIRSA** | HARYANA | `temperature` | `32.1` | **`29.53`** | `[25.23, 33.83]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A1E1EC` | **BARPETA** | ASSAM | `temperature` | `29.2` | **`32.34`** | `[27.49, 37.19]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A1FC48` | **NALBARI** | ASSAM | `temperature` | `29.5` | **`32.15`** | `[27.31, 36.99]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A20BC2` | **MUSHALPUR** | ASSAM | `temperature` | `29.5` | **`31.83`** | `[26.57, 37.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A223FC` | **MARIGAON** | ASSAM | `temperature` | `27.0` | **`30.86`** | `[26.93, 34.79]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A28304` | **JOWAI** | MEGHALAYA | `temperature` | `29.6` | **`26.09`** | `[21.95, 30.23]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A2B84C` | **GOKULPUR** | TRIPURA | `temperature` | `30.6` | **`35.27`** | `[31.35, 39.18]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A307EA` | **JIRIBAM** | MANIPUR | `temperature` | `25.6` | **`30.84`** | `[24.78, 36.89]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0A32FD4` | **UDALGURI** | ASSAM | `temperature` | `30.2` | **`31.57`** | `[27.21, 35.94]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A34A32` | **ALONG** | ARUNACHAL_PRADESH | `temperature` | `30.3` | **`28.04`** | `[22.25, 33.82]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A35796` | **DEOMALI** | ARUNACHAL_PRADESH | `temperature` | `35.3` | **`31.42`** | `[27.04, 35.8]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A3B464` | **TALEGAON** | MAHARASHTRA | `temperature` | `28.1` | **`31.6`** | `[29.42, 33.78]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A53C6C` | **SURAT** | GUJARAT | `temperature` | `33.8` | **`31.57`** | `[30.63, 32.5]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0A665CC` | **COONOOR** | TAMIL_NADU | `temperature` | `20.2` | **`28.14`** | `[24.49, 31.78]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-A0AAE244` | **SHOPIAN** | JAMMU_AND_KASHMIR | `temperature` | `25.7` | **`25.68`** | `[21.23, 30.12]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0AD4E5A` | **NAMCHI** | SIKKIM | `temperature` | `18.3` | **`17.33`** | `[10.42, 24.24]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0AD53FE` | **MANKARA** | KERALA | `temperature` | `31.8` | **`28.67`** | `[26.59, 30.76]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B2741E` | **MASSOURI** | UTTARAKHAND | `temperature` | `19.7` | **`20.3`** | `[13.04, 27.57]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B2A276` | **MUNGESHPUR** | DELHI | `temperature` | `34.4` | **`30.72`** | `[25.04, 36.41]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B41FE4` | **MIRDHA** | UTTAR_PRADESH | `temperature` | `26.4` | **`24.87`** | `[22.35, 27.39]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B4BF1C` | **KAMALPUR** | TRIPURA | `temperature` | `36.6` | **`34.97`** | `[30.37, 39.58]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B4F2C4` | **RAMBAGH** | JAMMU_AND_KASHMIR | `temperature` | `28.1` | **`25.36`** | `[19.93, 30.8]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-A0B51D1E` | **RANCHI_AMFU** | JHARKHAND | `temperature` | `22.6` | **`25.61`** | `[24.61, 26.6]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-APGPA000` | **KV_GOPANNAPALEM_ELURU** | ANDHRA_PRADESH | `temperature` | `32.2` | **`29.73`** | `[27.72, 31.75]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ARDIG000` | **DIRANG** | ARUNACHAL_PRADESH | `temperature` | `23.8` | **`26.81`** | `[24.17, 29.44]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ARNYA000` | **NYAPIN** | ARUNACHAL_PRADESH | `temperature` | `26.4` | **`23.78`** | `[18.75, 28.81]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ARPNG000` | **PANGIN_CIRCLE** | ARUNACHAL_PRADESH | `temperature` | `29.6` | **`33.99`** | `[28.01, 39.96]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASAAU000` | **AAU_HRS** | ASSAM | `temperature` | `25.9` | **`24.42`** | `[20.45, 28.39]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASDHB000` | **DHARAMTUL** | ASSAM | `temperature` | `26.8` | **`25.24`** | `[20.85, 29.63]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASDTU000` | **DOWN_TOWN_UNIVERSITY** | ASSAM | `temperature` | `27.0` | **`28.68`** | `[24.54, 32.82]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASIIT000` | **IIT GUWAHATI** | ASSAM | `temperature` | `25.1` | **`23.98`** | `[19.86, 28.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASKME000` | **KAMPUR** | ASSAM | `temperature` | `28.9` | **`27.9`** | `[23.05, 32.75]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASKMK000` | **KAMAKHYA** | ASSAM | `temperature` | `26.0` | **`24.26`** | `[20.29, 28.22]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASNLB000` | **NALBARI_KVK** | ASSAM | `temperature` | `28.1` | **`30.83`** | `[24.55, 37.11]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASNTP000` | **NTPS_APDCL** | ASSAM | `temperature` | `36.9` | **`36.33`** | `[30.62, 42.04]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASROW000` | **ROWTA_AEGCL** | ASSAM | `temperature` | `31.1` | **`32.16`** | `[27.96, 36.35]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASSOF000` | **SONARI_AEGCL** | ASSAM | `temperature` | `32.6` | **`35.15`** | `[29.78, 40.53]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-ASUDI000` | **UDI_KVK** | ASSAM | `temperature` | `30.7` | **`27.69`** | `[24.01, 31.37]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-B48970CA` | **LODI ROAD** | DELHI | `temperature` | `32.2` | **`30.32`** | `[28.45, 32.19]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-B48A3A1C` | **RANCHI** | JHARKHAND | `temperature` | `23.7` | **`22.25`** | `[19.35, 25.15]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-B4966C62` | **RAJGURUNAGAR** | MAHARASHTRA | `temperature` | `25.9` | **`28.71`** | `[25.84, 31.58]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-GUATH000` | **SURAT_KVK** | GUJARAT | `temperature` | `31.7` | **`33.28`** | `[31.28, 35.28]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-HPBIE000` | **BILASPUR_KVK** | HIMACHAL_PRADESH | `temperature` | `28.1` | **`22.41`** | `[15.49, 29.33]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-JHBIU000` | **GUMLA-BISHNUPUR_KVK** | JHARKHAND | `temperature` | `25.4` | **`22.95`** | `[21.77, 24.13]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-JHNTT000` | **NETARHAT** | JHARKHAND | `temperature` | `20.5` | **`22.92`** | `[21.68, 24.15]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-JKJMU000` | **JAMMU** | JAMMU_AND_KASHMIR | `temperature` | `29.1` | **`34.31`** | `[26.64, 41.98]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-JKPNC000` | **POONCH** | JAMMU_AND_KASHMIR | `temperature` | `29.1` | **`24.15`** | `[16.55, 31.75]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-JKREA000` | **REASI_KVK** | JAMMU_AND_KASHMIR | `temperature` | `31.6` | **`23.36`** | `[17.8, 28.93]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-KEAYP000` | **AYYAPPANKOVIL** | KERALA | `temperature` | `26.2` | **`27.13`** | `[22.27, 31.99]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEKBY000` | **KABANIGIRI** | KERALA | `temperature` | `25.5` | **`23.39`** | `[20.06, 26.71]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEKRH000` | **KARAPUZHA** | KERALA | `temperature` | `22.3` | **`22.61`** | `[18.84, 26.38]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEMLF000` | **MALAMPUZHA DAM** | KERALA | `temperature` | `28.8` | **`29.6`** | `[25.46, 33.74]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEPAF000` | **PALODE** | KERALA | `temperature` | `30.3` | **`27.24`** | `[24.25, 30.22]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEPEP000` | **PEPPARA** | KERALA | `temperature` | `29.2` | **`27.42`** | `[23.73, 31.1]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEPOT000` | **POTHUNDY DAM** | KERALA | `temperature` | `27.7` | **`29.33`** | `[26.02, 32.64]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KETRQ000` | **THIRUVALLA_KALLUNKAL** | KERALA | `temperature` | `32.6` | **`29.38`** | `[27.54, 31.22]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEUDO000` | **UDUMBANNOOR** | KERALA | `temperature` | `30.9` | **`28.07`** | `[24.24, 31.9]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEULA000` | **ULANADU** | KERALA | `temperature` | `27.5` | **`28.54`** | `[26.06, 31.02]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-KEVAT000` | **VATTAVADA** | KERALA | `temperature` | `24.3` | **`23.56`** | `[16.19, 30.92]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MADUO000` | **RJSPMCOP_DUDULGAON** | MAHARASHTRA | `temperature` | `29.8` | **`28.35`** | `[25.75, 30.94]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MAKHB000` | **KHADAKWADI_AMBEGAON** | MAHARASHTRA | `temperature` | `30.4` | **`27.26`** | `[24.25, 30.27]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MANIG000` | **NIMGIRI_JUNNAR** | MAHARASHTRA | `temperature` | `25.6` | **`29.76`** | `[26.62, 32.9]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MANRA000` | **NARAYANGOAN_KRISHI_KENDRA** | MAHARASHTRA | `temperature` | `28.0` | **`26.75`** | `[22.33, 31.17]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MAPAB000` | **PABAL_SHIRUR** | MAHARASHTRA | `temperature` | `26.4` | **`29.06`** | `[26.2, 31.92]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MAVIO000` | **VILHOLI** | MAHARASHTRA | `temperature` | `29.0` | **`31.18`** | `[28.94, 33.41]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MEKHZ000` | **KHATARSHNONG_LAITKROH** | MEGHALAYA | `temperature` | `21.6` | **`25.31`** | `[22.41, 28.22]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MIKOB000` | **KOLASIB** | MIZORAM | `temperature` | `24.3` | **`31.41`** | `[27.24, 35.57]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-MIMIU000` | **MIZORAM_UNIVERSITY** | MIZORAM | `temperature` | `29.9` | **`26.44`** | `[22.45, 30.43]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MIMMZ000` | **LENGPUI_KVK** | MIZORAM | `temperature` | `25.3` | **`27.49`** | `[24.04, 30.95]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MRCAK000` | **CHAKPIKARONG** | MANIPUR | `temperature` | `28.2` | **`30.66`** | `[28.04, 33.28]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-MRCNL000` | **CHANDEL_KVK** | MANIPUR | `temperature` | `28.2` | **`25.47`** | `[23.06, 27.87]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-NANEQ000` | **CHIEPHOBOZOU_NERHEMA** | NAGALAND | `temperature` | `24.2` | **`27.8`** | `[23.87, 31.73]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-PJPTN000` | **KVK_PATHANKOT** | PUNJAB | `temperature` | `30.9` | **`30.34`** | `[24.3, 36.37]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-PJTEI000` | **THEIN_DAM** | PUNJAB | `temperature` | `27.2` | **`32.21`** | `[27.13, 37.3]` | `TIER_1_SAFE_AUTO_REPAIR` | 48% | Safe causal spatial imputation recommended. S... |
| `INC-IMD-PUPUU000` | **PUDUCHERRY_KVK** | PUDUCHERRY | `temperature` | `33.9` | **`34.1`** | `[29.6, 38.6]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-SISOE000` | **SORENG** | SIKKIM | `temperature` | `15.6` | **`16.52`** | `[11.95, 21.08]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TNPAQ000` | **NIOT_PALLIKARANAI** | TAMIL_NADU | `temperature` | `32.6` | **`34.53`** | `[32.5, 36.56]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRAAS000` | **Ambassa** | TRIPURA | `temperature` | `34.2` | **`31.21`** | `[26.88, 35.55]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRASA000` | **ASHAPARA** | TRIPURA | `temperature` | `32.0` | **`34.15`** | `[30.76, 37.54]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRBGF000` | **BAGAFA** | TRIPURA | `temperature` | `30.8` | **`34.27`** | `[30.86, 37.68]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRDMO000` | **DM_OFFICE_WEST_AGARTALA** | TRIPURA | `temperature` | `31.0` | **`32.75`** | `[28.37, 37.13]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRHEZ000` | **Hezamara** | TRIPURA | `temperature` | `33.5` | **`32.58`** | `[27.81, 37.35]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRKBR000` | **Karbook** | TRIPURA | `temperature` | `30.8` | **`29.66`** | `[25.26, 34.06]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRKNQ000` | **Kanchanpur** | TRIPURA | `temperature` | `31.6` | **`29.68`** | `[25.86, 33.5]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRRGD000` | **Rajnagar** | TRIPURA | `temperature` | `29.6` | **`30.35`** | `[26.24, 34.47]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-TRSEH000` | **SIPAHIJALA** | TRIPURA | `temperature` | `33.4` | **`35.28`** | `[30.51, 40.05]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-UPBAL000` | **BALLIA_AWS400** | UTTAR_PRADESH | `temperature` | `24.5` | **`26.63`** | `[24.63, 28.62]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-UPMTU000` | **MATHURA_AWS400** | UTTAR_PRADESH | `temperature` | `27.3` | **`30.5`** | `[29.0, 32.0]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-UTALA000` | **MATELA_KVK** | UTTARAKHAND | `temperature` | `22.5` | **`20.46`** | `[11.47, 29.45]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |
| `INC-IMD-UTNAF000` | **NAINITAL(JEOLIKOT)_KVK** | UTTARAKHAND | `temperature` | `20.6` | **`21.39`** | `[13.61, 29.18]` | `TIER_1_SAFE_AUTO_REPAIR` | 78% | Sensor operating within acceptable variance l... |

## 3. Scientific Methodology & Compliance Guardrails
- **Lapse-Rate Compensated IDW:** All spatial consensus estimations account for vertical lapse rate (6.5°C/km for temperature, 12 hPa/100m for barometric pressure).
- **Adaptive 90% Uncertainty Intervals:** Normal quantile bounds ($1.645\sigma$) computed dynamically from regional peer dispersion.
- **Data Integrity Rule:** The raw reported observation is NEVER modified in-place or deleted; corrections are offered as calibrated imputation streams with cryptographic audit provenance.
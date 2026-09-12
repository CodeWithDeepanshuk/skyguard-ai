# Iteration 12 — Genuine IMD AWS Data Guide

## Seedha decision

SIH 26073 ke liye sabse relevant data **authorized IMD AWS Data API** hai, kyunki isme Indian AWS stations se directly reported temperature, relative humidity aur MSLP pressure milta hai. Iteration 12 isi source ko gold data lane banata hai. NOAA data useful official historical pretraining source hai, lekin use IMD AWS bolna galat hoga. DWD sirf cross-climate robustness ke liye secondary hai.

## Iteration 11 mein actual problem kya thi

Iteration 11 discovery ne 545 Indian NOAA IDs aur 441 available candidates find kiye the, lekin returned run ne 24 Indian stations hi use kiye. Corrected pilot mein sirf 6 stations download/process hue aur 5 eligible nikle. Isliye 543-map entries ko 543-station training evidence nahi maana ja sakta.

## Iteration 12 kya karta hai

1. IMD portal ke approved `x-api-key` aur JWT ko Colab Secrets se memory mein load karta hai.
2. Official `aws_data_mapping` aur national `aws_data` endpoints ko call karta hai.
3. Har API response ko unchanged JSON, retrieval time aur SHA-256 checksum ke saath Drive par archive karta hai.
4. Sirf temperature, MSLP pressure aur direct RH ko model-input contract mein normalize karta hai.
5. Station ID, name, state, district aur coordinates provenance/context ke liye rakhta hai.
6. Invalid/missing values ko overwrite ya generated values se fill nahi karta.
7. Duplicate station-time rows remove karke deterministic Parquet table banata hai.
8. 30-day, 90-day aur 365-day station coverage separately measure karta hai.
9. Data insufficient ho to training ko fail-closed rakhta hai; old deployed model replace nahi hota.

## Bahut important limitation

Documented IMD endpoint current snapshot deta hai; ek Colab run historical years create nahi kar sakta. Isliye genuine data collection aaj se accumulate hoga. Ek snapshot par temporal anomaly model train karna galat hoga.

Recommended minimum:

| Stage | Minimum evidence | Kya allowed hai |
|---|---|---|
| Connectivity check | 1 valid snapshot | Schema aur station coverage verify |
| Pilot model | kam-se-kam 50 stations ke 30 distinct days | Limited causal temporal experiment |
| Strong temporal model | 50+ stations ke 90 days | Better drift/freeze/season transition test |
| Seasonal claim | 50+ stations ke 365 days | Annual seasonal patterns evaluate |

Yeh engineering readiness thresholds hain, SIH ke official prescribed numbers nahi.

## Google Colab par kya karein

1. [SkyGuard_AI_Iteration_12_Genuine_IMD_AWS_Data_Colab.ipynb](../notebooks/SkyGuard_AI_Iteration_12_Genuine_IMD_AWS_Data_Colab.ipynb) upload karein.
2. Colab Secrets mein `IMD_API_KEY` aur `IMD_JWT_TOKEN` add karein.
3. Pehle `COLLECT_HOURS=0` ke saath one-snapshot smoke test run karein.
4. IMD approval/documentation se AWS `DATE + TIME` ka timezone confirm karein. Uske baad hi matching `SOURCE_TIMEZONE` set karke `TIMESTAMP_TIMEZONE_CONFIRMED=True` karein. Public field table timezone ko explicitly define nahi karti, isliye default gate fail-closed hai.
5. Result sahi ho to `COLLECT_HOURS=6`, `INTERVAL_MINUTES=15` karke bounded collection run karein, ya notebook ko scheduled collector service mein convert karein.
6. Drive ke `SkyGuard_AI_GPU/experiments/iteration12_genuine_imd_aws_v1` folder ko delete/rename na karein; future runs wahi history append karenge.
7. Last cell se `SkyGuard_Iteration12_Genuine_IMD_AWS_Reports.zip` download karke review ke liye dein.

GPU data download mein benefit nahi deta; CPU runtime enough hai. Future model training ke liye T4 useful ho sakta hai.

## Accuracy ke bare mein honest rule

Official observation automatically “healthy sensor” label nahi hota. IMD API fault labels provide nahi karta. Real detection accuracy validate karne ke liye controlled injected faults, station/time holdouts aur ideally IMD maintenance logs/adjudicated fault episodes chahiye. Primary metrics fault incident precision, fault episode recall, false incidents per station-day, genuine-weather preservation, unseen-station F1 aur latency honge—sirf overall accuracy nahi.

## Official references

- [IMD AWS API reference](https://api.imd.gov.in/public/api_reference.html)
- [IMD API management portal](https://api.imd.gov.in/public/index.php)
- [NOAA GHCNh official product](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly)

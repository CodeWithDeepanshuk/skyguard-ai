# SkyGuard AI Iteration 10 — Colab execution guide

## Is step mein kya complete hua

Iteration 10 ek fresh, standalone final-development candidate hai. Yeh Iteration 9 ko blindly extend nahi karta. Ismein ye structural fixes hain:

- corrected official NOAA/NCEI India parser aur verified 2022–2023 corpus;
- official DWD 2022–2023 multi-climate transfer corpus;
- total 40 stations: India 24 aur DWD 16;
- India ke mixed 30/60/180-minute cadence ke liye cadence-adaptive curriculum;
- 6 coherent regional-weather families;
- 13 operational sensor/communication fault families;
- sirf temperature, pressure aur relative humidity observation inputs;
- 76 strict causal ML features;
- absolute aur cross-station pressure-datum shortcuts removed;
- LightGBM + GPU CatBoost row evidence;
- causal rolling incident-state LightGBM ensemble;
- mutually exclusive normal / genuine-weather / sensor-fault decision;
- independent neighbour-weather gate;
- k-of-n persistence, hysteresis aur instant deterministic path;
- slope/CUSUM-based drift evidence;
- L2 calibrated confidence;
- hierarchical root-cause classification;
- incident-level precision, recall, F1, false alerts/station-day aur latency;
- advisory correction MAE, interval coverage aur end-to-end correction coverage;
- health score aur maintenance action;
- LightGBM importance aur SHAP export;
- three fresh injection seeds;
- station/time/season-safe split;
- 2024 aur 2025 data completely locked.

## Aapko kaunse files use karne hain

Google Drive ke `/MyDrive/SkyGuard_AI_GPU/` folder mein sirf ye do ZIP upload karein:

1. `SkyGuard_Iteration10_Final_Starter_Bundle.zip`
2. `SkyGuard_Iteration8_Development_Data_Bundle.zip`

Phir Colab mein ye notebook open karein:

`SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb`

## Exact run process

1. Colab runtime ko T4 GPU par set karein.
2. Notebook mein `UNLOCK_FINAL_TESTS=False` hi rehne dein.
3. `REUSE_FEATURE_CACHE=True` rehne dein. Agar aapne pehle Iteration 10 run kiya hai, toh feature tables aapke Google Drive folder (`/MyDrive/SkyGuard_AI_GPU/`) mein pehle se cached hain — **is wajah se yeh run sirf 10-15 minutes lega!**
4. `RUN_STRESS_SEEDS=True` rehne dein.
5. Runtime menu se **Run all** karein.
6. Iteration 10-R refinement ke tahat policy grid search 0.50–0.85 operational range mein search karegi aur safe high-precision floor use karegi, jisse purana over-alerting defect fix ho jayega.
7. Disconnect hone par bhi cached tables/models reuse honge.

## Run ke baad kya bhejna hai

Sabse important:

- `iteration10_result_block.json`
- `iteration10_multidomain_confirmation.csv`
- `iteration10_fault_episode_recall.csv`
- `iteration10_multiseed_stress.csv`
- `iteration10_root_cause_metrics.csv`
- `iteration10_root_cause_per_class.csv`
- `iteration10_calibration_metrics.json`
- `iteration10_correction_metrics.csv`
- `iteration10_weather_by_cluster.csv`
- `iteration10_detection_latency.csv`
- `iteration10_season_metrics.csv`
- `iteration10_sensor_health.csv`
- `iteration10_policy_frontier.csv`
- `iteration10_feature_contract.json`
- `iteration10_integrity_receipt.json`
- `iteration10_runtime_metrics.json`
- `SkyGuard_Iteration10_Result_Package.zip`

## Result ko kaise interpret karna hai

Notebook ke last result mein har gate ka exact PASS/FAIL aayega. Main target ye hai:

| Metric | Promotion target |
|---|---:|
| Incident fault precision | >= 0.80 |
| Incident fault F1 | >= 0.70 |
| False alerts / station-day | <= 0.02 |
| Fault episode recall | >= 0.70 |
| Drift episode recall | >= 0.50 |
| Frozen episode recall | >= 0.80 |
| Communication mean recall | >= 0.80 |
| Weather incident F1 | >= 0.70 |
| Fault ko weather bolne ki rate | <= 0.01 |
| Root-cause accuracy | >= 0.80 |
| Root-cause macro F1 | >= 0.70 |
| Fault/weather ECE | <= 0.08 |
| Fresh-seed consistency | 3/3 runs |

Accuracy akeli sufficient metric nahi hai, kyunki normal rows bahut zyada hain. Incident precision/F1, false-alert budget, per-family episode recall, root cause aur weather separation main decision metrics hain.

## Important honesty rule

Iteration 10 ka architecture aur executable notebook complete hai, lekin uski final empirical accuracy tabhi valid hogi jab T4 run ka output mil jaye. Is notebook ko run kiye bina naya score claim nahi karna hai. Existing accepted deployment Iteration 5 hi rahega aur Iteration 10 `shadow_evidence_only_unvalidated` mode mein rahega. Is mode mein model/drift evidence visible hai, lekin deterministic QC ya transport proof ke bina live incident confirm nahi hota. Saare gates pass hone par bhi next step sirf ek separately authorised locked confirmation hoga—automatic deployment nahi.

# SkyGuard 2025 Blind Result — Roman Hindi Review

## Seedha nishkarsh

Blind run technically sahi aur trustworthy tha. Model hashes, 108-feature contract, fixed policy, development confusion matrices aur no-tuning receipt sab pass hue. Lekin Iteration 5 strict promotion gate pass nahi kar saka.

Iteration 5 ne known-station future-time test par chhota lekin real improvement diya. Unseen stations par usne ek bhi additional fault detect nahi kiya. Isliye use final production model banana abhi safe nahi hai.

## Main comparison

| Test | Precision | Recall | Point F1 | Event F1 | Operational episode recall |
|---|---:|---:|---:|---:|---:|
| Future time Iteration 3 | 87.48% | 29.69% | 44.33% | 64.99% | 81.54% |
| Future time Iteration 5 | 87.80% | 31.16% | 46.00% | 65.33% | 82.05% |
| Unseen station Iteration 3 | 90.15% | 35.52% | 50.96% | 72.73% | 76.92% |
| Unseen station Iteration 5 | 90.15% | 35.52% | 50.96% | 72.73% | 76.92% |

## Hamari sabse strong cheezein

1. Point precision 87.8% aur 90.15% hai. Alert aane par fault hone ka chance kaafi strong hai.
2. Duplicate packet detection dono tests me 100% precision aur 100% recall hai.
3. Communication corruption aur unit error episode detection 100% hai.
4. Severe scaling, spikes aur multi-sensor failures generally strong hain.
5. Detector sirf temperature, pressure aur relative humidity se nikle causal features use karta hai.
6. Blind benchmark ek baar fixed policy ke saath khola gaya; score ko dekh kar threshold change nahi hua.
7. Accuracy 98.5% jaisi dikhti hai, lekin class imbalance ke kaaran ise headline metric nahi banana chahiye. F1, episode recall aur false-alert rate zyada meaningful hain.

## Problem kahan hai aur kyon hai

### 1. Recall kam hai

Model conservative hai. High precision bachane ke liye threshold strong rakha gaya hai, isliye subtle faulty rows miss ho rahe hain. Future-time recall 31.16% aur unseen-station recall 35.52% hai.

Bias, drift aur frozen faults dheere badalte hain. Ek individual row normal weather variation jaisa lag sakta hai. Jab tak enough temporal ya neighbour disagreement accumulate hota hai, episode ka bada hissa miss ho chuka hota hai.

### 2. Unseen-station transfer kamzor hai

Iteration 5 known stations par 35 extra faulty rows recover karta hai, lekin unseen stations par zero. Iska matlab model ke kuch patterns station-specific distribution, reporting cadence, elevation ya local climate se jude hue hain.

Absolute values aur station climatology ka behaviour naye station par shift hota hai. Isi liye Iteration 6 raw station-identifying features ko hata kar relative residual, slope, CUSUM aur neighbour-agreement features par focus karega.

### 3. Genuine weather model transfer nahi kar raha

Weather F1 future time me 53.02% aur unseen stations me 13.64% hai. Unseen-station weather recall sirf 9.09% hai.

Training weather examples limited aur mostly regional temperature events hain. Pressure fronts, humidity transitions aur multi-parameter events ka coverage kam hai. Purana weather model absolute/local distributions ko zyada learn kar sakta hai aur neighbour coherence ko kam generalize karta hai.

### 4. Dropout rule ka false alarm bahut zyada hai

Duplicate detector perfect hai, lekin dropout precision future time me 0.46% aur unseen stations me 5.36% hai.

NOAA archive fixed-heartbeat AWS stream nahi hai. Reports naturally irregular ho sakti hain, kuch stations 30 minute aur kuch 180 minute cadence par report karte hain, aur historical archive me natural missing intervals hote hain. Sirf long gap dekh kar injected dropout aur natural archival gap ko reliably alag nahi kiya ja sakta.

Safe solution: expected cadence/heartbeat contract milne par automatic dropout incident; unknown cadence par sirf `unverified data gap` advisory, sensor-fault maintenance alert nahi.

## Target gap

| Parameter | Future-time score | Unseen-station score | Target | Improvement ki zarurat |
|---|---:|---:|---:|---|
| Precision | 87.80% | 90.15% | 80% | Already pass |
| Point F1 | 46.00% | 50.96% | 65% | +19.00 aur +14.04 points |
| Episode recall | 82.05% | 76.92% | 85% | +2.95 aur +8.08 points |
| Weather F1 | 53.02% | 13.64% | 80% | +26.98 aur +66.36 points |
| Weather-to-fault | 0% | 3.03% | maximum 1% | Time pass; unseen ko 2.03 points reduce karna hai |
| Automatic dropout precision | 0.46% | 5.36% | practical target at least 80% | Contract-aware redesign required |

## Iteration 6 me kya hoga

1. 2025 benchmark ko dobara nahi khola jayega.
2. 2022 training aur 2023 development blocks hi use honge.
3. Har regional cluster ka ek station pseudo-unseen confirmation ke liye training se bahar rahega.
4. Communication policy arrival-gap identifiability audit karegi.
5. Unknown-cadence archive gaps automatic sensor fault nahi banenge.
6. Station-invariant weather CatBoost aur LightGBM experts train honge.
7. Station-balanced weak-fault CatBoost aur LightGBM experts train honge.
8. May–September policy discovery ke baad October aur pseudo-unseen confirmation mandatory hogi.
9. Precision, false alerts, point F1 ya event F1 regress hua to candidate reject hoga.

## Model recommendation

Abhi TabPFN, SAINT ya bada Transformer first priority nahi hai. Main failure data representation, station transfer, weather diversity aur communication contract ka hai. Bada neural network in problems ko automatically solve nahi karega aur overfitting risk badha sakta hai.

Pehle station-invariant CatBoost/LightGBM consensus aur correct operational policy ko test karna zyada scientific aur SIH-friendly hai. Neural model tab add karna chahiye jab woh pseudo-unseen confirmation par measurable additional gain de.

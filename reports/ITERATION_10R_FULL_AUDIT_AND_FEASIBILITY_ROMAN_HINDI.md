# SkyGuard AI SIH26073 — Iteration 10R Full Audit aur Realistic Feasibility

## Seedha verdict

Project ka core approach SIH26073 ko solve karta hai: causal real-time detection,
temperature/pressure/humidity temporal learning, neighbour comparison, genuine
weather versus sensor-fault separation, confidence, explanations, root cause,
communication faults, sensor health aur advisory correction sab architecture mein
present hain.

Lekin returned Iteration 10 model deployable nahi hai. Uska fault incident precision
sirf **2.99%**, F1 **5.79%**, aur false alerts **0.2196 per station-day** tha. Ye India
data ki inherent limit nahi thi. Sabse bade causes ek stale-cache station-ID defect,
natural prevalence ko distort karne wala balanced calibrator, aur over-permissive
drift rescue the. Isliye Iteration 10 ko final result samajhna galat hoga.

Iteration 10R notebook in defects ko directly repair karta hai. Notebook ka static
aur synthetic regression audit **20/20 PASS** hai; actual accuracy/F1 sirf T4 Colab
par full run ke baad honestly report ki ja sakti hai.

## Ab tak project mein kya hua

| Stage | Main kaam | Evidence-based decision |
|---|---|---|
| Data foundation | Official corrected India/NCEI observations, station metadata, DWD multi-climate observations, checksums aur validation reports | Real data valid hai; true sensor-fault labels available nahi hain, isliye injected faults evaluation ke liye use hote hain |
| Iteration 1 | CatBoost/LightGBM/TCN baselines, calibrated hybrid, episode metrics | Precision 85.15%, point F1 51.11%, event F1 64.44%; frozen sensor recall zero tha |
| Iteration 2 | Weak-fault rescue, block-wise threshold selection | Oct–Dec point F1 55.11%, event F1 59.79%; drift/frozen ab bhi weak |
| Iterations 3–4 | Duplicate/communication replay aur causal incident state | Duplicate packet precision/recall 100%; unsafe candidate gains reject kiye gaye |
| Iteration 5 | Episode-balanced weak-fault consensus | Safe retained India reference: Oct–Dec precision 83.26%, point F1 55.11%, event F1 59.79%, false alerts 0.0174/station-day |
| Blind 2025 audit | Fresh time and unseen-station test | Blind-time precision 87.80%, event F1 65.33%; blind-station precision 90.15%, event F1 72.73%. Weather transfer aur dropout precision weak rahe |
| Iterations 6–7 | Heartbeat safety contract, climate calibration, causal TCN | TCN/model additions ne confirmation improvement prove nahi ki; safe baseline retain hua |
| Iteration 8 | DWD multi-climate curriculum, CatBoost + LightGBM + LSTM autoencoder + Isolation Forest audit | India event F1 65.26%; DWD weather F1 90.84%; candidate full promotion fail hua |
| Iteration 9 | Domain-invariant residual models, L2 calibration, multi-seed stress, root cause | DWD precision 91.18%, event F1 40.00%; DWD holdout precision 98%, event F1 61.54%. India event F1 62.79%; overall promotion fail |
| Iteration 10 | Unified 3-state incident intelligence | Architecture broad thi, par implementation defects ke kaaran catastrophic false positives aaye; 9/21 gates pass |
| Iteration 10R | Cache/integrity, natural-prior calibration, safe drift/weather state, cadence adaptation, conformal correction | Code/synthetic audit 20/20 PASS; full GPU result ab run hona baaki hai |

## Returned Iteration 10 ka exact result

| Metric | Iteration 10 | Meaning |
|---|---:|---|
| Point accuracy | 3.14% | Invalid operational behaviour; 98.93% normal rows fault ban gaye |
| Fault point F1 | 1.11% | Catastrophic |
| Fault AUPRC | 19.01% | Ranking signal ab bhi hai; prevalence lagbhag 0.59% se kaafi better |
| Fault incident precision | 2.99% | Har 100 fault alerts mein lagbhag 97 false |
| Fault incident recall | 89.39% | Blanket alerts ki wajah se artificially high |
| Fault incident F1 | 5.79% | Deployable nahi |
| False alerts/station-day | 0.2196 | Target 0.02 se lagbhag 11 guna zyada |
| Weather point AUPRC | 91.89% | Weather ranking strong hai |
| Weather incident F1 | 61.20% | Moderate, lekin weather-to-fault overlap 89.86% tha |
| Fault ECE | 34.60% | Confidence badly miscalibrated |
| Root-cause accuracy | 10.17% | False incident population ne downstream diagnosis ko corrupt kiya |
| Throughput | 28,153 rows/sec | Excellent scalability evidence |

Confusion matrix mein 195,655 true-normal confirmation rows the; unmein se 193,570
fault declare hue. Isliye high recall ko achievement nahi maana ja sakta.

## Iteration 10 kyun fail hua

1. **Balanced probability calibrator:** natural class prevalence preserve nahi hui.
   187,423 rows ko average fault confidence lagbhag 35.67% mili, jab us bin ki actual
   fault rate sirf 0.289% thi.
2. **Stale cache station-ID bug:** cached India `station_id` integer load hua, jabki
   holdout list strings thi. Holdout comparison silently fail hua. Isi liye India
   holdout output mein zero rows aaye aur claimed split receipt reliable nahi tha.
3. **Over-permissive drift rescue:** 15 slope/CUSUM values mein se kisi ek ka maximum
   threshold cross karna enough tha. Miscalibrated fault probability 0.08 se upar
   hone par normal weather bhi drift fault ban gaya.
4. **Failed policy ko freeze kiya gaya:** policy frontier mein eligible candidates
   zero the, phir bhi fallback policy final policy ke roop mein save hui.
5. **Weather/fault state contamination:** ek combined candidate-run feature aur
   direct class switching ne same event ko weather aur fault dono incidents mein
   tod diya.
6. **Downstream cascade:** wrong detection ke baad root cause, corrections aur
   sensor-health scores meaningful nahi reh sakte. Isi wajah se 80 mein se 71
   sensors critical dikhe.

## India aur DWD data ka measured comparison

Ye comparison sirf 2022–2023 development observations par kiya gaya hai.

| Data property | India | DWD | Modelling impact |
|---|---:|---:|---|
| Stations | 24 | 16 | India mein count zyada, par station histories uneven |
| Model rows | 385,656 | 279,400 hourly | Dono usable |
| Main-variable completeness | 99.93% | 100% | Dono strong |
| Cadence | 11 stations: 30 min; 13: 180 min | sab 16: 60 min | India persistence/latency heterogeneous |
| Median regular cadence | 97.22% | 99.99% | DWD temporal baselines cleaner |
| Minimum regular cadence | 59.83% | 99.86% | Kuch India stations bahut irregular |
| Median full-year slot coverage | 97.55% | 99.95% | DWD nearly complete |
| Minimum slot coverage | 11.50% | 98.31% | India ka weakest station season/generalization ko hurt karta hai |
| Same-time 2+ neighbours | 72.98% | 100% | India ke 27.02% rows par strong spatial vote available nahi |
| Rows/station CV | 0.8031 | 0.00337 | India data volume extremely uneven; DWD balanced |
| Median gap q99.9 | 4× cadence | 1× cadence | India archive mein long gaps common |
| Maximum gap q99.9 | 48× | 5× | India dropout versus archive silence ambiguity high |
| Pressure source | 71.34% altimeter, 27.17% SLP, 1.47% station | 100% one reduced-to-MSL source | India pressure datum/source shift residual learning ko complicate karta hai |

### DWD se result generally stable kyun hota hai

- Har station same hourly rhythm par hai, isliye rolling window ka physical meaning
  consistent hai.
- Lagbhag har expected slot present hai; gap ko communication problem samajhna easy
  hai.
- Har row ke same-time neighbours available hain; regional weather aur single-sensor
  fault ko separate karna easier hai.
- Station-wise sample sizes almost equal hain, isliye model kisi high-volume station
  se dominate nahi hota.
- Pressure preprocessing uniform hai, isliye cross-station/domain residual shift kam
  hota hai.

### Important correction

Rich DWD data ka matlab har fault metric automatically high nahi hota. Best retained
confirmation mein India event F1 **65.26%** tha, DWD-all event F1 **40.00%**, aur DWD
holdout event F1 **61.54%** tha. DWD weather separation (lagbhag 94% F1 in Iteration
9) bahut strong thi, lekin subtle injected fault recall lower raha. Data quality aur
fault-injection difficulty dono alag factors hain.

## India data par realistic maximum kya hai

“Accuracy” akela misleading hai, kyunki 99% rows normal predict karke bhi bahut high
accuracy mil sakti hai. SIH ke liye incident precision, incident recall/F1, false
alerts, class-wise recall, ECE aur unseen station/time performance primary honi
chahiye.

| Metric | Already proved best | Current India archive par realistic 10R band | Rich real India AWS + true fault labels milne par |
|---|---:|---:|---:|
| Fault incident precision | 83–90% range in retained/blind runs | 75–90% | 85–95% |
| Fault incident recall | up to 80.6% in selected development blocks | 60–80% | 75–90% |
| Fault incident F1 | 65.26% India confirmation; 72.73% blind station | 65–78% | 78–90% |
| Fault point F1 | 55.11% India confirmation | 50–63% | 65–82% |
| False alerts/station-day | 0.0125–0.0187 in strong retained runs | <=0.02 achievable | <=0.01 realistic |
| India weather incident F1 | unstable: 34–78% by split | 50–72% | 75–90% with dense neighbours |
| Communication recall | duplicate 100%; safe mean 87.5% in Iteration 10 | 80–95% only with verified heartbeat | 90–99% |
| Weak drift/frozen episode recall | roughly 33–56% in reliable retained runs | 45–70% | 65–85% with labelled degradation histories |
| 13-class root macro F1 | India detected-row 62.0% in Iteration 9 | 45–65% | 65–80% |
| Broad root-family accuracy | evidence depends on detector quality | 70–85% | 80–92% |
| Fault confidence ECE | Iteration 10: 34.6% (broken) | <=8% target, <=5% strong | <=5% |

Ye ranges guarantees nahi hain. Ye existing blind/confirmation evidence, measured
data limitations aur injected-fault setup par based engineering estimates hain.
Unknown SIH hidden injection distribution par result lower ya higher ho sakta hai.

## Iteration 10R mein exact improvements

1. Naya cache namespace old defective cache ko read nahi karta.
2. Cache load par station, row aur evaluation IDs explicitly strings bante hain.
3. India/DWD holdout rows non-zero hona mandatory assertion hai; holdouts training
   mein zero hone chahiye.
4. January model early-stop aur February calibration alag kiye gaye hain.
5. L2 calibrator se `class_weight=balanced` remove hua; calibrated means natural
   observed prior se match karaye jaate hain.
6. Calibration safety audit normal fault p99, ECE aur prior error check karta hai.
7. Drift score ab single maximum nahi; second-largest evidence aur kam-se-kam teen
   supporting windows/features maangta hai.
8. Drift rescue ko neighbour-isolation aur no-weather-gate condition chahiye.
9. Fault aur weather run lengths separate hain.
10. Coherent neighbour weather fault vote ko veto karta hai.
11. 180-minute India station par sirf very-high-confidence row ko immediate path
    milta hai; lower confidence ko persistence chahiye.
12. Policy search aggregate score ke badle worst India/DWD safety constraints use
    karta hai.
13. Eligible policy zero ho to `frozen_policy=null`; diagnostic policy deploy nahi
    ho sakti.
14. Sensor-health automatic maintenance action detection gates pass hone tak blocked
    hai.
15. Correction uncertainty sensor-wise development conformal residuals se target
    90% marginal coverage leti hai.
16. 2024/2025 direct observation read path absent hai; stress tests fresh 2023
    injection seeds use karte hain.

## Model stack aur deep models par decision

- Row evidence: 3-seed LightGBM + GPU CatBoost ensemble.
- Incident state: 3-seed LightGBM on causal rolling state features.
- Calibration: natural-prior L2 logistic layer plus prior matching.
- Root cause: hierarchical CatBoost broad-family and 13-class classifiers.
- Deterministic safety: physical limits, duplicate/timestamp detection, verified
  heartbeat gaps, multi-sensor freeze.
- Signal methods: rolling median/MAD, robust z-score, EWMA residual, multi-window
  slope, CUSUM, seasonal climatology, neighbour agreement.
- Earlier challengers: causal TCN, LSTM autoencoder and Isolation Forest were tested;
  they were not promoted where confirmation gains failed.

Abhi naya Transformer/LSTM add karna first priority nahi hai. Iteration 10 weather
AUPRC 91.89% aur fault AUPRC 19.01% (rare prevalence se bahut above) batate hain ki
ranking signal present tha. Catastrophe probability/policy layer mein thi, capacity
ki kami mein nahi. 10R ke baad agar fault AUPRC/recall genuinely low rahe tab
cadence-aware TCN specialist ka controlled ablation justified hoga.

## 10R run ke acceptance rules

Run ko successful tabhi maana jaye jab:

- `calibration_safety_pass = true`;
- `policy_promotable = true` aur `frozen_policy` null na ho;
- India aur DWD holdout row counts non-zero hon;
- confirmation fault precision har domain/holdout par >=80%;
- false alerts har domain/holdout par <=0.02 per station-day;
- overall incident fault F1 >=70%;
- fault episode recall >=70%;
- India event F1 previous best 65.26% se materially regress na ho;
- fault ECE <=8%;
- weather-to-fault overlap dramatically reduce ho;
- pressure/temperature/humidity correction intervals ke coverage ko 90% target ke
  around separately inspect kiya jaye;
- fresh-seed precision aur false-alarm gates pass hon.

Kisi gate ke fail hone par dashboard demo chal sakta hai, lekin model ko automatic
repair/maintenance system kehkar deploy nahi karna chahiye.

## Ab turant kya karna hai

1. `SkyGuard_AI_GPU_Iteration_10R_Calibration_Integrity_Repair_Colab.ipynb` ko Colab
   mein upload/open karo.
2. Drive mein existing unchanged starter aur DWD development bundles rakho.
3. T4 select karke **Run all** karo. Old Iteration 10 cache copy mat karo; 10R khud
   naya schema folder banayega.
4. 2024/2025 bundle open mat karo.
5. Final cell ke result ZIP aur listed JSON/CSV files wapas do. Uske baad actual 10R
   score ko isi acceptance table ke against audit kiya jayega.


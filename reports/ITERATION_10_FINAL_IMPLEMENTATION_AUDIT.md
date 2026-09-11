# SkyGuard AI — Iteration 10 final implementation audit

## Decision

Iteration 10 ka code, data contract, incident architecture, evidence-only live shadow integration, standalone Colab aur verification package complete hai. Naye model ki empirical accuracy abhi claim nahi ki gayi hai, kyunki final T4 notebook intentionally local CPU par train nahi kiya gaya. Accepted deployment Iteration 5/Phase 10 hi hai. Iteration 10 ko promote karne ka ek hi valid path hai: notebook ke frozen 2023 confirmation outputs saare gates pass karein.

## Real-data evidence

| Evidence | Result |
|---|---:|
| India complete rows | 385,386 |
| DWD hourly development rows | 279,400 |
| Total development rows | 664,786 |
| India stations / clusters | 24 / 4 |
| DWD stations / clusters | 16 / 4 |
| Development years | 2022–2023 only |
| India complete T/P/RH fraction before complete-row selection | 99.930% |
| Duplicate India station timestamps | 0 |
| India clusters with >=2 causal neighbours within 180 minutes | 99.63%–99.94% |
| Locked observation readers in Iteration 10 notebook | 0 |

## Live safety regression

30 August 2026 ke official live METAR refresh par 139 genuine observations aur 12 reporting stations mile. Accepted row model ne 2 research alerts diye aur deterministic QC ne 0 alerts diye. Purani uncalibrated drift shadow policy isi clean window par false critical incidents khol rahi thi. Root cause live-domain CUSUM/climatology shift tha, na ki accepted model ka high fault probability.

Final contract `shadow_evidence_only_unvalidated` hai:

- raw model probability aur drift score dashboard/API evidence mein visible rehte hain;
- promotion se pehle model ya drift evidence incident confirm nahi kar sakta;
- sirf deterministic physical QC, duplicate/out-of-order transport, ya verified communication evidence instant incident path use kar sakta hai;
- old cached shadow incidents policy-version change par invalidate hote hain.

Fix ke baad same live pipeline par active shadow incidents `0` rahe. Yeh ek safety regression result hai, Iteration 10 accuracy claim nahi.

Official India normalization mein MA1 parser defect fix hua: NOAA MA1 ke station-pressure fields pehle ignore ho rahe the. Corrected bundle fake elevation conversion nahi karta; real station pressure fallback use karta hai. Isliye final model absolute aur instantaneous cross-station pressure fields use nahi karta.

## Curriculum evidence

Real-data smoke run:

| Check | Result |
|---|---:|
| 2022 training episodes | 410 |
| 2023 validation episodes | 488 |
| Operational fault families | 13/13 |
| Coherent weather families | 6/6 plus operational regional-temperature replay |
| Episode IDs | Unique |
| Calibration/policy/discovery/confirmation scopes | Disjoint |

Mixed India cadence ke liye injection point requirements station ke observed cadence se adapt hote hain. Hourly DWD assumption ko India par force nahi kiya gaya.

## SIH26073 objective coverage

| SIH requirement | Iteration 10 solution | Status before GPU run |
|---|---|---|
| Real-time anomaly alerts | causal row evidence + elapsed-time incident state + live shadow endpoint | Implemented |
| Spike/frozen/communication faults | deterministic instant path + 13-family operational replay | Implemented |
| Temporal/seasonal learning | lag, robust rolling state, EWMA, slopes, CUSUM, climatology residuals | Implemented |
| Multivariate consistency | T/P/RH consistency and safe T/H neighbour agreement | Implemented |
| Real weather vs fault | exclusive three-way state and independent weather gate | Implemented; metric pending |
| Confidence/severity | L2 calibration, incident confidence and severity | Implemented; ECE pending |
| Explainability | deterministic reasons, LightGBM importance and SHAP export | Implemented |
| Root cause | broad-family CatBoost then constrained subtype CatBoost with abstention | Implemented; metric pending |
| Degradation/maintenance | drift rescue, repeated-incident health score and advisory action | Implemented |
| Corrected value | causal prior/neighbour estimate, interval, MAE/RMSE/coverage | Implemented; metric pending |
| Scalability | batch throughput, memory and model-size outputs | Implemented; measurement pending |
| Dashboard/API | existing judge dashboard plus `/api/live/incidents` evidence-only shadow lifecycle | Implemented |

## ML and policy stack

1. Deterministic QC for impossible values, packet order, verified-heartbeat gaps and multi-sensor freeze.
2. Three-seed regularized LightGBM plus one GPU CatBoost row-evidence ensemble.
3. Seventy-six domain-invariant causal features; no station/domain/location input and no absolute pressure datum.
4. Causal rolling state evidence and three-seed LightGBM incident-state classifier.
5. L2 multinomial probability calibrator fitted only on January–February 2023 development stations.
6. Policy thresholds selected only on March–April 2023 development stations.
7. Independent neighbour-weather gate; a high fault score cannot create a weather decision.
8. Elapsed-time k-of-n persistence, recovery hysteresis, instant hard-fault path and drift rescue.
9. Broad root-family model followed by family-constrained subtype model and low-confidence abstention.
10. Discovery and confirmation are report-only; station holdouts never enter fitting, calibration or policy selection.

TCN/LSTM and Isolation Forest are retained as previous ablation evidence, not automatically inserted into the final alert path. Earlier runs did not prove safe cross-station incremental value. Iteration 10 prioritizes the failure source identified in Iteration 9: row-level veto/threshold structure and lack of incident persistence. A neural model should be added only after a paired incident-level ablation beats this frozen candidate without violating false alarms.

## Verification completed locally

- corrected normalization tests;
- mixed 3-hour cadence curriculum test;
- causal arrival-order test for corrupted timestamps;
- incident-state, triage, drift, diagnosis and metric tests;
- live/API evidence-only shadow integration tests and stale-cache invalidation;
- notebook JSON/syntax/stale-output verification;
- exact bundle SHA-256 verification;
- locked-reader scan;
- empty-policy and non-contiguous-index runtime smoke test;
- full real-data curriculum smoke run.

## Required next action

Run `SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb` on a T4 using the two approved ZIPs. Return `SkyGuard_Iteration10_Result_Package.zip`. Do not open any 2024/2025 file. The result block—not an estimated SIH score—will decide whether the model is excellent, weak, or eligible for one locked confirmation.

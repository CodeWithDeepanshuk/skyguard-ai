# SkyGuard folder review — 11 September 2026

## Seedha verdict

Har file live SIH solution mein contribute nahi karti. Yeh folder ek working prototype + research history + data archive + delivery workspace hai. Relevant hona, runtime mein use hona aur scientifically validated hona teen alag baatein hain.

Inventory snapshot: 866 files including the inventory utility, approximately 1.81 GiB. 113 cache files; 17 exact duplicate groups. Audit output directory itself excluded. Existing project source/model/data files were not edited or removed during this review. Tests may regenerate interpreter caches.

## Audit ka scope aur limit

- Har filesystem file enumerated, sized, SHA-256 hashed and assigned a role in EVERY_FILE_REVIEW.md / inventory.json.
- Local API Python import graph traced; explicit model and report loads inspected.
- Python source parsed; JSON parsed; notebook code-cell counts and saved error outputs inspected without running notebooks. ZIP/PPTX container directories inspected, not every archived member interpreted.
- 94 existing Python tests passed in 25.12 seconds; one Starlette/httpx deprecation warning. This proves covered software checks, not model accuracy or every user flow.
- Large data tables, binary model internals and presentation slides were NOT exhaustively semantically reviewed. No binary model deserialization or test-set scoring was performed. Inventory role classification is evidence-assisted triage, not proof that every scientific claim in every file is correct.
- Existing provenance reports were read, but raw files were not redownloaded and historical manifest hashes were not independently revalidated against their providers in this audit. Local SHA hashes establish an inventory, not external authenticity.

## File groups aur contribution

| Group | Actual role | SIH relevance / handling |
|---|---|---|
| src/skyguard/api/app.py | HTTP API, dashboard, live/replay routing and evidence endpoints | Direct runtime; essential |
| src/skyguard/live/metar.py | METAR fetch, normalization, cached observations, model scoring | Direct runtime; not direct IMD AWS telemetry |
| features/builder.py, temporal.py, phase10.py, neighbors.py, contracts.py | Temporal, spatial and three-variable feature construction | Essential; spatial source compatibility still needs work |
| quality/engine.py, rules.py, models.py | Physical/transport QC contracts and state | Essential; rules are not proof of real sensor failure |
| incidents/*.py and models/phase10.py | Incident logic, diagnosis, drift/triage, persistence | Imported runtime modules; individual classes/functions may not all execute on every request |
| streaming/*.py | Offline scenario replay and SQLite state | Required offline demonstration support |
| models/phase10_final.joblib | Actual direct live-model bundle | Keep; headline metrics must refer to this model |
| models/phase10_climatology.joblib | Actual direct live climatology | Keep |
| Other 15 files in models/ | Earlier/alternative models or policy files | Research/reproducibility; not all simultaneously deployed |
| dashboard/ (13 files) | UI, maps, chart, local Leaflet, offline land geometry and QC display | Visualization; JS neighbour diagnostic does NOT retrain ML |
| data/raw, manifest, processed | Source, lineage and normalized historical observations | Essential research evidence; not necessary in every deployment |
| data/labelled, features, features_phase10 | Injected fault labels and feature tables | Training/evaluation, not live observations |
| data/predictions* and incidents | Historical predictions, correction and health evidence | Offline benchmark; must not masquerade as current station health |
| data/demo, live, runtime | Offline scenarios, mutable live cache, mutable SQLite | Runtime support; cache freshness must be checked |
| data/iteration8, iteration10 | DWD / revised India development data | Relevant transfer experiments; not deployed just because present |
| data/blind_2025 | Previously opened evaluation artifacts | Preserve; no longer an untouched holdout |
| reports/ and iteration 10 result/ | Evidence and iteration outcomes | Relevant, including rejected experiments; not all results are current |
| notebooks/ (13) and tools/ | Colab iterations, builders, audits, experiment scripts | Development tools; notebook existence does not establish successful training |
| tests/ | Regression checks | Keep; missing coverage still possible |
| docs/ and README | Delivery, use cases, model card and operating guidance | SIH requirement; stale statements need reconciliation |
| deliverables/ (48 original files) | Packaged handoffs and releases | Helpful distribution copies; some are exact duplicates |
| Letter to write/writing-block.md | Administrative access request | Enables data access, not inference; keep private |
| .pytest_cache and __pycache__ | Generated caches | No direct scientific contribution; regenerable |
| Root PPTX + deliverables PPTX | Identical presentation copies | Presentation support, not model evidence; slide claims not checked visually |

## Confirmed findings and priorities

### P1 — selected-city incident evidence can still be wrong

dashboard/app.js uses `selectedStation match || state.incidents[0]` after a live refresh, and another first-incident fallback in the alert handler. The trace selection fix does not eliminate this incident-panel problem. If the selected station has no incident, show an explicit empty state rather than another station's explanation.

### P1 — verification launcher can report success incorrectly

verify_skyguard.ps1 executes native python/node commands and unconditionally prints success. `$ErrorActionPreference = 'Stop'` alone does not reliably turn native nonzero exit codes into terminating errors. Check `$LASTEXITCODE` after each command. The same script runs a profiling utility, so it is not a purely read-only validator.

### P1 — training/evaluation separation remains a promotion concern

src/data/train_phase10_full_data.py fits its calibrator on validation, selects thresholds on that same validation and then scores both 2024 splits. That script is not a safe 'improve model' button now that those tests have been repeatedly inspected. Calibrator fitting and policy selection share data; use a distinct calibration/selection/confirmation protocol for new claims.

tools/build_gpu_iteration10r_notebook.py builds train_state from base predictions on train_features and fits the state model on it. These are in-sample first-stage predictions rather than out-of-fold ones. This creates a stacking distribution mismatch/overfit risk; it is not evidence of direct future-test leakage by itself. Repair with temporal out-of-fold stage-one predictions before promoting the state model.

### P1 — inconsistent scientific/operational claims

docs/SIH_COMPLIANCE.md calls mandatory functions complete and demonstration-ready; docs/MODEL_CARD.md more correctly lists limited recall, diagnosis coverage and operational limitations. reports/ITERATION_10R_FULL_AUDIT_AND_FEASIBILITY_ROMAN_HINDI.md still describes a GPU run as pending. A static/synthetic validation pass must not be treated as successful returned-model performance.

dashboard/app.js empty alert queue still says 'All stations normal'. No alert is not proof of healthy sensors. dashboard/index.html also has 'Live AWS Operations' and a 'Continuous ... WMO physical quality rules' initial placeholder while actual source is periodic airport METAR. Update these labels, not the data, to match evidence.

### P2 — live cache age is a snapshot

src/skyguard/live/metar.py computes source_age_minutes when refreshing; status() returns stored fields. Cached or repeated status responses can display a frozen age. Compute current age at response time and distinguish newest-network timestamp from each station's timestamp.

### P2 — neighbours lack full physical compatibility

features/neighbors.py currently chooses nearest members of the same configured cluster; no explicit radius/elevation gate or pressure-datum compatibility filter is applied to sensor comparison. SLP, QNH and station pressure should not be treated as interchangeable. The proposed stricter neighbour-selection step was inspected but NOT implemented before this audit request.

### P2 — experimental improvements are not accepted improvements

reports/github_qc_challenger/comparison.json shows the latest challenger failed its gate. Matched baseline vs challenger F1: 44.09% vs 43.67%; false alarms/station-day: 0.02484 vs 0.03877. Preserve the result as useful negative evidence; do not promote or cite its larger incident recall alone.

### P2 — package scope is too broad for blind public deployment

Dockerfile uses COPY . .; .dockerignore excludes some training directories but not every newer iteration directory, administrative letter or root result folder. Some are unnecessarily included. The application has mutable cache and SQLite state; local running is not equivalent to successful Vercel deployment.

### P3 — duplicates and caches

17 byte-identical groups were detected. Examples: the two final PPTX copies, matching deliverable/notebook copies of Iterations 10 and 10R, archived CSV/JSON results, and identical iteration2/iteration3 episode recall files. Equality can reflect a retained baseline or intentional release; it does not prove fraud or an error. Archive by purpose and preserve provenance. No deletion authorized or performed.

## SIH26073 coverage: implemented versus proved

| Objective | Assessment |
|---|---|
| Three atmospheric detector parameters | Implemented contract; RH derived in METAR adapter |
| Real-time observations and alerts | Near-real-time METAR prototype; direct IMD AWS and field performance unverified |
| Spikes, freezes and communications | Implemented rules/models and simulation; weak-fault recall and heartbeat availability limit reliability |
| Temporal/seasonal and multivariate learning | Feature/model implementation exists; valid on all climates not established |
| Distinguish true weather from faults | Implemented and historically evaluated; transfer and source conventions remain risks |
| Confidence/explanations/root cause | Present; calibration/coverage and station-specific UI alignment need improvement |
| Degradation/maintenance prediction | Heuristic/research support, not confirmed with maintenance outcomes |
| Corrected values | Advisory optional output, not safe unattended replacement |
| Visualization | Functional map/chart/dashboard; identified UI truthfulness gaps remain |
| Scale/energy/edge | Local profiling/projections, not national deployment or measured hardware energy; ESP32 not implemented |
| Executable delivery and use cases | Present; reproducibility and launcher failure handling need tightening |

## Verified benchmark identity

Deployed Phase10 report/model card: 2024 time split precision 71.47%, recall 41.50%, F1 52.51%, episode recall 79.17%. Station split precision 89.89%, recall 32.00%, F1 47.20%, episode recall 63.33%. These are retained historical injected-fault metrics, not newly recomputed or live accuracy. They should not be combined with Colab iteration results as if one model produced all of them.

## Recommended next steps (not applied in this audit)

1. Correct live incident selection, empty states, freshness and verification failure handling.
2. Maintain explicit active-model and dataset manifests; label candidate and historical artifacts.
3. Repair training/calibration/stacking protocol before adding more models.
4. Implement stricter neighbour compatibility in a separate experiment; compare multiple seeds, stations, natural weather and latency, not F1 alone.
5. Reconcile README, compliance, model card, latest returned run and slides into one truthful release statement.
6. Separate runtime bundle, research workspace and private administrative material. Move/delete only with explicit authorization.

Bottom line: yeh SIH-relevant prototype hai, lekin 'har file zaroori hai', 'har feature complete hai' aur 'best validated live model hai' teenon claims supported nahi hain.

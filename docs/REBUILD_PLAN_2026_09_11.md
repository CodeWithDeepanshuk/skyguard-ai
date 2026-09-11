# SkyGuard reliability-first rebuild plan

Status: proposed execution plan; no existing models, source data or live policies replaced by writing this document.

## Scope and honest progress estimate

Approximately 55–65% toward a reliable, reproducible SIH software demonstration, as an engineering judgment—not a measured completion percentage, accuracy, official SIH score or acceptance prediction. The UI and core code are ahead of scientific and operational validation. Production IMD readiness cannot be assigned a defensible percentage from the available evidence.

Retain the local dashboard, API, raw-source archives, fault simulator, useful tests and existing model as a frozen comparator. Preserve rejected iterations for traceability. Rebuild data contracts, evaluation protocol and model promotion workflow before choosing a larger architecture. Do not delete or move archives without authorization.

## Phase R0 — establish a single reproducible baseline

- Record deployed model hash, model version, supported schema, preprocessing, thresholds, dependencies and evaluation provenance in one release manifest.
- Label all candidate/rejected/legacy artifacts. Keep 2024/2025 previously inspected results as historical benchmarks, not fresh tests.
- Correct verification script nonzero exit handling, selected-station incident fallback, cached-age calculation and misleading health labels.
- Exit: one startup path, failure-aware verification and station-specific UI regression tests; no model change.

## Phase R1 — data suitability before data volume

- Define per-observation station id, observed timestamp and timezone, arrival timestamp when genuinely available, temperature C, pressure hPa with datum, RH percent with reported/derived flag, source, units and provenance.
- Keep QC flags for audit; never silently use injected labels, clean targets, episode ids or source QC labels as inference features. Metadata supports routing/context, not source-identity shortcuts.
- Separate station pressure, QNH and sea-level pressure. Do not silently switch or pool them. Any justified conversion must retain original values, metadata, assumptions and uncertainty.
- Audit station-level cadence, gaps, duplicate reports, source changes, missingness, climate/season coverage and neighbour overlap. Do not reconstruct real arrival times from observation timestamps and call them measured arrivals.
- Public processed weather can already have QC filtering; it is not guaranteed raw sensor telemetry. Fault injection is permitted by the supplied SIH statement but must be identified as simulated.
- Exit: reproducible readiness table per station and dataset, including missing prerequisites.

## Phase R2 — evaluation contract before another training run

- Separate chronological fit, early stopping, probability calibration, policy selection and confirmation blocks; respect episode boundaries and add a purge gap appropriate to the feature lookback.
- Group station holdouts and keep domain results separate. Choose an actually uninspected station/time set before examining its outcome; opened years cannot be made blind again by renaming.
- Train stacked/incident models using chronological out-of-fold first-stage predictions or a separate fit block, not in-sample predictions.
- Fit preprocessing and normal reference distributions only on the designated fit data. All temporal/spatial lookups causal at the claimed time of detection.
- Define one prespecified model comparison and promotion policy, plus multi-seed/station uncertainty reporting. Subsequent tuning consumes a confirmation set as development data.
- Exit: leakage/integrity tests and frozen split/feature/policy contracts.

## Phase R3 — targeted acquisition, only after the gap audit

- Preferred target-domain feed: authorized IMD AWS T/P/RH and station metadata, sampling/heartbeat information and maintenance/fault records if obtainable. Access is not guaranteed; do not block the whole project indefinitely.
- Existing NOAA Indian station observations remain valuable. Acquire additional compatible station-periods only where they repair identified seasonal/cadence/station gaps; verify source schema and licenses first.
- Existing DWD is a separate external-domain robustness dataset, not a substitute for Indian validation. Preserve domain-specific reporting and pressure conventions.
- Accumulate new live METAR reports for operation/freshness evidence; unlabelled live data does not establish accuracy or reveal a hardware fault by itself.
- Reserve some genuinely new compatible data before exploration for final evaluation. Avoid downloading arbitrary Kaggle/forecast/reanalysis collections as sensor-fault ground truth.
- Exit: a small verified pilot before a larger download; no new model yet.

## Phase R4 — correct classical baseline and physical context

- Physical range and finite-value checks, causal step/persistence tests, saturation-aware RH handling, duplicate/out-of-order state, and verified-heartbeat missing-packet detection.
- Strict spatial context: radius, elevation, time alignment, comparable pressure datum and sufficient independent neighbours. Missing support means unavailable, not healthy/faulty.
- Compare rules/Hampel/EWMA/CUSUM with regularized LightGBM and CatBoost on identical splits and fault prevalence. Bound the tuning budget.
- Reuse Titanlib concepts as a documented comparator; installing its library does not validate thresholds or Indian sparse-network behavior.
- Exit: per-fault, per-station and per-domain metrics with baseline errors explained.

## Phase R5 — one neural challenger only if evidence justifies it

- First choice: a small causal TCN for temporal weak-fault/drift residuals, using masks, elapsed-time information and station-local sequences. Never construct sequences across different stations or future rows.
- LSTM/GRU is an alternative comparator, not a mandatory addition. Autoencoder and Isolation Forest are novelty/abstention candidates; unusual weather can also produce reconstruction/anomaly scores.
- No default switch to large Transformers, TabPFN or a multi-model ensemble. Neural models must beat the tree/rule baseline at the same false-alarm budget and comparable inference cost.
- Use Colab T4 for this stage if warranted. Calibration and policy training remain disjoint and at realistic prevalence.
- Exit: freeze winner or retain baseline; report rejected challengers honestly.

## Phase R6 — incidents, diagnosis and trustworthy live operation

- Connect accepted detector to the same feature/state code in offline replay and live ingestion; test parity.
- Incident hysteresis, probable fault-family diagnosis, confidence abstention and local explanations.
- Distinguish no report / stale report / review signal / verified transport evidence; do not equate lack of an alert with sensor health.
- Corrections advisory and raw values immutable. Maintenance remains an explainable risk indicator unless labelled maintenance outcomes support a predictor.
- Live performance is arrival-to-alert latency; source publication delay is measured separately. Offline fault simulations stay explicitly separate from genuine live reports.
- Exit: long-running replay/live soak tests, provider-failure recovery and station-specific UI consistency.

## Phase R7 — acceptance and delivery

- Proposed internal targets, NOT official SIH minimums or guaranteed achievable scores: point precision >=85%, recall >=60%, F1 >=70%; episode recall >=80%; false alerts <=0.02 per station-day; weather-as-fault <=2%. Evaluate on each relevant station/domain slice, not just pooled data. Show denominators and uncertainty, especially where positives/weather episodes are few.
- Report root-cause accuracy AND abstention coverage, probability calibration (Brier/reliability), per-fault latency, correction MAE AND coverage, CPU/RAM and end-to-end p95/p99 arrival-to-alert latency. Set a latency target after defining the actual network load and reporting cadence.
- Do not force optional corrections or maintenance claims merely to meet a checklist. Missed targets require an honest limitation report and scope decision, not retuning on the final holdout.
- Publish a lean runtime package with pinned/reproducible dependencies, private administrative material excluded, one training notebook and one model card. Full retraining and deployment are distinct verification steps.

## Immediate next execution

Start R0 and R1 with existing data. Do not first replace the model, download a large unrelated collection, or repeat prior notebook chains. Produce a baseline manifest, fix confirmed correctness bugs and a station-level data gap report; use that report to decide R3 acquisition.

## Sources informing recommendations

- Project audit: ../deliverables/FOLDER_AUDIT_2026_09_11/REVIEW_SUMMARY_ROMAN_HINDI.md
- Model card: MODEL_CARD.md
- NOAA ISD fields and provenance: https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database
- Weather QC/spatial checks: https://github.com/metno/titanlib
- Tree/deep-learning benchmark (not AWS-specific): https://arxiv.org/abs/2207.08815
- Broader tabular comparison (not a guarantee for this dataset): https://arxiv.org/abs/2407.00956

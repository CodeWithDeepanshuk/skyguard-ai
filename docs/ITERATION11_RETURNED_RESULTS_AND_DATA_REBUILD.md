# Iteration 11: returned-result review and corrected data rebuild

Reviewed 12 September 2026. The uploaded `iteration 11 result` directory and its executed notebook are preserved unchanged. This report separates measured results, source-code defects and hypotheses. It does not certify production readiness or assign an SIH judge score.

## Decision

Do not promote the returned Iteration 11 model. Its own result says `promoted: false`. Do not interpret its title as evidence of training on 543/545 stations. Continue with the separately named **SkyGuard_AI_Iteration_11_Data_Rebuild_Colab.ipynb**, which downloads new observations instead of repackaging only a larger catalog.

## What the returned run actually used

`iteration11_result_block.json` records 385,386 usable Indian rows from **24 Indian stations**, plus 279,400 hourly-selected DWD rows from **16 German stations**, for 2022–2023. The local ZIP named `SkyGuard_Iteration11_All_India_545_Stations_Bundle.zip` contains 385,656 Indian rows before complete-case filtering and still only **24 distinct observation station IDs**. Its 543-entry station catalog does not expand the training observations.

The executed notebook reads `india_aws_2022_2023.csv.gz` and `india_stations.csv`; it does not acquire the 441 additional-public-archive candidate network. Metadata, observations, eligible training stations and actually fitted stations must be counted separately.

## Measured returned results

| Metric | Result | Interpretation |
|---|---:|---|
| Three-class point accuracy | 91.96% | Misleading alone: always predicting normal gives **96.61%** accuracy on these same labels, but detects no faults. |
| Point fault F1 | 5.68% | Fault decisions are weak. |
| Fault incident precision | 1.56% | 25 matched true incidents / 1,600 predicted incidents. |
| Fault episode recall | 37.88% | 25 / 66 injected fault incidents detected; 41 missed. |
| Fault incident F1 | 3.00% | Not operationally acceptable. |
| False incidents | 1,575 | 0.1807 per station-day across 8,714 station-days. |
| Median matched-fault latency | 300 minutes | Five hours; missed incidents are not included in matched latency. |
| India incident precision / recall / F1 | 0.73% / 33.33% / 1.44% | Particularly severe false-alarm problem. |
| DWD incident precision / recall / F1 | 13.73% / 42.42% / 20.74% | Better than India here, but still weak; not a successful DWD model. |
| India station-holdout fault recall | 0% | This returned evaluation detects no matched holdout fault incidents. |
| Drift / bias episode recall | 10% / 20% | One of ten drift incidents and two of ten bias incidents detected. |
| Frozen-sensor episode recall | 60% | Six of ten incidents. |
| Root-cause accuracy / macro F1 | 44% / 34.69% | On 25 matched incidents only, not all66 true incidents. |

Evidence: `iteration11_result_block.json`, `iteration11_multidomain_confirmation.csv`, `iteration11_fault_episode_recall.csv`, `iteration11_root_cause_metrics.csv`. Point and incident metrics have different definitions and must not be compared as the same score.

## Confirmed implementation/reporting defects

1. **Data expansion was not implemented in the returned notebook.** The 545-station title described metadata, while fitting still used24 Indian stations. Merely changing bundle names is not a new dataset.
2. **False policy-eligibility flag.** `iteration11_policy_frontier.csv` has111 candidates and zero eligible policies. `iteration11_frozen_policy.json` agrees (`eligible_policy_count: 0`). The notebook's fallback nevertheless sets `POLICY_PROMOTABLE=True`, making `eligible_policy_found` pass incorrectly. The reported8/25 passed gates is therefore not reliable; this flag alone removes one reported pass. Gate count is not SIH completion percentage.
3. **Checksum validation bypass.** The supplied builder/notebook permits a starter checksum via `actual in VALID_STARTER_HASHES or True`. Consequently, an integrity `PASS` cannot prove starter checksum enforcement. This does not establish that the uploaded archive was corrupted; it establishes that the check cannot catch corruption.
4. **Single-sensor flatline hard override.** The notebook marks a single sensor frozen after eight repeated readings and routes it through hard-fault handling. Repeated rounded observations can be legitimate. Elapsed time, resolution, past variability and independent evidence matter; eight rows are not a universal failure criterion. The new rebuild treats flatline duration as model evidence, not a compulsory hardware-failure label.
5. **Pressure incompatibility remains a data-contract issue.** The old normalizer can switch between station pressure, sea-level pressure and altimeter pressure. Excluding absolute pressure features does not prevent a datum switch from corrupting pressure deltas/slopes. The rebuild freezes one pressure type per station from2020–2021 and retains missing values instead of switching types.

## Corrections to the pasted explanation

- It is **not true that all spatial features were removed**. Reconstructing the executed `STRICT_FEATURES` leaves25 neighbour-related features, including temperature/humidity residuals and pressure-neighbour residual slopes. Instantaneous pressure-neighbour and several regional aggregate features were excluded. An ablation is needed to quantify the effect of each exclusion.
- The confusion matrix proves7,897 normal and531 weather rows were predicted faulty. It does **not prove that every one was caused by the freeze rule**. Per-rule predictions or a replay with that rule disabled are required for causal attribution.
- `k=1` is not universally wrong: single-point spikes can require immediate alerts. A universal `k>=3` could miss them and delay other events. Persistence needs fault-specific evaluation, not a promise that changing it will raise precision above80%.
- Small aggregate ECE does not establish “rock-solid calibration.” Most probabilities fall in the normal-dominated low-probability bin. In the returned fault bin averaging0.6437, the actual fault fraction is0.3041. Alert-region reliability and low incident precision remain concerns.
- Temperature/humidity comparisons are not elevation-independent, and pressure tendency is not guaranteed elevation-neutral. Same-datum changes are safer, but representativeness, elevation, timestamps and source conventions still matter.
- No evidence supports the pasted guarantees “false incidents below100”, “precision above80%”, or “mathematically impossible without these exact fixes.” They are hypotheses, not measured outcomes.

## Corrected Iteration 11 Data Rebuild

The corrected standalone notebook implements:

1. Official NOAA metadata plus annual directory discovery for **all Indian candidates**, not an old24 list restriction.
2. Download/retry/checksum/resume for2020–2023 observations, with explicit failures and no silent schema substitution.
3. Per-station raw provenance, reported/derived RH identification, preserved QC flags, duplicate handling and one fixed pressure datum.
4. Training eligibility based on2020–2021 completeness and distinct days; non-screened rows remain unknown, not negative ground truth.
5. Distance/elevation/datum/age-constrained neighbours. Missing support remains unavailable; no invented neighbouring observations.
6. Geographic station holdouts, separate early-stop/calibration/policy periods, and honest2023 development confirmation rather than a rebranded blind test.
7. Controlled synthetic faults before causal features in both target and neighbouring streams; no clean-neighbour oracle.
8. Robust-QC, temporal LightGBM, spatial LightGBM, optional spatial CatBoost and a same-protocol legacy24 retrained comparator when sufficient old stations qualify.
9. Full-prevalence calibration/evaluation; fault-specific and per-station reports. Failed policy gates stay failed. No automatic live promotion.

This version intentionally does not claim trained root-cause/maintenance/correction or communication-loss performance. Those project components remain separate, unpromoted research capabilities pending validation. A missing sensor value is not a missing packet; a known reporting SLA is required to assess communication faults.

## Verified new-source scope and pilot

Official metadata/listings cached11 September2026 contain545 Indian IDs,543 with coordinates, and **441 IDs with at least one listed2020–2023 file** (1,596 station-year files:407/404/389/396 by year). Final usable network size is not yet known.

A local bounded test downloaded **24 real files for six stations outside the original24**: Lucknow, Fursatganj, Bahraich, Patna, Gaya and Darbhanga. Their processed files contain197,510 total rows across2020–2023. Five pass the training data guard, with83,365 QC-screened2020–2021 rows combined. Darbhanga fails this pilot's minimum-history guard. Three stations have at least two geographic buddies, but none have two pressure-compatible buddies under the conservative pilot graph. More station names alone do not guarantee usable spatial pressure support.

The small CPU smoke test reached feature building, LightGBM and CatBoost training, calibration, policy selection and confirmation. It is labelled `smoke_test_only: true`; these pilot scores are **not** national-performance claims or directly comparable to the old incident benchmark. Full-network training has not run locally.

## What to do now

Run **SkyGuard_AI_Iteration_11_Data_Rebuild_Colab.ipynb**, keep `RUN_MODE='all_available'`, and return `SkyGuard_Iteration11_Data_Rebuild_Reports.zip`. No old starter/data ZIP is required. The notebook downloads suitable candidates itself and reports actual eligibility. Download/preparation runs on CPU; CatBoost can use T4. Checkpoints make multi-session runs possible.

The current public source remains an Indian surface/airport observational proxy. Direct IMD AWS measurements, especially directly measured RH and consistent station pressure, are preferable for final field validation. IMD's1008 network count is a different catalog, not evidence that1008 suitable historical streams are publicly downloadable.

Sources: [NOAA station histories](https://www.ncei.noaa.gov/products/land-based-station/station-histories), [NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database), [GHCNh transition](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly), [IMD AWS API reference](https://api.imd.gov.in/public/api_reference.html), [PIB18 March2026 AWS network count](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2241702).

Website deployment is separate from model promotion. The GitHub repository exists, but this audit has no verified Vercel deployment URL or authenticated Vercel project connection. Do not claim a successful deployment or replace the live model with the failed returned candidate.

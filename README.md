# SkyGuard AI — SIH 26073

An offline-first, live-capable anomaly detection and decision-support system for Automatic Weather Stations using only temperature, atmospheric pressure, and relative humidity as detector inputs.

## Current verified status

**11 September 2026 — R0 baseline:** the deployed model is unchanged. The new [R0 record](docs/R0_BASELINE_2026_09_11.md) and [active release manifest](config/active_model_manifest.json) distinguish current runtime from historical experiments. R0 verifies display/contracts and byte preservation, not accuracy or complete SIH acceptance. The historical descriptions below are not proof that data suitability, calibration or live sensor-fault performance have been independently validated.

SkyGuard has a **Phase 10 compliant competition prototype**, a frozen Iteration 5 development reference, and a standalone **Iteration 10 final-development challenger**. The deployed detector remains `SkyGuard-P10-compliant`; Iteration 10 stays in evidence-only shadow mode until its T4 result passes every incident, weather, root-cause, calibration, transfer and false-alarm gate. Before promotion, live model/drift evidence is visible but cannot confirm an incident; only deterministic QC or transport evidence can use the immediate path. The challenger combines corrected official India data with official DWD multi-climate data, complete operational fault coverage, causal incident state and hierarchical diagnosis. It never opens 2024/2025 observations. Dew point, location, station/domain identity and pressure-datum shortcuts are not model inputs.

- 664,786 complete 2022–2023 development rows across official India and DWD sources
- 40 stations in eight regional/climate clusters: India 24 and DWD 16
- 2022 fitting; disjoint 2023 calibration, policy, discovery and confirmation; station holdouts excluded from all selection
- 13 operational fault classes, six coherent weather families, verified-heartbeat dropout detection and advisory unknown-cadence gaps
- offline replay and genuine live AviationWeather.gov METAR mode
- alert confidence, severity, root cause, evidence, advisory correction, uncertainty, health, degradation trend, and maintenance guidance
- causal incident-state, drift, hierarchical diagnosis and incident-metric modules with regression tests
- a completed one-time 2025 blind-time and blind-station evaluation; its labels are now closed to further tuning

The primary compliant benchmark is:

| Split | Precision | Recall | F1 | AUCPR | Episode recall | False alarms/station-day |
|---|---:|---:|---:|---:|---:|---:|
| 2024 unseen time | 71.47% | 41.50% | 52.51% | 48.45% | 79.17% | 0.0429 |
| 2024 unseen stations | 89.89% | 32.00% | 47.20% | 41.95% | 63.33% | 0.0064 |

Earlier Phase 5 scores are retained only as historical experiments because that model used a dew-point-derived feature. They are not the submission headline.

## Run the project

Double-click `start_skyguard.bat`, or run:

```powershell
python src/data/run_api.py
```

Open `http://127.0.0.1:8000/`. The `/docs` route is the developer API tester, not the judge-facing dashboard.

- Use **Offline replay** for a deterministic SIH demonstration without internet.
- Use **Live observations** to fetch genuine METAR observations. Temperature and QNH pressure are reported by the source; relative humidity is derived before the detector receives the three permitted values.

## Verify the R0 code and data-preservation contracts

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File verify_skyguard.ps1
```

This uses a process-scoped script setting only, not a machine policy change. Historical report regeneration is opt-in with `-RefreshHistoricalReports`; it is not a fresh blind evaluation.

The default run checks automated code/contract regressions, dashboard JavaScript and unchanged model/data hashes. It does not rerun training, benchmark inference speed, validate live accuracy or certify correction safety in the field.

## Runtime architecture

```text
AWS/METAR/replay observations
  -> schema + deterministic communication/physical QC
  -> causal temporal, seasonal, multivariate and neighbour features
  -> calibrated LightGBM event detector
  -> neighbour-weather gate + station-specific operating policy
  -> incident-level root diagnosis and confidence abstention
  -> advisory correction + uncertainty
  -> health/degradation forecast + maintenance recommendation
  -> FastAPI + SQLite + dashboard + downloadable incident report
```

The causal TCN remains advisory. It was not placed in the automatic alert path because its false-alarm behaviour on new stations did not meet the deployment constraint.

## Run the final Iteration 10 challenger

Use [the standalone Colab notebook](notebooks/SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb) with the two checksummed ZIPs in `deliverables/`. Follow [the Roman-Hindi execution guide](docs/ITERATION10_COLAB_EXECUTION_GUIDE_ROMAN_HINDI.md). The notebook must produce `iteration10_result_block.json` before any new accuracy claim or deployment decision.

## Reproduce the main evidence

```powershell
python src/data/download_noaa_dataset.py
python src/data/normalize_noaa_isd.py
python src/data/validate_dataset.py
python src/data/run_qc_baseline.py
python src/data/generate_labelled_faults.py
python src/data/validate_labelled_faults.py
python src/data/generate_features.py
python src/data/validate_features.py
python src/data/generate_phase10_features.py
python src/data/finalize_phase10.py
python src/data/run_correction_health.py
python src/data/validate_correction_health.py
python src/data/run_safe_repair.py
python src/data/validate_safe_repair.py
python src/data/package_replay_scenarios.py
python src/data/profile_streaming_platform.py
python src/data/validate_streaming_platform.py
python src/data/profile_competition_readiness.py
python src/data/validate_dashboard.py
python src/data/final_verification.py
```

Canonical observations: `data/processed/aws_observations_2022_2024.csv`

## Most important documents

- `docs/SIH_26073_COMPETITIVE_AUDIT.md` — requirement coverage, score estimate, gaps, and competitive targets
- `docs/FINAL_REPORT.md` — start-to-finish implementation and current metrics
- `docs/ARCHITECTURE.md` — repository, runtime structure, and model stack
- `docs/MODEL_CARD.md` — intended use, exact inputs, exclusions, performance and safety limits
- `docs/IMPROVEMENT_ROADMAP.md` — ordered model and deployment improvement plan
- `docs/BLIND_2025_RUNBOOK.md` — exact one-time T4 Colab evaluation procedure
- `docs/BLIND_2025_HINDI_REVIEW_AND_ITERATION_06_PLAN.md` — Roman-Hindi result explanation and next-phase design
- `docs/GPU_ITERATION_REVIEW.md` — what improved and what did not across GPU iterations
- `reports/ITERATION_08_NEW_DATA_RUNBOOK.md` — official DWD new-data contract, sealed split and T4 procedure
- `docs/SKYGUARD_MASTER_PROMPT.md` — reusable engineering prompt for future iterations
- `docs/SKYGUARD_FINAL_COMPLETION_MASTER_PROMPT.md` — final SIH26073 engineering and acceptance contract
- `docs/ITERATION10_COLAB_EXECUTION_GUIDE_ROMAN_HINDI.md` — exact standalone T4 run and result interpretation
- `docs/DEMO_SCRIPT.md` — judge presentation flow
- `docs/LIVE_DATA.md` — live source mapping and limitations
- `docs/DEPLOYMENT.md` — Windows, Python and container runtime instructions
- `reports/final_verification.md` — current automated delivery result
- `reports/competition_readiness.md` — full inference and scale evidence
- `deliverables/SkyGuard_AI_SIH26073_Final.pptx` — presentation; update its metrics before final submission
- `deliverables/SkyGuard_Blind_2025_Bundle.zip` — sealed official-source 2025 benchmark
- `notebooks/SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb` — final development challenger; does not open 2024/2025

## Evidence boundary

This is a strong SIH prototype, not a certified IMD production deployment. Controlled faults provide known labels; genuine public observations provide meteorological realism. Operational approval still requires an official IMD AWS adapter, real maintenance labels, a newly frozen prospective holdout, distributed load testing, and calibrated energy measurement.

Official data source: https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database

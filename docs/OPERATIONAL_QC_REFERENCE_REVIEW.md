# Uploaded operational-QC reference: adoption and implementation

Date: 2026-09-08. Continue from Iteration 10/10R.

The supplied reference aligns with the user-provided SIH26073 objectives in its
hybrid quality-control, temporal ML, weather protection, explanation, and raw-data
preservation approach. It is a research proposal, not measured project evidence.

## Implemented in this review

| Change | Implementation | Purpose |
|---|---|---|
| Pressure-source-aware validity envelope | quality/models.py, quality/rules.py | Avoid applying sea-level lower bounds to high-altitude station pressure |
| Explicit NaN/infinity alerts | quality/rules.py | Prevent undefined comparisons and scores |
| Reset persistence after observation gaps | quality/engine.py | An unobserved interval does not establish a stuck sensor |
| Reset pressure persistence on source change | quality/engine.py | Different pressure products must not share persistence evidence |
| Persistent 100% RH produces review evidence | quality/engine.py | Atmospheric saturation and clipping cannot be distinguished by constancy alone |
| Statistical QC cannot immediately confirm a live incident | live/metar.py | Rate, persistence and provider flags need corroboration |

Station/unknown pressure uses a configurable 300–1100 hPa screening envelope.
This is a project default, not a universal physical law or WMO/MADIS certification.
Known sea-level/QNH products retain the existing configurable screening limits.
Range failure means failing a configured QC check, not a verified broken sensor.
Multi-channel freeze is still separate corroborating evidence.
All changes run within the existing live QC path; saved experimental model weights
and old performance reports are unchanged. Changed QC behavior requires fresh evaluation.

## Reference recommendations and decisions

| Recommendation | Decision |
|---|---|
| Hybrid rules + temporal model + boosted trees | Existing project direction; retain and compare components on identical splits |
| MADIS public QC data | Valuable next external validation source; provider flags are weak labels, not verified physical fault diagnoses |
| MADIS passed-QC background | Candidate clean background only; preserve extremes and original flags; passing QC does not prove truth |
| T/RH-derived vapor pressure or dew point | Uses permitted inputs mathematically, but deriving RH from original dew point makes some relationships circular; separate experiment required |
| Mixing ratio | Requires actual station pressure; do not substitute QNH/sea-level pressure |
| Centered spike window and next-observation explanation | Offline retrospective analysis only; live inference uses present/past available observations |
| TCN/LSTM normal-weather forecast | Existing temporal candidates require causal evaluation; adding another network does not repair calibration/leakage |
| Logistic score fusion | Fit on out-of-fold or independent predictions; calibrate separately at realistic class prevalence |
| Forecast uncertainty | Validate empirical coverage and interval width by sensor/domain/season |
| Extreme-weather stress set | Required next evaluation; observationally supported extremes must be distinguished from synthetic weather |
| Leave-one-fault-type-out | Useful separate experiment; freeze splits before training |
| ERA5/POWER | Optional offline atmospheric context; not independent sensor ground truth, not required runtime inputs |
| ESP32 student/INT8 | Optional future software export; actual energy/hardware claims need measurement; user's no-hardware constraint remains |
| Download 2015–2025 | Do not blanket-open previously protected or inspected test years; define a development-only acquisition manifest first |
| 95–99% accuracy claims | Not established; targets cannot be converted to expected results or jury scores |
| New repository layout | Retain existing project structure and tested integration |

## Next execution order

1. Finish 10R stacking audit: downstream training must not use in-sample base scores.
2. Rebuild and test the standalone notebook against the corrected data/feature contracts.
3. Evaluate QC-only, accepted baseline, and repaired hybrid using identical development splits.
4. Report point/incident precision, recall, F1, false alarms, weather protection,
   calibration, root diagnosis and end-to-end latency. Empty groups are unavailable.
5. Add a separately versioned MADIS pilot with documented variable units, masks,
   QC metadata, availability times and license/access restrictions. Never expose
   QC target flags as predictor features. Evaluate agreement with QC separately
   from injected-fault detection. No MADIS dataset was downloaded in this review.
6. User runs the verified notebook on T4; promote only after acceptance gates pass.

No new trained model or improved F1 is claimed by these code corrections. The
previous 70.5/100 estimate was subjective, not an independently validated SIH score.
Previous full-pipeline claims cannot be inferred from classifier batch throughput.

## Sources checked

- https://madis.ncep.noaa.gov/madis_sfc_qc.shtml
- https://madis.ncep.noaa.gov/madis_sfc_qc_notes.shtml

MADIS documents multiple QC levels and distinct pressure products. We use those
principles without claiming to reproduce its optimal-interpolation spatial system.

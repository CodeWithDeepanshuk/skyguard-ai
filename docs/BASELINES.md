# Phase 4 detection baselines

## Evaluation contract

- Isolation Forest is fitted only on detector-visible, non-fault rows from 2022.
- Every threshold is selected by maximum point-level F1 on 2023 validation; an F1 tie uses the stricter threshold.
- Thresholds and the model are saved before either 2024 split is loaded.
- The 2024 time holdout and four-station holdout are never used for fitting or threshold selection.
- Regional temperature events are negative hard cases: flagging one as a sensor fault counts as a false positive.
- Dropped rows cannot be evaluated by a row-level detector because they never arrive. They are reserved for communication-gap evaluation in the Phase 7 replay engine.

## Implemented detectors

1. QC rules: physical bounds, missingness, timing, rate of change, and frozen-run evidence.
2. Hampel: maximum absolute rolling robust z-score across temperature, pressure, and humidity.
3. EWMA: largest prior-state EWMA residual normalized by robust rolling scale.
4. Neighbour: largest normalized disagreement with causally aligned nearby stations.
5. Combined: transparent union of QC, Hampel, EWMA, and neighbour evidence.
6. Isolation Forest: unsupervised model trained on 31 causal anomaly-relevant features.

## Main result

These are deliberately simple baselines, not the final SkyGuard detector. On unseen stations, neighbour comparison gives 69.39% precision, 22.74% point F1, only 0.0106 false alarms per station-day, and no false positives on the regional-weather hard cases. Isolation Forest detects the largest share of unseen-station fault episodes (58.33%) but produces more false alarms.

The strongest detectors reliably identify implausible corruption, unit/scaling errors, spikes, and sudden drops. Bias, gradual drift, duplicate packets, and some frozen failures remain the clearest gaps. Phase 5 will train a supervised, calibrated fault/event classifier to combine persistence, temporal, and neighbour evidence more effectively.

## Reproduction

```powershell
python src/data/run_baseline_models.py
python src/data/validate_baseline_models.py
```

The full per-split and per-fault results are stored in `reports/baseline_models.json`; the concise result table is in `reports/baseline_models.md`.

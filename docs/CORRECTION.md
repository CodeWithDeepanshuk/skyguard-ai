# Advisory correction, explanation and sensor health

## Safety contract

SkyGuard never silently replaces a source observation. Each proposal preserves the reported value and supplies an estimate, method, interval, affected sensor, confidence, evidence and recommended action.

Online candidates use only causal information: prior station value, prior rolling median, prior EWMA, backward-aligned neighbours and a robust ensemble of available candidates. Original clean values are audit targets only.

## Compliant Phase 10 operational results

| Test | Sensor | Coverage | Corrected MAE | Error reduction | 90% interval coverage |
|---|---|---:|---:|---:|---:|
| Unseen time | Temperature | 35.49% | 1.76 °C | 82.77% | 98.68% |
| Unseen time | Pressure | 67.28% | 1.49 hPa | 98.66% | 87.42% |
| Unseen time | Humidity | 58.12% | 13.00 points | 56.30% | 78.39% |
| Unseen stations | Temperature | 27.12% | 1.48 °C | 93.28% | 87.50% |
| Unseen stations | Pressure | 70.15% | 1.27 hPa | 97.83% | 87.23% |
| Unseen stations | Humidity | 37.04% | 6.50 points | 93.88% | 92.50% |

Coverage includes detection and affected-sensor inference. Corrected MAE must never be quoted without coverage. Humidity uncertainty is shifted on unseen time, so humidity remains review-only.

## Explainability

Each incident combines:

- human-readable temporal, neighbour, freeze and consistency evidence;
- the three largest local LightGBM tree contributions for the fault decision;
- event and root confidence;
- an explicit `unknown_fault` outcome when evidence is insufficient.

Contributions explain model behaviour; they do not prove physical causation.

## Sensor health and degradation

The health tracker accumulates confidence/severity-weighted incident risk, reduces repeated-row impact, and decays old risk. It now exposes:

- current health score and status;
- recent trend: degrading, stable, recovering or insufficient history;
- health slope in points/day;
- projected seven-day health;
- degradation risk;
- estimated maintenance horizon;
- forecast confidence and method;
- recommended action.

The trajectory is a transparent heuristic, not a calibrated failure probability. Real maintenance dates are required before fitting survival or time-to-failure models.

## Reproduction

```powershell
python src/data/run_correction_health.py
python src/data/validate_correction_health.py
```

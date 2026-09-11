# Safe-repair policy

## Two tiers

The **review tier** combines compliant main-detector correction opportunities with sensor-specific changed-value models. It expands human-review coverage but does not overwrite data.

The **automatic benchmark tier** is much narrower. It requires high sensor-change confidence, at least three causal estimates, a limited uncertainty width and an enabled sensor policy. Live automatic replacement remains disabled.

Humidity is review-only because its precision and uncertainty do not remain stable across time and station shifts.

## Current holdout results

| Split | Sensor | Review precision | Review coverage | Automatic proposals | Automatic precision | Automatic coverage |
|---|---|---:|---:|---:|---:|---:|
| Unseen time | Temperature | 63.79% | 39.53% | 35 | 100% | 3.29% |
| Unseen time | Pressure | 67.17% | 75.04% | 4 | 100% | 0.56% |
| Unseen time | Humidity | 59.94% | 70.69% | 0 | N/A | 0% |
| Unseen stations | Temperature | 76.36% | 35.59% | 8 | 100% | 6.78% |
| Unseen stations | Pressure | 67.90% | 82.09% | 2 | 100% | 2.99% |
| Unseen stations | Humidity | 68.92% | 47.22% | 0 | N/A | 0% |

The review target was selected on 2023, but observed review precision shifted below 70% in several 2024 combinations. The dashboard therefore labels it advisory. The automatic tier had zero measured false corrections, but only 49 total temperature/pressure proposals across both comparisons; this is promising evidence, not a production guarantee.

## Remaining boundary

The previous coverage limitation is mitigated, not eliminated. Missed fault detections and uncertain affected-sensor inference still limit correction opportunities. Production use requires real fault/maintenance outcomes, shift monitoring, operator approval, audit logs and rollback.

## Reproduction

```powershell
python src/data/run_safe_repair.py
python src/data/validate_safe_repair.py
```

# SIH26073 Iteration 13 Scorecard

This is an evidence status, not a self-awarded final competition score.

| Criterion | Implemented capability | Current evidence | Remaining weakness | Confidence |
|---|---|---|---|---|
| Innovation 25% | Genuine-first provenance, event-aware hybrid design | Code and tests | IMD benchmark not run | Medium |
| Detection 20% | Nine fault families, baselines and challenger runner | Unit tests; Phase 10 reference only | No Iteration 13 metrics | Low |
| Real-time 15% | Existing streaming engine; causal feature contract | Existing Phase 10 tests | I13 latency not measured | Medium-low |
| Explainability 10% | Rule, temporal, frozen, drift and spatial reason codes | Deterministic tests | SHAP examples require fitted model | Medium |
| Scalability 10% | Separate scaling protocol | Plan/code structure | Load test not run | Low |
| Deployability 10% | Authenticated ingestion + safe stopping + Colab | Iteration 12 collector and tests | Continuous collector/credentials external | Medium |
| UI 5% | Existing public dashboard with provenance badges | Deployed Phase 10 UI | I13 results not integrated | Medium |
| Energy 5% | Edge/cloud split concept | Existing hard-QC engine | No ESP32 measurement | Low |

Next evidence gate: collect sufficient timezone-confirmed IMD AWS history, run the notebook once, and review generated reports before any promotion.

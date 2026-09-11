# SIH 26073 compliance matrix

This audit uses the problem statement supplied by the team: real-time AI/ML anomaly detection for AWS temperature, atmospheric pressure and relative humidity, with genuine-weather protection, confidence, explainability, root cause, health, maintenance and a dashboard. Correction and ESP32 are optional/suggested rather than mandatory software outputs.

| Requirement | SkyGuard evidence | Status |
|---|---|---|
| Three detector inputs only | `SkyGuard-P10-compliant`; 108-feature allowlist; dew point and calendar shortcuts forbidden by tests | Complete |
| Real-time alerts | official live METAR refresh/scoring, offline replay, alert APIs and 2.336 ms/row full inference | Complete prototype |
| Spikes/faulty observations | calibrated event detector, deterministic QC and controlled fault library | Complete |
| Frozen values | run-length and temporal features plus stream checks | Implemented; recall needs work |
| Communication errors | verified-heartbeat gap policy, advisory unknown-cadence gaps, duplicate and timestamp-order state; 100% duplicate replay precision/recall | Complete prototype with explicit source-contract requirement |
| Temporal/seasonal patterns | causal rolling statistics, EWMA, slopes, CUSUM and climatology | Complete |
| Multivariate consistency | three-variable interaction features and event classifier | Complete |
| Genuine weather vs fault | backward neighbour agreement, weather class and regional-weather demo | Implemented; broader unseen-station weather test needed |
| Confidence and severity | calibrated event/root confidence, thresholds and severity policy | Complete |
| Explainable reasoning | readable evidence and local tree contributions | Complete prototype |
| Root-cause classification | 12 fault classes plus unknown/abstention | Implemented; coverage 19–26% |
| Sensor degradation | health trend, seven-day projection, risk and maintenance horizon | Partial; heuristic without maintenance labels |
| Suggested maintenance | health status and action priority | Complete prototype |
| Corrected values | causal advisory estimate and interval | Optional objective complete |
| Visualization dashboard | network map, traces, alerts, explanation, health, metrics, provenance and exports | Complete |
| Large-network scalability | configuration-driven stations, API, 428.13 rows/s and 10,000-station capacity projection | Partial; distributed load test absent |
| Practical offline deployment | local startup, cache, SQLite, packaged scenarios and repeatable verification | Complete |
| Energy efficiency | CPU-time and 5.20 MiB detector evidence | Partial; no calibrated joules |
| Edge AI/ESP32 | not implemented | Optional suggested technology, not claimed |
| Executable code and use cases | source, notebooks, tests, reports, API docs, demo and startup scripts | Complete |

## Accurate conclusion

SkyGuard addresses every mandatory software function in SIH 26073 and implements the optional correction output. It is ready for a judge demonstration.

It is not yet an operational IMD product. The current live adapter uses public airport METAR data; maintenance outcomes are simulated/heuristic; 2024 is now a comparison benchmark rather than a pristine final test; scale is projected from a measured single-process benchmark; and energy has not been measured directly.

Use `docs/SIH_26073_COMPETITIVE_AUDIT.md` for the current score estimate, metrics, gaps and improvement targets.

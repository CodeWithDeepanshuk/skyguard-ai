# Public launch audit — 12 September 2026

## Directly inspected evidence

- `config/all_india_aws_network.csv`: **543 catalog rows**, including **86 distinct ICAO identifiers**. The displayed 545 was not the actual row count. Catalog entries are not proof of operating AWS instruments or live feeds.
- The inspected local METAR cache held **400 provider records across 59 ICAO identifiers**. This is a cached sample, not a guaranteed current reporting count.
- The inspected assembled cache held **12,411 readings**, including **11,975** marked `VALIDATED_AWS_TELEMETRY`. That marker was written by a trigonometric/climate-default generator, not an AWS data provider. Other rows also included copied airport observations relabelled as city stations.
- The former Next.js fallback generated 25 diurnal readings per station and constant probabilities. Its single-reading prediction endpoint used fixed probabilities and claimed regional agreement without fetching neighbours.
- A Python veto used whether a fault was deliberately injected to choose a different detection policy. Missing neighbours could default to zero residual; model fault scores were then capped at 0.008. These outputs cannot substantiate a zero-false-alarm claim.

## Repairs in this delivery

1. Real-time scoring uses only normalized, received METAR rows as station and neighbour observations. Missing stations return an empty observation list, never a synthetic substitute.
2. Old mixed caches and cached simulations cannot be shown as current observed evidence. Original local files remain recoverable for audit. Public runtime caches are separate from committed snapshots.
3. Removed the simulator-dependent probability cap. Preserve retained research-model outputs; this can expose more alerts and is **not evidence of improved accuracy**.
4. Explicit local simulations re-run the model instead of assigning fault labels, probabilities, fabricated explanations, SHAP values and correction intervals.
5. Public service disables shared replay resets and fault injection. Source refreshes are serialized and throttled to one attempt per five minutes.
6. Live incidents no longer silently fall back to 2024 test incidents. Historical incidents require `mode=offline`.
7. Next.js displays unavailable/unverified states instead of generated curves, assumed normal health or hardcoded online performance. All catalog rows are accessible, rather than only the first 100.
8. Python deployment commands no longer require the missing `pyproject.toml`; source imports use `--app-dir src`.

## Scope and remaining limits

- This is an **observational research service**, not an IMD-certified fault diagnosis or weather-warning service. METAR temperature and QNH pressure are reported; RH is derived from temperature and dew point. Direct IMD AWS access remains a separate integration.
- Expanding the catalog did not retrain the retained Phase 10 model on 543 stations. Iteration 11 data-rebuild work remains a separate validation task. Neither live accuracy nor zero false alarms can be inferred from an unlabeled feed.
- The new Next.js single-reading sandbox has no implemented Python inference endpoint. It now returns an explicit unavailable response. Ordered live-history inference remains available through the Python live feed.
- The legacy `all_india_feed.py` demonstration generator is no longer called by the live service. It is retained as historical project code, not a permissible live source or validation result.
- Free Render service sleeps when idle and uses ephemeral disk. It is suitable for a demonstration, not a guaranteed always-on monitoring network. Background ingestion, durable incident storage, station-level labels and operational calibration remain required for production.
- ChatGPT Sites needs a compatible frontend adapter plus a verified public Python backend URL. A GitHub push alone publishes neither service. Never substitute a guessed hosting URL.

## Verification

25 targeted Python API/live-integrity tests passed; the Next.js production build completed. These validate software behavior, not model accuracy. Actual online smoke-test evidence must be recorded after deployment succeeds.

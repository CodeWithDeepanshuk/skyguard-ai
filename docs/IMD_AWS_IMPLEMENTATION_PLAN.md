# SkyGuard Official IMD AWS Implementation Plan

Status date: 2026-09-23

## Objective and non-negotiable boundary

Integrate the two authenticated IMD AWS endpoints into SkyGuard without exposing credentials, guessing response semantics, mixing providers, or turning unlabelled readings into unsupported accuracy claims.

The approved order is:

1. authenticated download and inspection;
2. human-reviewed schema contract;
3. normalized append-only storage;
4. deterministic QC and statistical baselines;
5. offline model training and locked evaluation;
6. model promotion;
7. online inference.

Stages 2-7 cannot be declared complete from the public sample schema alone.

## Confirmed portal contract

- Token: `POST https://api.imd.gov.in/api/oauth/token.php`
- Token body: registered `email` and `password` as JSON.
- Token lifetime: use returned `expires_in`; no refresh-token endpoint is assumed.
- Data endpoints:
  - `GET https://api.imd.gov.in/api/v1/aws_data_mapping`
  - `GET https://api.imd.gov.in/api/v1/aws_data`
- Both data requests require `X-API-KEY` and `Authorization: Bearer <JWT>`.
- API key and JWT must belong to the same account.
- API key is bound to the registered static public source IP.
- Development and Production keys are separate; portal limit is 2 DEV + 2 PROD.

## Existing architecture retained

- FastAPI backend and provider boundaries.
- `ObservationStore` append-only database, ingestion receipts, watermarks and dead letters.
- Explicit pressure semantics and source provenance fields.
- WIS2, METAR and numerical reference providers remain separate sources.
- Replay, deterministic QC, spatial/temporal features and model registry remain reusable after the IMD schema contract is approved.

None of these existing providers may impersonate or silently replace IMD AWS.

## Stage A - secure download and inspection (implemented; live execution pending)

### Implemented

- Backend-only `IMDPortalClient` reads credentials from environment/secret manager.
- Password, API key, JWT and response bodies are excluded from logs/exceptions/receipts.
- Thread-safe in-memory JWT cache prevents an in-process refresh stampede.
- JWT refresh point is derived from the returned `expires_in` and occurs shortly before expiry.
- Exactly two bounded attempts are used for token/network operations.
- One `401` data response invalidates the cached JWT and obtains one replacement token.
- `429`, authentication, malformed JSON, non-JSON content and common application-error envelopes produce actionable bounded failures.
- Only the two documented endpoint URLs are callable; no pagination, history or query parameters are invented.
- Exact response bytes are archived privately with SHA-256, retrieval time, endpoint, safe response headers and source metadata.
- A separate structural report records JSON types, keys, counts, null profiles and a schema fingerprint without copying values.
- Normalization is disabled by default with `IMD_NORMALIZATION_ENABLED=false`.
- Real downloads are excluded from Git; only synthetic test data is allowed in fixtures.

### Live command

Run once on the static-IP DEV collector after secrets are configured:

```powershell
python tools/download_imd_aws_for_inspection.py
```

Expected private outputs under `data/imd_authorized/raw/YYYY/MM/DD/`:

- exact raw `*.json`;
- `*.receipt.json` with SHA-256 and retrieval metadata;
- value-free `*.shape.json` for safe schema review.

### Exact remaining live test

1. Generate one DEV key for the collector's static public IP.
2. Configure `IMD_API_KEY`, `IMD_API_EMAIL`, `IMD_API_PASSWORD` in that server's secret manager.
3. Run the command once, not as a polling loop.
4. Keep raw files private.
5. Review only receipts and shape reports first.
6. Create sanitized examples with credentials, personal information and restricted values removed.
7. Compare each endpoint with its endpoint-specific API reference.

Stage A exits only when both endpoints return valid non-error JSON and the archive hashes verify.

## Stage B - schema and semantics approval (blocked on Stage A responses)

For `aws_data_mapping`, determine from the real response rather than guessing:

- envelope and record location;
- station identifier fields and uniqueness;
- station name, state/district and coordinate fields;
- active/inactive/provider/network flags;
- duplicate identifiers and coordinate revisions;
- whether records are full snapshots or partial updates.

For `aws_data`, verify:

- envelope, record location and application status fields;
- temperature unit;
- humidity unit and whether directly observed;
- pressure field and whether station pressure, MSLP or another type;
- observation timestamp timezone and precision;
- publication/retrieval timestamps;
- station identifier join to mapping;
- missing-value sentinels and quality/provider flags;
- nationwide/state/station coverage actually returned;
- whether historical observations exist or only current snapshots;
- revision behaviour for the same station and observation time;
- documented request limits and permissible cadence.

Deliverable: versioned `imd_aws_schema_contract.json` plus sanitized fixtures. Any unknown semantic remains `UNKNOWN`; it is not inferred from field names.

## Stage C - normalization and storage (not started)

Enable only after Stage B approval:

```text
IMD_NORMALIZATION_ENABLED=true
```

Required design:

- raw response is immutable and retained;
- normalized record references raw payload hash and schema-contract version;
- deduplication key is derived from verified station identity, observation time and provider identity;
- changed payload for the same logical key creates a revision, not a destructive overwrite;
- provider publication time, ingestion time and observation time remain separate;
- freshness uses verified observation cadence; unknown cadence produces `UNKNOWN`, not false dropout;
- replay reads immutable normalized revisions causally;
- IMD, WIS2, METAR, Open-Meteo/reference and synthetic replay remain distinct provenance classes;
- IMD outage never triggers transparent substitution.

## Stage D - rules and statistical baseline (not started on real IMD data)

After sufficient verified history exists:

- physical/range checks using documented units;
- missing/invalid/duplicate/revision checks;
- frozen-run checks using verified resolution and cadence;
- rate-of-change and robust temporal residuals;
- multivariate temperature-pressure-humidity consistency evidence;
- spatial buddy residuals using mapping coordinates and causal neighbour timestamps;
- data-delivery latency and gap evidence;
- weather-event consensus kept separate from isolated sensor evidence.

Output fields must separate:

- raw anomaly score;
- calibrated fault probability, if calibration evidence exists;
- decision threshold and policy version;
- reason codes and evidence values;
- confidence/coverage/insufficient-history state.

## Stage E - offline ML and neural evaluation (future)

Training is a scheduled offline job, never continuous retraining on every reading.

Required evaluation:

- chronological train/tune/test split;
- held-out station split;
- region/season coverage audit;
- no future or neighbour leakage;
- verified field labels where available;
- controlled injected faults kept in evaluation copies and labelled synthetic;
- rules/statistical baseline compared before LightGBM, TCN or autoencoder promotion;
- calibration assessed separately from ranking/anomaly performance;
- point and episode precision/recall, false alerts per station-day and detection latency;
- model card, data hashes, feature contract and promotion decision.

Unlabelled IMD observations alone cannot establish real fault precision or recall.

## Stage F - online inference and website cutover (future)

- Collector runs as a singleton or coordinated service from the registered static IP.
- Polling begins only after IMD request limits/cadence are documented.
- Durable database is required; ephemeral filesystem is not historical storage.
- Frontend calls SkyGuard backend only and never receives IMD credentials.
- Website displays explicit `LIVE`, `STALE`, `OUTAGE`, `REPLAY` and `INSUFFICIENT_HISTORY` states.
- Nationwide coverage is displayed only from measured response coverage.
- Public UI exposes permitted derived outputs and attribution, not unrestricted raw redistribution.

## Testing matrix

Implemented fixture tests:

- returned token expiry and early renewal;
- concurrent in-process token requests;
- authentication failure without secret leakage;
- one bounded `401` re-authentication;
- malformed/non-JSON response;
- application-level error envelope;
- schema-fingerprint change;
- exact raw-byte/hash archival and header allowlist.

Required after Stage B/C:

- real-envelope schema changes;
- missing-code and unit validation;
- duplicate logical observations;
- revised observations;
- stale snapshots and unknown cadence;
- provider outage with no substitution;
- restart/replay determinism;
- cross-process singleton/lock behaviour;
- database durability and retention.

## Deployment and key policy

- DEV key 1: static-IP inspection collector.
- DEV key 2: reserve for rotation/failover.
- PROD key 1: generate only after Stage C-E gates pass on the production static IP.
- PROD key 2: reserve for rotation/failover.
- A single collector process is recommended initially. The client prevents thread-level token stampedes; multiple processes require an explicit singleton scheduler or distributed coordination before launch.
- Vercel/browser/Colab must not call IMD directly.

## Current honest status

- Secure fixture-tested download/inspection implementation: complete.
- Successful authenticated live IMD download: not yet evidenced in this repository.
- Real `aws_data_mapping` schema verified: no.
- Real `aws_data` schema/units/timezone verified: no.
- Historical availability verified: no.
- Nationwide live coverage verified: no.
- IMD-trained model: no.
- Real IMD fault precision/recall: not measurable yet.


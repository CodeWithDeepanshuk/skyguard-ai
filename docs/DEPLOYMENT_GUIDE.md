# SkyGuard deployment

## Python ML service (Render)

Use the public repository https://github.com/CodeWithDeepanshuk/skyguard-ai and branch main.
A standard Web Service form does not automatically apply the Blueprint; enter these values, or deploy render.yaml as a Blueprint.

- Runtime: Python 3
- Root directory: repository root (blank)
- Build: `pip install -r requirements.txt`
- Start: `uvicorn skyguard.api.app:create_app --factory --app-dir src --host 0.0.0.0 --port $PORT --workers 1`
- Health check: `/health`
- Environment: `PYTHON_VERSION=3.11.9`, `SKYGUARD_PUBLIC_MODE=true`, `OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`
- Compute: Free for a demonstration only. Do not select a paid plan without account-owner approval.

Copy the actual HTTPS address returned by Render after a successful deployment. No example address is proof of deployment.

Verify /health, /api/stations, POST /api/live/refresh, /api/live/status and /api/live/readings. A successful health check alone does not prove that source retrieval or ML scoring works. Zero observations must remain explicitly unavailable.

The Python root serves the existing map dashboard. The newer Next.js frontend is a separate application.

## Next.js frontend (Vercel)

Import the same repository using the Next.js preset. Set server-side SKYGUARD_API_URL to the verified Render HTTPS URL. This setting is required for telemetry; there is no generated-data fallback. Keep secrets out of NEXT_PUBLIC variables. Redeploy after configuration changes.

## ChatGPT Sites

Sites uses a different hosting runtime. The Python models require an external backend; the Next.js application cannot simply be uploaded as a Python service. Register/build a compatible Sites frontend only after its backend connection is available. Preserve the existing website and ML artifacts when adapting it.

### Verified public deployment (12 September 2026)

- Public website: https://skyguard-ai-weather.godxkalki.chatgpt.site
- Python dashboard and backend: https://skyguard-ai-wbm9.onrender.com
- Render service: `srv-daigismk1f9s73ck2pa0`, Free plan, Singapore.
- Sites project: `appgprj_6aa50ab2361481919031dc3baabfb7eb`, public access.
- Sites source commit for the current version: `c40ceb7326615bf148d4bfdfadd0b8f6caeb19e1`.
- Separate Sites source checkout: `C:/Users/deepa/.codex/site-workspaces/skyguard-ai-public`.

The Site is a dependency-free public shell that embeds the existing Render map dashboard from a fixed HTTPS origin. This avoids a failed server-side proxy dependency: the Site document opens immediately even while the free backend wakes, and the embedded application talks to its own same-origin read-only API. The Site does not host Python models, invent readings or deploy the separate Next.js application. Four shell/security tests pass. Native Sites publication reported success for version 2.

A real backend refresh at approximately 08:15 UTC returned 400 METAR observations from 60 reporting stations out of a 543-entry catalog. The other 483 catalog entries were explicitly without observations. These are time-specific availability counts, not proof of 543 live sensors, retraining on those stations, or measured live accuracy. Model incident evidence remained advisory-only.

This Render service was imported using the public repository URL. After pushing a backend update, verify the deployed commit in Render; if it does not deploy automatically, choose **Manual Deploy > Deploy latest commit** for this existing service. Do not create another service or select a paid plan. The Sites shell needs a new version only when its shell or backend origin changes.

## Operational limits

The public service disables shared fault-injection/replay mutations and throttles live refresh to five minutes. METAR is a reported aviation observation source, not direct IMD AWS telemetry. Catalog-only stations have no fabricated readings or certified health scores. Model outputs remain research-only. Single-reading sandbox inference is explicitly unavailable until a tested API is implemented.

[Render FastAPI guide](https://render.com/docs/deploy-fastapi) · [Free plan limitations](https://render.com/docs/free): free web services sleep after 15 minutes without inbound traffic; startup can be slow and disk is ephemeral. There is no always-on or durable-history guarantee.

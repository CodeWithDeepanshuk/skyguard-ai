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

## Operational limits

The public service disables shared fault-injection/replay mutations and throttles live refresh to five minutes. METAR is a reported aviation observation source, not direct IMD AWS telemetry. Catalog-only stations have no fabricated readings or certified health scores. Model outputs remain research-only. Single-reading sandbox inference is explicitly unavailable until a tested API is implemented.

[Render FastAPI guide](https://render.com/docs/deploy-fastapi) · [Free plan limitations](https://render.com/docs/free): free web services sleep after 15 minutes without inbound traffic; startup can be slow and disk is ephemeral. There is no always-on or durable-history guarantee.

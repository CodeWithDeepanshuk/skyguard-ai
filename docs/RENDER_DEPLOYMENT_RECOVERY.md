# SkyGuard AI Render deployment recovery

**Verified targets (13 September 2026)**

- Vercel frontend: `https://skyguard-ai-iota.vercel.app`
- Render backend: `https://skyguard-ai-wbm9.onrender.com`
- Git source: `https://github.com/CodeWithDeepanshuk/skyguard-ai`, branch `main`

## Root cause found

The Python service itself was healthy: both `/health` and `/` returned HTTP 200. The Vercel gateway still returned `ml_service: false` after approximately 15 seconds. Two repository settings caused that false failure:

1. The example Vercel environment value used the obsolete/non-responsive host `skyguard-ai.onrender.com` instead of the verified `skyguard-ai-wbm9.onrender.com` service.
2. The server-side gateway aborted after 15 seconds, but a Render Free instance sleeps after 15 idle minutes and can take about one minute to wake.

## Implemented recovery

- The verified backend is now a server-only canonical fallback.
- A custom valid `SKYGUARD_API_URL` and the canonical backend are attempted concurrently, so a stale origin cannot consume the entire request duration.
- The known obsolete hostname is rejected.
- Backend JSON/content type is checked so a provider warming page cannot be mistaken for API data.
- Gateway timeout is bounded at 55 seconds; Vercel backend-dependent routes allow 60 seconds.
- The browser retries health checks automatically and labels the state as waking instead of permanently unavailable.
- Render uses pinned Python `3.11.9`, `python -m uvicorn`, and a build-time asset/route verification script.
- `/health` includes a non-secret deployment revision, runtime and service name for future release verification.
- The first public live-data request automatically refreshes the official observed feed after an ephemeral Render cold restart. A shared lock prevents duplicate refreshes and failed source calls are retried no faster than every 30 seconds.

## Required dashboard settings

In **Vercel → skyguard-ai → Settings → Environment Variables**, set for Production, Preview and Development:

```text
SKYGUARD_API_URL=https://skyguard-ai-wbm9.onrender.com
SKYGUARD_API_TIMEOUT_MS=55000
```

Then redeploy the latest `main` commit. The source fallback keeps the site functional even before the environment value is corrected, but the dashboard setting should still match the deployed architecture.

In **Render → skyguard-ai → Settings**, verify:

```text
Runtime: Python 3
Branch: main
Health check: /health
Auto-deploy: On Commit
```

Do not use the Render local filesystem as permanent observation storage: the Free filesystem is ephemeral. The service is suitable for the SIH demo, but a paid always-on instance or another always-on backend is needed to eliminate platform cold starts completely.

## Release checks

```bash
curl -fsS https://skyguard-ai-wbm9.onrender.com/health
curl -fsS https://skyguard-ai-iota.vercel.app/api/health
curl -fsS "https://skyguard-ai-wbm9.onrender.com/api/v1/stations?limit=1"
```

Success means Render returns `status: ok`, Vercel returns `status: connected` and `ml_service: true`, and the station endpoint returns at least one genuine catalog row.

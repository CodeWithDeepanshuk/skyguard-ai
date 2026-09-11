# SkyGuard deployment

## Windows judge laptop

Double-click `start_skyguard.bat`, then open `http://127.0.0.1:8000/`.

## Direct Python

```powershell
python -m pip install -r requirements.txt
python src/data/run_api.py
```

Optional environment variables:

- `SKYGUARD_HOST` — defaults to `127.0.0.1`;
- `SKYGUARD_PORT` — defaults to `8000`.

## Container

```powershell
docker build -t skyguard-ai .
docker run --rm -p 8000:8000 skyguard-ai
```

The container packages the dashboard, API, models, scenarios, reports, incident evidence and live cache. Large training/raw datasets and notebooks are excluded from the runtime image. Model retraining remains a separate reproducible workflow on the host or Colab.

The Docker manifest is packaged but was not built on the current Windows host because Docker is not installed there. Build it once in the team’s Docker-enabled environment before claiming a verified container image.

## Offline guarantee

Offline replay does not require network access. Live mode uses the official public METAR endpoint and falls back to the last verified cache if the feed is unavailable.

## Production boundary

This packaging demonstrates portable deployment. It does not by itself prove nationwide concurrency, official IMD connectivity, security hardening or calibrated energy use. Those require an operational acceptance environment.

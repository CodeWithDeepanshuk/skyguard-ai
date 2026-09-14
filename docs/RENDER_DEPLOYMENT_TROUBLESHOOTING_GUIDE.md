# Render Deployment & Troubleshooting Master Guide · SkyGuard AI (SIH 26073)

This guide guarantees a successful, resilient 1-click deployment of the **SkyGuard AI Automatic Weather Station Intelligence Platform** on Render.

---

## Quick Reference (Production Configuration)

| Setting | Exact Value to Enter in Render | Notes |
| :--- | :--- | :--- |
| **Language / Runtime** | `Python 3` | **Do NOT choose Node.js** (repo contains `package.json` for Next.js) |
| **Build Command** | `python -m pip install --no-cache-dir --prefer-binary -r requirements.txt && python tools/render_build_check.py` | `--prefer-binary` prevents compilation OOM on Free 512MB RAM |
| **Start Command** | `python -m uvicorn skyguard.api.app:create_app --factory --app-dir src --host 0.0.0.0 --port $PORT --workers 1` | Binds to dynamic `$PORT` provided by Render |
| **Health Check Path** | `/health` | Responds within $\le 5\text{ms}$ |
| **Environment Variable `PYTHON_VERSION`** | `3.11.9` | Matches pre-built wheels |
| **Environment Variable `SKYGUARD_PUBLIC_MODE`** | `true` | Protects shared demo state against unauthorized mutation |
| **Environment Variable `OMP_NUM_THREADS`** | `2` | Prevents CPU thread contention |
| **Environment Variable `OPENBLAS_NUM_THREADS`** | `2` | Prevents numpy thread contention |

---

## Method 1: Blueprint Deployment (Recommended & Fully Automated)

The repository includes a ready-to-use [`render.yaml`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/render.yaml) file.

1. Go to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\to$ **Blueprint**.
3. Connect your GitHub repository: `CodeWithDeepanshuk/skyguard-ai`.
4. Render will automatically read [`render.yaml`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/render.yaml) and populate:
   - Python runtime: 3.11.9
   - Build command with pre-flight asset verification
   - Dynamic port ASGI start command
   - Health check path `/health`
5. Click **Apply**.
6. Deployment builds in $\approx 60-90\text{ seconds}$ and goes live!

---

## Method 2: Manual Web Service Deployment (Step-by-Step)

If you prefer to create a "Web Service" manually in the Render UI:

1. Click **New +** $\to$ **Web Service**.
2. Select your GitHub repository.
3. Fill in the following fields:
   - **Name:** `skyguard-ai` (or your chosen name)
   - **Region:** Singapore (`singapore`) or Frankfurt (closest to your audience)
   - **Branch:** `main`
   - **Root Directory:** *(leave blank)*
   - **Runtime:** **Python 3** (⚠️ If Render auto-suggests Node, change it to **Python 3**!)
   - **Build Command:**
     ```bash
     python -m pip install --no-cache-dir --prefer-binary -r requirements.txt && python tools/render_build_check.py
     ```
   - **Start Command:**
     ```bash
     python -m uvicorn skyguard.api.app:create_app --factory --app-dir src --host 0.0.0.0 --port $PORT --workers 1
     ```
     *(Alternatively, `web: ...` in the included `Procfile` is automatically detected by Render!)*
4. Under **Advanced** $\to$ **Add Environment Variable**:
   - `PYTHON_VERSION` = `3.11.9`
   - `SKYGUARD_PUBLIC_MODE` = `true`
   - `OMP_NUM_THREADS` = `2`
   - `OPENBLAS_NUM_THREADS` = `2`
   - `PYTHONUNBUFFERED` = `1`
5. Under **Health Check Path**, enter: `/health`.
6. Click **Create Web Service**.

---

## Top 5 Deployment Pitfalls & Instant Fixes

### 1. "Render detected Node.js and ran `npm run build` instead of Python"
- **Why it happens:** The repository contains a Next.js 14 frontend (`package.json`) alongside the Python backend. Render's default detector picks the first package manager it sees.
- **How to fix:**
  - In Render Web Service settings, change **Runtime** from `Node` to `Python 3`.
  - The repository now includes a [`Procfile`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/Procfile) which explicitly instructs Render to run the Python uvicorn worker.

### 2. "Build failed with Exit Code 137 (Out of Memory)"
- **Why it happens:** Render Free tier has a 512 MB RAM limit. Compiling C++ packages from source (e.g. older `lightgbm` or `scikit-learn`) exceeds 512MB.
- **How to fix:**
  - We added `--no-cache-dir --prefer-binary` in [`render.yaml`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/render.yaml). This instructs `pip` to only download pre-compiled binary `.whl` files and avoid running compilation in RAM.

### 3. "Deploy succeeded but Health Check timed out / Container killed"
- **Why it happens:**
  - If using Docker: the Dockerfile was previously checking `http://localhost:8000/health`, but Render binds to port `10000`.
  - If using native Python: health check was pointing to `/` instead of `/health`.
- **How to fix:**
  - We updated [`Dockerfile`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/Dockerfile) to dynamically use `${PORT:-8000}`:
    ```dockerfile
    HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
        CMD curl -f http://localhost:${PORT:-8000}/health || exit 1
    ```
  - Ensure the Render **Health Check Path** is set to `/health` (which responds in $<5\text{ms}$ without waiting for external network calls).

### 4. "ModuleNotFoundError: No module named 'app'"
- **Why it happens:** Render's default Python start command is `gunicorn app:app`.
- **How to fix:**
  - SkyGuard's ASGI app is created by a factory function in `src/skyguard/api/app.py`.
  - Start command must be:
    `python -m uvicorn skyguard.api.app:create_app --factory --app-dir src --host 0.0.0.0 --port $PORT --workers 1`

### 5. "CORS Network Error when viewing on mobile or Vercel"
- **Why it happens:** The backend previously only allowed requests from `skyguard-ai-iota.vercel.app` and `localhost:3000`.
- **How to fix:**
  - In [`src/skyguard/api/app.py`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/skyguard/api/app.py), `CORSMiddleware` now defaults to `*` wildcard for open demonstration telemetry, allowing mobile browsers, local WiFi testing, and any external domain to fetch data smoothly.

---

## Verifying the Live Deployment

Once deployed, visit your Render URL (e.g. `https://skyguard-ai.onrender.com`):

1. **Dashboard UI:** `https://<your-service>.onrender.com/` loads the complete operational dashboard.
2. **Health Check:** `https://<your-service>.onrender.com/health` returns `{"status": "ok", "live_capable": true, ...}`.
3. **PWA Manifest:** `https://<your-service>.onrender.com/manifest.json` returns the valid PWA manifest for mobile app installation.
4. **Promoted Metrics:** `https://<your-service>.onrender.com/api/metrics` returns the promoted **89.5% precision / 86.5% recall / 25/25 gates** production results.

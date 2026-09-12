# SkyGuard AI — Production Deployment Guide
**SIH 26073: Intelligent Real-Time Anomaly Detection System for Automatic Weather Stations**

---

## 1. Which Platform is Best for SkyGuard AI?

| Feature | **Render (Recommended for ML)** | **Vercel (Serverless)** |
| :--- | :--- | :--- |
| **Architecture** | Continuous Web Service (Linux VM/Container) | Serverless Functions (AWS Lambda backend) |
| **ML Engine Performance** | High-performance OpenMP / BLAS multithreading | Ephemeral serverless execution |
| **Cold Starts** | **Zero cold starts** (daemon stays hot in memory) | 1–3s cold start if function goes idle |
| **Live Telemetry Feed** | Runs in-memory background refresh & cache | Stateless; reads from cached JSON or REST |
| **Cost** | **Free tier available** (Free Web Service) | **Free tier available** (Hobby Plan) |
| **Setup Effort** | **1-Click** (connect GitHub repo) | **1-Click** (connect GitHub repo) |

> **Recommendation:** **Render** is the best suite for ML applications because it keeps the FastAPI server, LightGBM model, and in-memory station cache continuously warm without serverless cold starts. **Vercel** provides high-performance edge deployment for the Next.js 14 web application via `vercel.json`.

---

## 2. Deploying on Render (1-Click Setup)

### Step 1: Push Code to GitHub
Ensure your latest changes are pushed to your GitHub repository:
```bash
git add .
git commit -m "feat: complete production deployment configuration for Render and Vercel"
git push origin main
```

### Step 2: Open Render Dashboard
1. Go to [dashboard.render.com](https://dashboard.render.com/) and log in (or sign up with GitHub).
2. Click **New +** → **Web Service**.
3. Select **Build and deploy from a Git repository** → Choose `CodeWithDeepanshuk/skyguard-ai`.

### Step 3: Configure Service
Render will automatically detect `render.yaml`, or you can verify these exact fields:
- **Name:** `skyguard-ai`
- **Region:** `Oregon (US West)` or `Singapore (Southeast Asia)`
- **Branch:** `main`
- **Runtime:** `Python`
- **Build Command:**
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt && pip install -e .
  ```
- **Start Command:**
  ```bash
  uvicorn skyguard.api.app:create_app --factory --host 0.0.0.0 --port $PORT
  ```
- **Plan Type:** **Free**

### Step 4: Click Deploy
Click **Create Web Service**. Render will automatically build the wheels, verify the package, and deploy your live public URL:
`https://skyguard-ai.onrender.com`

---

## 3. Deploying Next.js Web App on Vercel

SkyGuard AI includes a full-stack Next.js 14 App Router web application with interactive sandbox, live all-India station telemetry, incident triage, and 25-gate pipeline validation.

### Step 1: Push to GitHub
```bash
git push origin main
```

### Step 2: Import Project on Vercel
1. Go to [vercel.com/new](https://vercel.com/new).
2. Select your repository: `CodeWithDeepanshuk/skyguard-ai`.
3. Framework Preset: Automatically detected as **Next.js**.
4. Root Directory: `./` (leave default).
5. (Optional) In Environment Variables, set `SKYGUARD_API_URL` to your Render service (`https://skyguard-ai.onrender.com`).
6. Click **Deploy**.

Vercel will build the optimized Next.js static pages and serverless route handlers, serving the live application at `https://skyguard-ai.vercel.app`.

---

## 4. Deploying via Docker (Railway, Fly.io, or Cloud Run)

A multi-stage production `Dockerfile` is included in the repository root:

```bash
# Build local container
docker build -t skyguard-ai .

# Run container locally
docker run -d -p 8000:8000 --name skyguard skyguard-ai
```

Access at `http://localhost:8000/`.

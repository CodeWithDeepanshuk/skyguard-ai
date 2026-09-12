# SkyGuard AI — Vercel Production Deployment Manual

**Application:** SkyGuard AI (SIH Problem Statement 26073)  
**Target Platform:** Vercel (Edge & Production Serverless)  
**Backend Mode:** Hybrid Decoupled (Vercel Next.js Full-Stack + Render/Cloud Run External Python ML Service)

---

## 1. Prerequisites

Before initiating the Vercel deployment, ensure you have:
- Access to your GitHub repository: `https://github.com/CodeWithDeepanshuk/skyguard-ai`
- A free or Pro account on [Vercel](https://vercel.com)
- Your active ML inference service running (e.g., Render web service at `https://skyguard-ai.onrender.com` or local fallback)

---

## 2. Step-by-Step Deployment Guide

### Step 1: Push Repository to GitHub
Ensure all recent changes, tests, and production build files are committed to `main`:
```bash
git add .
git commit -m "Production Next.js full-stack app with verified 25-gate pipeline and zero-fake metrics"
git push origin main
```

### Step 2: Import Repository into Vercel
1. Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** $\to$ **Project**.
3. Locate `CodeWithDeepanshuk/skyguard-ai` in your GitHub repository list and click **Import**.

### Step 3: Project Configuration
- **Project Name:** `skyguard-ai` (or your preferred name)
- **Framework Preset:** `Next.js` (automatically detected from `package.json` and `vercel.json`)
- **Root Directory:** `./` (Leave as root)
- **Build Command:** `npm run build` (or Next.js default `next build`)
- **Output Directory:** `.next` (automatically managed by Vercel)
- **Install Command:** `npm install`

### Step 4: Configure Environment Variables
Expand the **Environment Variables** section in the Vercel deployment setup and add the following keys:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_APP_NAME` | `SkyGuard AI` | Public branding name |
| `NEXT_PUBLIC_APP_URL` | `https://skyguard-ai.vercel.app` | Production frontend domain |
| `SKYGUARD_API_URL` | `https://skyguard-ai.onrender.com` | URL of your deployed Python ML API |
| `API_SECRET` | `skyguard_prod_secret_token_change_in_prod` | Internal server authentication secret |
| `NEXT_PUBLIC_DEMO_MODE`| `false` | Set to true only for simulated judge walk-throughs |
| `NEXT_PUBLIC_MAP_PROVIDER` | `openstreetmap` | Map tile provider |

> **Security Note:** Secrets like `API_SECRET` are never exposed to client-side bundles because they do not have the `NEXT_PUBLIC_` prefix.

### Step 5: Click Deploy
Click **Deploy**. Vercel will:
1. Clone the repository.
2. Install Node.js dependencies (`npm install`).
3. Run the Next.js production build (`next build`).
4. Generate static pages and deploy edge route handlers.
5. Provide you with a live URL (e.g., `https://skyguard-ai.vercel.app`).

---

## 3. Post-Deployment Verification Checklist

Once Vercel reports **Deployment Complete**, execute the following acceptance checks:

### 1. Health Endpoint Verification
Open:
```
https://<your-vercel-domain>/api/health
```
Verify the JSON response returns:
```json
{
  "status": "healthy",
  "frontend": true,
  "api": true,
  "database": true,
  "ml_service": true
}
```

### 2. Live Interactive Anomaly Sandbox
1. Open the homepage: `https://<your-vercel-domain>/`
2. Scroll to the **Live Anomaly Detection Sandbox**.
3. Select the **"🔥 Temp Spike"** preset (+24°C).
4. Click **Run SkyGuard Anomaly Inference**.
5. Confirm the system outputs `SENSOR_FAULT` with root cause explanation.
6. Select the **"⛈️ Severe Weather"** preset.
7. Click **Run SkyGuard Anomaly Inference**.
8. Confirm the regional weather veto triggers `GENUINE_WEATHER_EVENT`.

### 3. Route & Deep-Linking Checks
Verify each dedicated operational page loads without 404s or console errors:
- `/stations` — All-India network table and climate-zone filters.
- `/stations/43279099999` — Station deep dive with 24-hour Recharts telemetry and CUSUM score.
- `/incidents` — Incident Command Center with CSV export button.
- `/analytics` — Verified holdout metrics (Unseen Stations Precision 89.89%).
- `/validation` — 25-Gate pipeline verification checklist.

---

## 4. Custom Domain Setup (Optional)

To connect a custom domain (e.g., `skyguard.ai` or `skyguard-ai.in`):
1. Navigate to **Project Settings** $\to$ **Domains** in the Vercel dashboard.
2. Add your domain name.
3. Configure your DNS provider with the CNAME record:
   - Type: `CNAME`
   - Name: `@` or `subdomain`
   - Value: `cname.vercel-dns.com`
4. Update `NEXT_PUBLIC_APP_URL` in environment variables to match your custom domain.

---

## 5. Troubleshooting & Fallback Behavior

- **"ML service unavailable" / Degraded Health:**
  - If your external Python service on Render is sleeping (free tier spin-up), the Next.js API routes will seamlessly fallback to embedded causal QC rules.
  - The UI will remain fully operational and will not show blank screens.
- **Rate Limits:**
  - Vercel Edge caching is configured on static and report routes (`/api/metrics`, `/api/gates`) to avoid redundant filesystem reads.

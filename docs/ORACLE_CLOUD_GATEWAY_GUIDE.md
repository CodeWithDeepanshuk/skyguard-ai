# SkyGuard AI — Oracle Cloud Always Free Gateway Guide (SIH 26073)

**Objective**: Provide a permanent, fixed public IPv4 address at ₹0 cost to authenticate with the official India Meteorological Department (IMD) Automatic Weather Station (AWS) API, bypassing dynamic IP restrictions on Render and Vercel.

---

## 1. The Dynamic-IP Problem & The ₹0 Solution

### The Challenge
The official IMD API portal (`https://api.imd.gov.in`) requires every API key (`X-API-KEY`) to be bound to a **single static public IPv4**. Requests originating from any other IP receive `HTTP 401 Unauthorized` or `HTTP 403 Forbidden`.
* **Vercel**: Uses serverless edge lambdas whose egress IPs rotate across AWS/GCP regions on every request.
* **Render**: Free and standard tiers use shared multi-tenant egress pools whose IP addresses change across deploys, restarts, and network shifts.

### The Solution: Oracle Cloud Always Free VM Gateway
Oracle Cloud Infrastructure (OCI) provides **Always Free** compute instances and includes **Reserved Public IPv4 addresses** that never change across reboots or instance restarts.

```
                    ONE FIXED RESERVED PUBLIC IPv4
                                  │
                                  ▼
                        Oracle Cloud Free VM
                                  │
                       IMD API authentication
                      X-API-KEY + JWT OAuth token
                                  │
                                  ▼
                          Official IMD AWS
                                  │
                                  ▼
                          Raw observation
                                  │
                      schema/data validation
                       (Temp, Pressure, RH)
                                  │
                                  ▼
                         SkyGuard storage
                                  │
                      ┌───────────┴───────────┐
                      ▼                       ▼
               Render backend             ML pipeline
                      │
                      ▼
               Vercel frontend
```

1. **Only the Oracle reserved IPv4 is registered with IMD**.
2. **Neither Vercel nor Render ever contacts IMD directly**.
3. **The Oracle VM runs a lightweight collector every 15 minutes**, validates the schema, computes a SHA-256 cryptographic receipt, and pushes clean observations to Render via an authenticated webhook (`POST /api/v1/ingestion/imd`).
4. **Render ingests the validated observations** into `ObservationStore` (PostgreSQL), updating the live Indian map and anomaly detection models.

---

## 2. Step-by-Step Setup Walkthrough

### Step 1: Create an Oracle Cloud Free Tier Account
1. Visit [oracle.com/cloud/free/](https://www.oracle.com/cloud/free/) and sign up.
2. When choosing your **Home Region**, select an Indian region for minimal latency to IMD servers:
   * **India South (Hyderabad)**: `ap-hyderabad-1`
   * **India West (Mumbai)**: `ap-mumbai-1`
3. A ₹0 / $0 temporary verification hold may be placed and immediately refunded to verify your card.

---

### Step 2: Launch an Always Free Compute Instance
1. In the OCI Console, navigate to **Compute** -> **Instances** -> **Create Instance**.
2. **Name**: `skyguard-imd-gateway`
3. **Image & Shape**:
   * **Image**: *Ubuntu 24.04 LTS* (or *Oracle Linux 9*)
   * **Shape**: Select *Always Free Eligible*:
     * *VM.Standard.E2.1.Micro* (AMD 1 OCPU, 1 GB RAM) **OR**
     * *VM.Standard.A1.Flex* (Ampere ARM, 1–4 OCPUs, up to 24 GB RAM)
4. **Networking**:
   * Create a new Virtual Cloud Network (VCN) and public subnet.
   * Under **Public IP Address**, choose *Do not assign a public IPv4 address* (we will attach a Reserved IP in Step 3) OR assign an ephemeral IP and promote it to reserved.
5. **Add SSH Keys**:
   * Select *Generate a key pair for me* and download both the **Private Key** (`skyguard_oci.key`) and **Public Key**.
6. Click **Create**. The instance will be ready in under 60 seconds.

---

### Step 3: Allocate and Attach a Reserved Public IPv4
A reserved IP persists forever across instance reboots, stops, and maintenance events.

1. In the OCI Console, go to **Networking** -> **IP Management** -> **Reserved Public IPs**.
2. Click **Reserve Public IP Address**:
   * **Name**: `skyguard-imd-static-ip`
   * **IP Address Scope**: *Region*
   * Click **Reserve**.
3. Once created, note your new fixed public IPv4 (e.g., `140.238.xxx.xxx`).
4. Attach to your instance:
   * Go to **Compute** -> **Instances** -> click `skyguard-imd-gateway`.
   * Under **Resources** (bottom left), click **Attached VNICs**.
   * Click the primary VNIC name.
   * Under **Resources**, click **IPv4 Addresses**.
   * Click the three dots `...` next to the assigned private IP -> click **Edit**.
   * Under **Public IP Type**, select **Reserved Public IP**.
   * Choose your reserved IP (`skyguard-imd-static-ip`) and click **Update**.
5. Your VM now has a **permanent fixed public IPv4**.

---

### Step 4: Register the Reserved IPv4 on the IMD Portal
1. Open your browser and log into [api.imd.gov.in](https://api.imd.gov.in).
2. Go to **API Key Management** / **Generate API Key**.
3. In the **Allowed Public IP / Whitelisted IP** field, enter your exact **Oracle Reserved Public IPv4** from Step 3.
4. Generate the key and save your:
   * `X-API-KEY`
   * Portal Login `Email`
   * Portal Login `Password`

---

### Step 5: Configure the SkyGuard Render Backend
1. Open your [Render Dashboard](https://dashboard.render.com).
2. Select your SkyGuard backend web service.
3. Go to **Environment** -> **Add Environment Variable**:
   * **Key**: `SKYGUARD_INGESTION_TOKEN`
   * **Value**: Generate a random secure token (e.g., run `python -c "import secrets; print(secrets.token_hex(24))"`).
4. Note your Render service URL (e.g., `https://skyguard-ai.onrender.com`).

---

### Step 6: Deploy the Gateway on the Oracle Cloud VM

1. **SSH into the VM**:
   ```bash
   chmod 400 skyguard_oci.key
   ssh -i skyguard_oci.key ubuntu@<YOUR_ORACLE_RESERVED_IP>
   ```

2. **Clone the repository or copy the gateway files**:
   ```bash
   git clone https://github.com/CodeWithDeepanshuk/skyguard-ai.git
   cd skyguard-ai/tools/oci_gateway
   ```

3. **Run the Automated Installer**:
   ```bash
   sudo bash setup_oracle_vm.sh
   ```
   The installer:
   * Verifies Python 3.
   * Copies `collector.py` to `/opt/skyguard-gateway/`.
   * Checks your public egress IP against `https://api.imd.gov.in/public/ip.php`.
   * Creates `/etc/systemd/system/skyguard-collector.service`.
   * Creates `/etc/systemd/system/skyguard-collector.timer` (15-minute schedule).
   * Enables and arms the timer.

4. **Configure your credentials**:
   ```bash
   sudo nano /opt/skyguard-gateway/.env
   ```
   Paste your real credentials:
   ```ini
   IMD_API_KEY="your_imd_api_key_from_portal"
   IMD_API_EMAIL="your_registered_imd_email@example.com"
   IMD_API_PASSWORD="your_imd_portal_password"
   EXPECTED_PUBLIC_IP="140.238.xxx.xxx"
   RENDER_INGEST_URL="https://skyguard-ai.onrender.com/api/v1/ingestion/imd"
   SKYGUARD_INGESTION_TOKEN="your_secure_token_from_step_5"
   INTERVAL_SECONDS="900"
   ```
   Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

5. **Test an immediate run**:
   ```bash
   sudo systemctl start skyguard-collector.service
   ```

6. **Check the live logs**:
   ```bash
   sudo journalctl -u skyguard-collector.service -n 50 -f
   ```
   You should see:
   ```text
   Starting IMD ingestion cycle...
   Egress IP verified: 140.238.xxx.xxx
   Retrieved 1,248,312 bytes from IMD.
   Archived raw payload (SHA-256: e3b0c44298fc1c14...)
   Normalized 1008 stations with valid Temp/Press/RH.
   Successfully forwarded to Render: {'status': 'SUCCESS', 'inserted': 1008}
   Ingestion cycle completed in 3.42s.
   ```

---

## 3. Defeating Oracle's Always Free Idle-Reclaim Policy

### What is the Policy?
Oracle Cloud monitors Always Free compute instances and may reclaim (terminate/stop) instances that are deemed **idle** for 7 consecutive days:
* CPU utilization is less than 20%
* Network utilization is less than 20%
* Memory utilization is less than 20%

### How SkyGuard Prevents Reclamation
The SkyGuard Gateway is specifically engineered to satisfy active-use criteria:
1. **Periodic HTTPS Network Calls**: Every 15 minutes, the collector initiates outbound network requests to IMD and Render, transferring several megabytes of real data daily.
2. **Cryptographic Computations**: Generating SHA-256 hashes on the raw JSON payloads exercises CPU instructions.
3. **Anti-Reclaim Heartbeat**: The collector script includes an internal `anti_reclaim_heartbeat()` routine that briefly touches memory and CPU registers on each cycle.
4. **Persistent Local Disk I/O**: Immutable raw archives are stored under `/opt/skyguard-gateway/raw_archives/`, demonstrating continuous operational use.

---

## 4. End-to-End Verification Checklist

| Step | Component | Verification Command / Check | Expected Result |
|------|-----------|-----------------------------|-----------------|
| 1 | Oracle Egress IP | `python3 collector.py --check-ip` | Matches Reserved IP exactly |
| 2 | IMD Portal Binding | Login to `api.imd.gov.in` | Whitelist IP matches Oracle Reserved IP |
| 3 | Raw Data Archiving | `ls -la /opt/skyguard-gateway/raw_archives/` | `.json` and `.receipt.json` files generated |
| 4 | Render Ingest | `curl https://skyguard-ai.onrender.com/api/v1/source/status` | `"provider_name": "IMD_AWS"` with recent timestamp |
| 5 | Vercel Frontend | Open SkyGuard Dashboard in browser | Station markers turn live green; real Indian telemetry displayed |

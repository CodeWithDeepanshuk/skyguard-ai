# SkyGuard AI — Oracle Cloud Always Free IMD Gateway

**Smart India Hackathon 2026 | Problem Statement: SIH 26073**  
*Official India Meteorological Department (IMD) Automatic Weather Station (AWS) Integration*

---

## 1. Architectural Overview

The official IMD API portal (`https://api.imd.gov.in`) requires all API requests to originate from a **single, static whitelisted IPv4 address** bound to the account's `X-API-KEY`.

Because hosting platforms like Render and Vercel use rotating outbound IPs, directly contacting IMD from Render or Vercel results in `HTTP 401/403 (IP not authorized)`.

The **Oracle Cloud Always Free Gateway** solves this problem at **₹0 cost**:

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
                     Official IMD AWS API
                                │
                                ▼
                        Raw observation
                                │
                    schema/data validation
                     (Temp, Pressure, RH)
                                │
                                ▼
                        SkyGuard Storage
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
             Render backend             ML pipeline
                    │
                    ▼
             Vercel frontend
```

### Key Principles
1. **Single IP Registration**: Only the Oracle VM's reserved public IPv4 is registered on the IMD portal.
2. **Zero External Contact from Render/Vercel**: Neither Render nor Vercel directly queries IMD.
3. **Immutability & Integrity**: Raw IMD responses are archived locally on the VM and transmitted to Render alongside SHA-256 cryptographic receipts.
4. **Parameter Isolation**: The gateway extracts and normalizes ONLY the three target parameters (Air Temperature, Barometric/MSL Pressure, Relative Humidity).
5. **Anti-Reclamation Countermeasure**: Regular 15-minute scheduled runs prevent Oracle Cloud from marking the Always Free instance as idle.

---

## 2. File Inventory

| File | Purpose |
|------|---------|
| [`collector.py`](file:///tools/oci_gateway/collector.py) | Standalone Python 3 daemon / script with auto JWT renewal, IP check, raw archiving, schema validation, and Render webhook delivery. Zero external dependencies. |
| [`setup_oracle_vm.sh`](file:///tools/oci_gateway/setup_oracle_vm.sh) | Automated bash installer that configures directories, systemd service, and 15-minute systemd timer on Ubuntu or Oracle Linux. |
| [`.env.example`](file:///tools/oci_gateway/.env.example) | Environment variable template for IMD credentials, Render endpoint URL, and shared ingestion secret. |

---

## 3. Quick Deployment on Oracle Cloud VM

### Step 1: Connect to your Oracle VM via SSH
```bash
ssh -i your_key.pem ubuntu@<YOUR_ORACLE_RESERVED_IP>
```

### Step 2: Clone or Copy the Gateway Files
```bash
mkdir -p /tmp/skyguard-gateway
cd /tmp/skyguard-gateway
# Copy collector.py, setup_oracle_vm.sh, and .env.example here
```

### Step 3: Run the Automated Installer
```bash
sudo bash setup_oracle_vm.sh
```

### Step 4: Configure Credentials
```bash
sudo nano /opt/skyguard-gateway/.env
```
Fill in:
- `IMD_API_KEY`: Key generated on `api.imd.gov.in`
- `IMD_API_EMAIL`: Your IMD login email
- `IMD_API_PASSWORD`: Your IMD login password
- `RENDER_INGEST_URL`: `https://your-render-app.onrender.com/api/v1/ingestion/imd`
- `SKYGUARD_INGESTION_TOKEN`: Matching secret on Render backend
- `EXPECTED_PUBLIC_IP`: Your Oracle Reserved Public IPv4

### Step 5: Test Execution & Verify Logs
```bash
sudo systemctl start skyguard-collector.service
sudo journalctl -u skyguard-collector.service -n 50 -f
```

The systemd timer will automatically trigger the collector every 15 minutes.

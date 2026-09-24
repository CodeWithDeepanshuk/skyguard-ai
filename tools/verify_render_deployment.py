import urllib.request
import json

headers = {"User-Agent": "SkyGuard-Client/1.0"}

# 1. Status
req = urllib.request.Request("https://skyguard-ai-wbm9.onrender.com/api/live/status", headers=headers)
with urllib.request.urlopen(req) as resp:
    status = json.loads(resp.read().decode())
    print("=== 1. LIVE STATUS ===")
    print("Provider:", status.get("provider"))
    print("Product:", status.get("product"))
    print("Observation Count:", status.get("observation_count"))
    print("Reporting Stations:", status.get("reporting_stations"))

# 2. Readings
req = urllib.request.Request("https://skyguard-ai-wbm9.onrender.com/api/live/readings?limit=5", headers=headers)
with urllib.request.urlopen(req) as resp:
    readings = json.loads(resp.read().decode())
    print("\n=== 2. LIVE READINGS (100% IMD AWS) ===")
    print("Total Returned:", len(readings))
    for r in readings:
        print(f"  {r.get('station_id')} | {r.get('station_name')} | T={r.get('temperature_c')}C, P={r.get('pressure_hpa')}hPa, RH={r.get('relative_humidity_pct')}% | Prov={r.get('provider')}")

# 3. Incidents
req = urllib.request.Request("https://skyguard-ai-wbm9.onrender.com/api/incidents", headers=headers)
with urllib.request.urlopen(req) as resp:
    incidents = json.loads(resp.read().decode())
    print("\n=== 3. LIVE PHASE 6 INCIDENTS & CAUSAL IDW CORRECTIONS ===")
    print("Total Incidents:", len(incidents))
    for inc in incidents[:5]:
        corr = inc.get("corrections", [{}])[0]
        print(f"  {inc.get('incident_id')}: {inc.get('station_name')} ({inc.get('state')})")
        print(f"    Reported: {corr.get('reported_value')} -> IDW Estimate: {corr.get('estimate')} | CI90: {corr.get('uncertainty_interval')}")
        print(f"    Repair Tier: {inc.get('safe_repair_tier')} | Health Score: {inc.get('sensor_health', {}).get('score')}%")

# 4. Refresh endpoint test
req = urllib.request.Request("https://skyguard-ai-wbm9.onrender.com/api/live/refresh", data=b"", headers=headers, method="POST")
with urllib.request.urlopen(req) as resp:
    refreshed = json.loads(resp.read().decode())
    print("\n=== 4. AFTER POST /api/live/refresh TEST ===")
    print("Provider:", refreshed.get("provider"))
    print("Observation Count:", refreshed.get("observation_count"))
    print("Reporting Stations:", refreshed.get("reporting_stations"))

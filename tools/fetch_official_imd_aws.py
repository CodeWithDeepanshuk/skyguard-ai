"""Official IMD AWS Fetcher & Secure Collector (SIH 26073).

Authenticates with the official IMD API portal, retrieves live AWS observations,
stores raw payloads immutably with SHA-256 checksums, and extracts ONLY:
- Air Temperature (temperature_c)
- Barometric / Sea-Level Pressure (pressure_hpa)
- Relative Humidity (relative_humidity_pct)
"""
from __future__ import annotations

import getpass
import hashlib
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
TOKEN_URL = "https://api.imd.gov.in/api/oauth/token.php"
AWS_DATA_URL = "https://api.imd.gov.in/api/v1/aws_data"
AWS_MAPPING_URL = "https://api.imd.gov.in/api/v1/aws_data_mapping"
IP_CHECK_URL = "https://api.imd.gov.in/public/ip.php"

RAW_DIR = ROOT / "data" / "raw" / "imd_aws"
OBS_DIR = ROOT / "data" / "observations"


def get_opener(proxy_url: Optional[str] = None) -> urllib.request.OpenerDirector:
    """Build an opener that routes through a static outbound proxy if configured."""
    proxy = proxy_url or os.getenv("IMD_PROXY_URL") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if proxy:
        return urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener()


def get_public_ip(proxy_url: Optional[str] = None) -> str:
    """Check what public IP the user/proxy is sending to IMD's servers."""
    try:
        req = urllib.request.Request(IP_CHECK_URL, headers={"User-Agent": "SkyGuard-AI/1.0"})
        with get_opener(proxy_url).open(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("public_ip", "UNKNOWN")
    except Exception:
        return "UNKNOWN"


def acquire_jwt_token(email: str, password: str, proxy_url: Optional[str] = None) -> tuple[str, int]:
    """Request JWT bearer token from IMD oauth endpoint."""
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST"
    )
    try:
        with get_opener(proxy_url).open(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("access_token")
            expires_in = int(data.get("expires_in", 3600))
            if not token:
                raise RuntimeError(f"IMD JWT response did not contain access_token: {data}")
            return token, expires_in
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"IMD Authentication failed with HTTP {exc.code}: {err_msg}") from exc


def fetch_imd_endpoint(url: str, api_key: str, jwt_token: str, proxy_url: Optional[str] = None) -> tuple[bytes, Any]:
    """Fetch an authenticated endpoint with X-API-KEY and Bearer JWT."""
    headers = {
        "X-API-KEY": api_key,
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/json",
        "User-Agent": "SkyGuard-AI-SIH26073/1.0",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with get_opener(proxy_url).open(req, timeout=25) as resp:
            raw_bytes = resp.read()
            payload = json.loads(raw_bytes.decode("utf-8"))
            return raw_bytes, payload
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"IMD API call to {url} failed with HTTP {exc.code}: {err_msg}") from exc


def archive_raw_payload(endpoint_name: str, raw_bytes: bytes, source_url: str) -> tuple[Path, Path]:
    """Store raw payload immutably alongside a cryptographic SHA-256 receipt."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    raw_file = RAW_DIR / f"{endpoint_name}_{ts}.json"
    receipt_file = RAW_DIR / f"{endpoint_name}_{ts}.receipt.json"

    raw_file.write_bytes(raw_bytes)

    receipt = {
        "endpoint_name": endpoint_name,
        "source_url": source_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "payload_bytes": len(raw_bytes),
        "payload_sha256": sha256,
        "generated_rows": 0,
        "is_synthetic": False,
        "provenance": "OFFICIAL_IMD_AWS_AUTHORIZED_ENDPOINT",
    }
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return raw_file, receipt_file


def parse_float(val: Any) -> Optional[float]:
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def normalize_aws_records(payload: Any) -> List[Dict[str, Any]]:
    """Extract and normalize only the three SIH 26073 target parameters."""
    records = []
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        for key in ("data", "records", "result", "results"):
            if isinstance(payload.get(key), list):
                records = payload[key]
                break
        if not records and any(k in payload for k in ("ID", "CALL_SIGN", "CURR_TEMP")):
            records = [payload]

    normalized = []
    for r in records:
        if not isinstance(r, dict):
            continue

        sid = str(r.get("CALL_SIGN") or r.get("ID") or r.get("station_id") or "").strip()
        if not sid:
            continue

        temp_c = parse_float(r.get("CURR_TEMP") or r.get("TEMP") or r.get("temperature_c"))
        press_hpa = parse_float(r.get("MSLP") or r.get("SLP") or r.get("PRESSURE") or r.get("pressure_hpa"))
        rh_pct = parse_float(r.get("RH") or r.get("HUMIDITY") or r.get("relative_humidity_pct"))

        date_str = str(r.get("DATE") or r.get("Date") or "").strip()
        time_str = str(r.get("TIME") or r.get("Time") or "00:00:00").strip()

        # Build UTC timestamp
        ts_utc = None
        if date_str:
            try:
                dt_iso = f"{date_str}T{time_str}Z"
                ts_utc = datetime.fromisoformat(dt_iso.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
            except Exception:
                ts_utc = datetime.now(timezone.utc).isoformat()
        else:
            ts_utc = datetime.now(timezone.utc).isoformat()

        normalized.append({
            "station_id": sid,
            "station_name": str(r.get("STATION") or r.get("station_name") or sid).strip(),
            "state": str(r.get("STATE") or r.get("state") or "").strip(),
            "district": str(r.get("DISTRICT") or r.get("district") or "").strip(),
            "latitude": parse_float(r.get("Latitude") or r.get("latitude")),
            "longitude": parse_float(r.get("Longitude") or r.get("longitude")),
            "timestamp_utc": ts_utc,
            "temperature_c": temp_c,
            "pressure_hpa": press_hpa,
            "relative_humidity_pct": rh_pct,
            "source": "IMD_AUTHORIZED_AWS_API",
            "is_direct_observation": True,
            "is_synthetic": False,
        })
    return normalized


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Fetch official IMD AWS observations")
    parser.add_argument("--proxy", help="Outbound static proxy URL (e.g. http://proxy.fixie.io:80)")
    args, _ = parser.parse_known_args()
    proxy_url = args.proxy or os.getenv("IMD_PROXY_URL")

    print("=" * 70)
    print("  SkyGuard AI — Official IMD AWS Secure Data Collector")
    print("  Problem Statement: SIH 26073 | India Meteorological Department")
    print("=" * 70)

    # 1. IP Check
    public_ip = get_public_ip(proxy_url)
    print(f"\n[1] IP Binding Check:")
    print(f"    Detected Public IP of this server: {public_ip}")
    print(f"    * Note: The IMD API key must be generated on the portal with this IP.")

    # 2. Credential Resolution
    api_key = os.getenv("IMD_API_KEY", "").strip()
    jwt_token = os.getenv("IMD_API_JWT_TOKEN", "").strip()
    email = os.getenv("IMD_API_EMAIL", "").strip()
    password = os.getenv("IMD_API_PASSWORD", "").strip()

    if not api_key:
        api_key = input("\n[2] Enter your IMD X-API-KEY: ").strip()

    if not jwt_token and not (email and password):
        print("\n[3] Authentication Method:")
        print("    A. Login with Portal Email + Password (auto-generates fresh JWT)")
        print("    B. Paste an existing JWT Access Token from portal Test Console")
        choice = input("    Select option [A/B] (default A): ").strip().upper() or "A"

        if choice == "B":
            jwt_token = input("    Paste your JWT Bearer Token (without 'Bearer '): ").strip()
        else:
            email = input("    Enter your registered IMD Portal Email: ").strip()
            password = getpass.getpass("    Enter your IMD Portal Password: ").strip()

    # 3. Generate JWT if needed
    if not jwt_token:
        print("\n[4] Requesting JWT Bearer Token from https://api.imd.gov.in/api/oauth/token.php...")
        try:
            jwt_token, expires_in = acquire_jwt_token(email, password, proxy_url)
            print(f"    SUCCESS: Obtained JWT Bearer Token (valid for {expires_in} seconds).")
        except Exception as exc:
            print(f"    ERROR: {exc}")
            sys.exit(1)

    # 4. Fetch AWS Data
    print(f"\n[5] Fetching live AWS Observations from {AWS_DATA_URL}...")
    try:
        raw_bytes, payload = fetch_imd_endpoint(AWS_DATA_URL, api_key, jwt_token, proxy_url)
        raw_path, receipt_path = archive_raw_payload("aws_data", raw_bytes, AWS_DATA_URL)
        print(f"    SUCCESS: Raw payload archived to {raw_path}")
        print(f"    Cryptographic receipt: {receipt_path}")

        # Normalize 3 parameters
        normalized = normalize_aws_records(payload)
        print(f"    Parsed {len(normalized)} stations with parameters (Temp, Pressure, RH).")

        OBS_DIR.mkdir(parents=True, exist_ok=True)
        obs_output = OBS_DIR / "latest_imd_aws.json"
        obs_output.write_text(json.dumps({
            "source": "IMD_AUTHORIZED_AWS_API",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "station_count": len(normalized),
            "records": normalized,
        }, indent=2), encoding="utf-8")
        print(f"    Normalized observations written to {obs_output}")

    except Exception as exc:
        print(f"    FAILED: {exc}")
        print("\n    Tip: If your IP is not bound or you receive HTTP 401/403, you can")
        print("    test directly in the IMD portal's 'API Test Console' in your browser,")
        print("    save the JSON, and run: python tools/import_manual_imd_json.py")
        sys.exit(2)

    # 5. Optionally fetch mapping
    fetch_map = input("\n[6] Also fetch AWS Station Metadata Mapping? [y/N]: ").strip().lower()
    if fetch_map in ("y", "yes"):
        try:
            raw_map, map_payload = fetch_imd_endpoint(AWS_MAPPING_URL, api_key, jwt_token, proxy_url)
            raw_mpath, rec_mpath = archive_raw_payload("aws_data_mapping", raw_map, AWS_MAPPING_URL)
            print(f"    SUCCESS: Station mapping archived to {raw_mpath}")
        except Exception as exc:
            print(f"    Mapping fetch warning: {exc}")

    print("\n" + "=" * 70)
    print("  IMD AWS Data Ingestion Complete! Ready for detection pipeline.")
    print("=" * 70)


if __name__ == "__main__":
    main()

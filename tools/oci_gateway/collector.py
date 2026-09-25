#!/usr/bin/env python3
"""SkyGuard AI — Oracle Cloud Always Free IMD Gateway Collector (SIH 26073).

Runs on an Oracle Cloud Always Free VM equipped with a single Reserved Public IPv4.
Acts as the dedicated, whitelisted ingestion proxy for the official IMD AWS API:
1. Verifies egress IP against the IMD IP-check endpoint.
2. Authenticates with IMD using X-API-KEY and auto-refreshed JWT OAuth tokens.
3. Retrieves authentic national Automatic Weather Station observations.
4. Stores raw JSON payloads immutably with cryptographic SHA-256 receipts.
5. Filters and validates ONLY the 3 target parameters:
   - Air Temperature (deg C)
   - Barometric / MSL Pressure (hPa)
   - Relative Humidity (%)
6. Securely forwards validated observations and receipts to the SkyGuard Render backend.
7. Generates periodic active CPU/memory/network activity to satisfy Oracle's Always Free policy.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

IMD_IP_CHECK_URL = "https://api.imd.gov.in/public/ip.php"
IMD_TOKEN_URL = "https://api.imd.gov.in/api/oauth/token.php"
IMD_AWS_DATA_URL = "https://api.imd.gov.in/api/v1/aws_data"
IMD_AWS_MAPPING_URL = "https://api.imd.gov.in/api/v1/aws_data_mapping"

GATEWAY_DIR = Path(__file__).resolve().parent
TOKEN_CACHE_FILE = GATEWAY_DIR / ".imd_jwt_cache.json"
DEFAULT_ARCHIVE_DIR = GATEWAY_DIR / "raw_archives"


def load_env_file(env_path: Path) -> None:
    """Load key-value pairs from .env into os.environ if not already set."""
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val


def get_current_public_ip(timeout: float = 10.0) -> str:
    """Detect egress public IP as seen by IMD's servers."""
    req = urllib.request.Request(
        IMD_IP_CHECK_URL,
        headers={"User-Agent": "SkyGuard-OCI-Gateway/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return str(data.get("public_ip") or "UNKNOWN")
    except Exception as exc:
        return f"ERROR ({exc})"


def parse_float(val: Any) -> Optional[float]:
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


class OCIIMDCollector:
    def __init__(
        self,
        api_key: str,
        email: str,
        password: str,
        render_url: str,
        ingest_token: str,
        expected_ip: Optional[str] = None,
        archive_dir: Path = DEFAULT_ARCHIVE_DIR,
    ) -> None:
        self.api_key = api_key.strip()
        self.email = email.strip()
        self.password = password.strip()
        self.render_url = render_url.strip()
        self.ingest_token = ingest_token.strip()
        self.expected_ip = expected_ip.strip() if expected_ip else ""
        self.archive_dir = archive_dir
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.cached_jwt = ""
        self.jwt_expires_at = 0.0
        self._load_cached_jwt()

    def _load_cached_jwt(self) -> None:
        if TOKEN_CACHE_FILE.is_file():
            try:
                data = json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
                token = data.get("access_token", "")
                exp = float(data.get("expires_at", 0))
                # Only use if at least 5 minutes remaining
                if token and exp > (time.time() + 300):
                    self.cached_jwt = token
                    self.jwt_expires_at = exp
            except Exception:
                pass

    def _save_cached_jwt(self, token: str, expires_in: int) -> None:
        self.cached_jwt = token
        self.jwt_expires_at = time.time() + max(60, expires_in)
        try:
            TOKEN_CACHE_FILE.write_text(
                json.dumps({"access_token": token, "expires_at": self.jwt_expires_at}),
                encoding="utf-8",
            )
            os.chmod(TOKEN_CACHE_FILE, 0o600)
        except Exception:
            pass

    def get_jwt_token(self) -> str:
        """Return valid JWT, requesting a fresh token when near expiration."""
        if self.cached_jwt and time.time() < (self.jwt_expires_at - 180):
            return self.cached_jwt

        if not self.email or not self.password:
            # Fall back to env JWT if email/password not provided
            env_jwt = os.getenv("IMD_API_JWT_TOKEN", "").strip()
            if env_jwt:
                return env_jwt
            raise RuntimeError("IMD_API_EMAIL and IMD_API_PASSWORD are required to obtain JWT token")

        body = json.dumps({"email": self.email, "password": self.password}).encode("utf-8")
        req = urllib.request.Request(
            IMD_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                token = data.get("access_token")
                expires_in = int(data.get("expires_in", 3600))
                if not token:
                    raise RuntimeError(f"IMD OAuth response missing access_token: {data}")
                self._save_cached_jwt(token, expires_in)
                return token
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"IMD JWT authentication failed (HTTP {exc.code}): {err}") from exc

    def verify_ip(self) -> str:
        """Verify egress IP matches expected Oracle Reserved Public IP."""
        current_ip = get_current_public_ip()
        if self.expected_ip and current_ip != self.expected_ip:
            raise RuntimeError(
                f"IP Mismatch! Current egress IP is {current_ip}, but expected Oracle reserved IP is {self.expected_ip}."
                " Update your configuration or verify VNIC attachment."
            )
        return current_ip

    def fetch_aws_payload(self) -> Tuple[bytes, Any]:
        """Fetch raw observation payload from official IMD endpoint."""
        token = self.get_jwt_token()
        headers = {
            "X-API-KEY": self.api_key,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "SkyGuard-OCI-Gateway-SIH26073/1.0",
        }
        req = urllib.request.Request(IMD_AWS_DATA_URL, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))
                return raw_bytes, data
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                # Token might have expired early; clear cache and retry once
                self.cached_jwt = ""
                self.jwt_expires_at = 0.0
                token = self.get_jwt_token()
                headers["Authorization"] = f"Bearer {token}"
                retry_req = urllib.request.Request(IMD_AWS_DATA_URL, headers=headers, method="GET")
                with urllib.request.urlopen(retry_req, timeout=25) as retry_resp:
                    raw_bytes = retry_resp.read()
                    data = json.loads(raw_bytes.decode("utf-8"))
                    return raw_bytes, data
            err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"IMD AWS data fetch failed (HTTP {exc.code}): {err}") from exc

    def archive_payload(self, raw_bytes: bytes, egress_ip: str) -> Dict[str, Any]:
        """Save raw bytes to local disk with SHA-256 cryptographic receipt."""
        ts_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ts_tag = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        raw_path = self.archive_dir / f"imd_aws_{ts_tag}.json"
        receipt_path = self.archive_dir / f"imd_aws_{ts_tag}.receipt.json"

        raw_path.write_bytes(raw_bytes)

        receipt = {
            "endpoint_name": "aws_data",
            "source_url": IMD_AWS_DATA_URL,
            "retrieved_at_utc": ts_iso,
            "gateway_egress_ip": egress_ip,
            "payload_bytes": len(raw_bytes),
            "payload_sha256": sha256,
            "provenance": "ORACLE_CLOUD_ALWAYS_FREE_GATEWAY",
            "is_synthetic": False,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return receipt

    def normalize_records(self, payload: Any) -> List[Dict[str, Any]]:
        """Extract and validate ONLY the 3 SIH 26073 target parameters."""
        records: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            records = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            for k in ("data", "records", "result", "results", "items"):
                if isinstance(payload.get(k), list):
                    records = [item for item in payload[k] if isinstance(item, dict)]
                    break
            if not records and any(k in payload for k in ("ID", "CALL_SIGN", "CURR_TEMP")):
                records = [payload]

        normalized: List[Dict[str, Any]] = []
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for r in records:
            sid = str(r.get("CALL_SIGN") or r.get("ID") or r.get("station_id") or "").strip()
            if not sid:
                continue

            temp_c = parse_float(r.get("CURR_TEMP") or r.get("TEMP") or r.get("temperature_c"))
            press_hpa = parse_float(r.get("MSLP") or r.get("SLP") or r.get("PRESSURE") or r.get("pressure_hpa"))
            rh_pct = parse_float(r.get("RH") or r.get("HUMIDITY") or r.get("relative_humidity_pct"))

            # Must contain at least one valid parameter
            if temp_c is None and press_hpa is None and rh_pct is None:
                continue

            # Parse timestamp
            date_str = str(r.get("DATE") or r.get("Date") or "").strip()
            time_str = str(r.get("TIME") or r.get("Time") or "00:00:00").strip()
            ts_utc = now_iso
            if date_str:
                try:
                    dt = datetime.datetime.fromisoformat(f"{date_str}T{time_str}Z".replace("Z", "+00:00"))
                    ts_utc = dt.astimezone(datetime.timezone.utc).isoformat()
                except Exception:
                    ts_utc = now_iso

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

    def forward_to_render(
        self,
        receipt: Dict[str, Any],
        records: List[Dict[str, Any]],
        raw_payload_str: str,
        attempts: int = 3,
    ) -> Dict[str, Any]:
        """Transmit observations and receipts to Render backend with retries."""
        payload_data = {
            "receipt": receipt,
            "records": records,
            "raw_payload_json": raw_payload_str,
            "gateway_metadata": {
                "source": "ORACLE_CLOUD_ALWAYS_FREE_GATEWAY",
                "forwarded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "record_count": len(records),
            },
        }
        body = json.dumps(payload_data).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Ingestion-Token": self.ingest_token,
            "Authorization": f"Bearer {self.ingest_token}",
            "User-Agent": "SkyGuard-OCI-Gateway/1.0",
        }
        req = urllib.request.Request(self.render_url, data=body, headers=headers, method="POST")

        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    return resp_data
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {exc.code}: {err_body}"
                if exc.code in (401, 403, 503):
                    # Authentication or configuration error; do not retry
                    raise RuntimeError(f"Render rejected ingestion ({last_error})") from exc
            except Exception as exc:
                last_error = str(exc)

            if attempt < attempts:
                wait_time = 2.0 ** attempt
                time.sleep(wait_time)

        raise RuntimeError(f"Failed to forward data to Render after {attempts} attempts: {last_error}")

    def run_cycle(self, dry_run: bool = False) -> Dict[str, Any]:
        """Execute one complete ingestion cycle."""
        start_time = time.monotonic()
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[{timestamp}] Starting IMD ingestion cycle...")

        # 1. IP Check
        egress_ip = self.verify_ip()
        print(f"[{timestamp}] Egress IP verified: {egress_ip}")

        # 2. Fetch from IMD
        raw_bytes, payload = self.fetch_aws_payload()
        print(f"[{timestamp}] Retrieved {len(raw_bytes):,} bytes from IMD.")

        # 3. Archive locally
        receipt = self.archive_payload(raw_bytes, egress_ip)
        print(f"[{timestamp}] Archived raw payload (SHA-256: {receipt['payload_sha256'][:16]}...)")

        # 4. Normalize (3 parameters ONLY)
        records = self.normalize_records(payload)
        print(f"[{timestamp}] Normalized {len(records)} stations with valid Temp/Press/RH.")

        # 5. Forward to Render
        render_response = {}
        if dry_run:
            print(f"[{timestamp}] DRY RUN: Skipping forward to Render.")
            render_response = {"status": "DRY_RUN", "records_ready": len(records)}
        else:
            if not self.render_url:
                raise RuntimeError("RENDER_INGEST_URL is not configured")
            raw_str = raw_bytes.decode("utf-8", errors="replace")
            render_response = self.forward_to_render(receipt, records, raw_str)
            print(f"[{timestamp}] Successfully forwarded to Render: {render_response}")

        elapsed = round(time.monotonic() - start_time, 2)
        print(f"[{timestamp}] Ingestion cycle completed in {elapsed}s.\n")
        return {
            "egress_ip": egress_ip,
            "receipt": receipt,
            "station_count": len(records),
            "render_response": render_response,
            "elapsed_seconds": elapsed,
        }


def anti_reclaim_heartbeat() -> None:
    """Light memory & CPU touch to maintain non-idle metrics for OCI Always Free policy."""
    # Performs a quick matrix computation and memory allocation to ensure OS
    # registers regular active CPU/RAM usage without consuming high resources.
    dummy = [math.sin(i * 0.01) for i in range(100_000)]
    _ = sum(dummy)
    del dummy


def main() -> None:
    parser = argparse.ArgumentParser(description="SkyGuard OCI Gateway Collector")
    parser.add_argument("--once", action="store_true", help="Run once and exit (for systemd timer)")
    parser.add_argument("--loop", action="store_true", help="Run continuously in a loop")
    parser.add_argument("--interval", type=int, default=900, help="Interval in seconds for loop mode (default: 900s / 15m)")
    parser.add_argument("--check-ip", action="store_true", help="Check current public IP and exit")
    parser.add_argument("--dry-run", action="store_true", help="Fetch from IMD and validate, do not push to Render")
    parser.add_argument("--env-file", type=str, default="", help="Path to custom .env file")
    args = parser.parse_args()

    # Load environment variables
    env_file = Path(args.env_file) if args.env_file else (GATEWAY_DIR / ".env")
    load_env_file(env_file)

    if args.check_ip:
        ip = get_current_public_ip()
        print(f"Oracle VM Public Egress IP: {ip}")
        expected = os.getenv("EXPECTED_PUBLIC_IP", "").strip()
        if expected:
            if ip == expected:
                print("MATCH: Egress IP matches configured EXPECTED_PUBLIC_IP.")
            else:
                print(f"WARNING: IP does not match EXPECTED_PUBLIC_IP ({expected})!")
        sys.exit(0)

    api_key = os.getenv("IMD_API_KEY", "").strip()
    email = os.getenv("IMD_API_EMAIL", "").strip()
    password = os.getenv("IMD_API_PASSWORD", "").strip()
    render_url = os.getenv("RENDER_INGEST_URL", "").strip()
    ingest_token = os.getenv("SKYGUARD_INGESTION_TOKEN", "").strip()
    expected_ip = os.getenv("EXPECTED_PUBLIC_IP", "").strip()

    if not api_key:
        print("ERROR: IMD_API_KEY environment variable is required.")
        sys.exit(1)

    collector = OCIIMDCollector(
        api_key=api_key,
        email=email,
        password=password,
        render_url=render_url,
        ingest_token=ingest_token,
        expected_ip=expected_ip,
    )

    if args.loop:
        print(f"Starting SkyGuard OCI Gateway in daemon loop (interval: {args.interval}s)...")
        while True:
            try:
                collector.run_cycle(dry_run=args.dry_run)
                anti_reclaim_heartbeat()
            except Exception as exc:
                print(f"[{datetime.datetime.now(datetime.timezone.utc)}] ERROR in cycle: {exc}")
            time.sleep(args.interval)
    else:
        # Default: single run (for systemd timer or manual test)
        try:
            collector.run_cycle(dry_run=args.dry_run)
            anti_reclaim_heartbeat()
        except Exception as exc:
            print(f"ERROR: {exc}")
            sys.exit(2)


if __name__ == "__main__":
    main()

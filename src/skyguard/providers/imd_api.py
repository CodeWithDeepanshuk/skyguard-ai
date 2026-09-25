"""Credentialed IMD AWS/ARG API adapter.

The official endpoint returns a current network snapshot.  Continuous history
is therefore created by the ingestion worker, not invented by this adapter.
Authentication details are intentionally environment-driven because the IMD
portal grants credentials per approved account and does not publish one
universal header contract on the public field-reference page.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from skyguard.providers.base import (
    ObservationRecord,
    PressureType,
    ProviderName,
    RHSource,
    SourceType,
    WeatherProvider,
)


AWS_ENDPOINT = "https://api.imd.gov.in/api/v1/aws_data"
AWS_MAPPING_ENDPOINT = "https://api.imd.gov.in/api/v1/aws_data_mapping"
TOKEN_ENDPOINT = "https://api.imd.gov.in/api/oauth/token.php"


def _number(value: Any) -> Optional[float]:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "records", "result", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    # A station-specific request can return one object directly.
    if any(key in payload for key in ("CALL_SIGN", "STATION", "CURR_TEMP")):
        return [payload]
    return []


def _timestamp_utc(row: Dict[str, Any]) -> str:
    date = str(row.get("DATE") or row.get("Date") or "").strip()
    clock = str(row.get("TIME") or row.get("Time") or "").strip()
    if not date:
        raise ValueError("IMD AWS row has no observation date")
    value = f"{date} {clock or '00:00:00'}"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        # IMD's public AWS field reference specifies UTC for observation time.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class IMDAWSAPIProvider(WeatherProvider):
    """Normalize approved IMD AWS/ARG responses into the SkyGuard contract."""

    def __init__(
        self,
        endpoint: str = AWS_ENDPOINT,
        mapping_endpoint: str = AWS_MAPPING_ENDPOINT,
        token_endpoint: str = TOKEN_ENDPOINT,
        timeout_seconds: float = 20.0,
    ) -> None:
        super().__init__(name=ProviderName.IMD_AWS.value, source_type=SourceType.OBSERVED)
        self.endpoint = endpoint
        self.mapping_endpoint = mapping_endpoint
        self.token_endpoint = token_endpoint
        self.timeout_seconds = timeout_seconds
        self._jwt_token = ""
        self._jwt_expires_at = datetime.min.replace(tzinfo=timezone.utc)

    @property
    def auth_headers(self) -> Dict[str, str]:
        api_key = os.getenv("IMD_API_KEY", "").strip()
        token = self._access_token()
        if not api_key or not token:
            return {}
        return {"X-API-KEY": api_key, "Authorization": f"Bearer {token}"}

    @property
    def configured(self) -> bool:
        api_key = os.getenv("IMD_API_KEY", "").strip()
        static_token = os.getenv("IMD_API_JWT_TOKEN", "").strip() or os.getenv("IMD_API_TOKEN", "").strip()
        email = os.getenv("IMD_API_EMAIL", "").strip()
        password = os.getenv("IMD_API_PASSWORD", "").strip()
        schema_verified = os.getenv("IMD_NORMALIZATION_ENABLED", "").strip().lower() in {"1", "true", "yes"}
        contract_value = os.getenv("IMD_SCHEMA_CONTRACT_PATH", "").strip()
        contract_exists = bool(contract_value and Path(contract_value).is_file())
        return bool(schema_verified and contract_exists and api_key and (static_token or (email and password)))

    def _access_token(self) -> str:
        """Return a valid JWT without ever persisting it to disk or logs."""
        static_token = os.getenv("IMD_API_JWT_TOKEN", "").strip() or os.getenv("IMD_API_TOKEN", "").strip()
        if static_token:
            return static_token
        if self._jwt_token and datetime.now(timezone.utc) < self._jwt_expires_at:
            return self._jwt_token
        email = os.getenv("IMD_API_EMAIL", "").strip()
        password = os.getenv("IMD_API_PASSWORD", "").strip()
        if not email or not password:
            return ""
        body = json.dumps({"email": email, "password": password}).encode("utf-8")
        request = urllib.request.Request(
            self.token_endpoint,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"IMD JWT request failed with HTTP {exc.code}") from exc
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("IMD JWT response did not contain access_token")
        try:
            expires_in = max(60, int(payload.get("expires_in", 3600)))
        except (TypeError, ValueError):
            expires_in = 3600
        self._jwt_token = token
        # Refresh early so an in-flight national request never uses a near-expiry token.
        self._jwt_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(30, expires_in - 300))
        return token

    def _request_json(self, url: str) -> Any:
        if not self.configured:
            raise RuntimeError("IMD API credentials are not configured")
        headers = {
            "Accept": "application/json",
            "User-Agent": "SkyGuard-AI-SIH26073-Academic/2.0",
            **self.auth_headers,
        }
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # A cached JWT may expire or be revoked before its advertised expiry.
            if exc.code == 401 and not os.getenv("IMD_API_JWT_TOKEN", "").strip():
                self._jwt_token = ""
                self._jwt_expires_at = datetime.min.replace(tzinfo=timezone.utc)
                retry_headers = {
                    "Accept": "application/json",
                    "User-Agent": "SkyGuard-AI-SIH26073-Academic/2.0",
                    **self.auth_headers,
                }
                retry = urllib.request.Request(url, headers=retry_headers)
                with urllib.request.urlopen(retry, timeout=self.timeout_seconds) as response:  # noqa: S310
                    return json.loads(response.read().decode("utf-8"))
            raise RuntimeError(f"IMD API request failed with HTTP {exc.code}") from exc

    def fetch_network(self, *, state_id: Optional[int] = None) -> List[ObservationRecord]:
        url = self.endpoint
        if state_id is not None:
            url = f"{url}?{urllib.parse.urlencode({'sid': state_id})}"
        payload = self._request_json(url)
        return self._normalize_payload(payload, url)

    def _normalize_payload(self, payload: Any, source_url: str) -> List[ObservationRecord]:
        observations: List[ObservationRecord] = []
        for row in _records(payload):
            try:
                timestamp = _timestamp_utc(row)
            except (TypeError, ValueError):
                continue
            call_sign = str(row.get("CALL_SIGN") or row.get("ID") or "").strip()
            if not call_sign:
                continue
            raw_payload = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            temperature = _number(row.get("CURR_TEMP"))
            pressure = _number(row.get("MSLP"))
            humidity = _number(row.get("RH"))
            latitude = _number(row.get("Latitude") or row.get("LATITUDE"))
            longitude = _number(row.get("Longitude") or row.get("LONGITUDE"))
            if latitude is None or longitude is None:
                continue
            observations.append(ObservationRecord(
                provider=self.name,
                source_type=self.source_type.value,
                station_id=call_sign,
                provider_station_id=call_sign,
                canonical_station_id=call_sign,
                station_name=str(row.get("STATION") or call_sign).strip(),
                state=str(row.get("STATE") or "").strip(),
                district=str(row.get("DISTRICT") or "").strip(),
                timestamp_utc=timestamp,
                latitude=latitude,
                longitude=longitude,
                temperature_c=temperature,
                pressure_hpa=pressure,
                pressure_type=PressureType.MEAN_SEA_LEVEL_PRESSURE.value,
                relative_humidity_pct=humidity,
                rh_source=RHSource.OBSERVED.value if humidity is not None else RHSource.UNAVAILABLE.value,
                is_direct_observation=True,
                is_interpolated=False,
                is_model_field=False,
                raw_source_hash=hashlib.sha256(raw_payload.encode("utf-8")).hexdigest(),
                source_url=source_url,
                message_id=str(row.get("ID") or f"{call_sign}|{timestamp}"),
                raw_payload_json=raw_payload,
            ))
        observations.sort(key=lambda item: (item.timestamp_utc, item.provider_station_id), reverse=True)
        return observations

    def fetch_current(self, station_id: str) -> Optional[ObservationRecord]:
        if not self.configured:
            return None
        url = f"{self.endpoint}?{urllib.parse.urlencode({'id': station_id})}"
        payload = self._request_json(url)
        rows = self._normalize_payload(payload, url)
        return rows[0] if rows else None

    def fetch_history(self, station_id: str, hours: int = 24) -> List[ObservationRecord]:
        del hours
        current = self.fetch_current(station_id)
        return [current] if current else []

    def station_metadata(self) -> List[Dict[str, Any]]:
        if not self.configured:
            return []
        return _records(self._request_json(self.mapping_endpoint))

    def healthcheck(self) -> Dict[str, Any]:
        if not self.configured:
            return {
                "provider": self.name,
                "status": "normalization_disabled_pending_real_schema_review",
                "endpoint": self.endpoint,
                "credential_source": "environment",
                "required_auth": "X-API-KEY + JWT bearer",
            }
        started = time.perf_counter()
        try:
            rows = self.fetch_network()
            return {
                "provider": self.name,
                "status": "healthy",
                "endpoint": self.endpoint,
                "latency_ms": round((time.perf_counter() - started) * 1000.0, 1),
                "records_received": len(rows),
            }
        except Exception as exc:
            return {
                "provider": self.name,
                "status": "unreachable",
                "endpoint": self.endpoint,
                "latency_ms": round((time.perf_counter() - started) * 1000.0, 1),
                "error": str(exc),
            }

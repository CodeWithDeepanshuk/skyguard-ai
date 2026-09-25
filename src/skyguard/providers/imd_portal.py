"""Backend-only client for the authenticated IMD API portal contract.

This module deliberately downloads and inspects payloads without interpreting
AWS fields. Normalization belongs to a later, explicitly approved stage after
real responses and the endpoint-specific reference have been reviewed.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


TOKEN_ENDPOINT = "https://api.imd.gov.in/api/oauth/token.php"
AWS_ENDPOINTS = {
    "aws_data_mapping": "https://api.imd.gov.in/api/v1/aws_data_mapping",
    "aws_data": "https://api.imd.gov.in/api/v1/aws_data",
}


class IMDPortalError(RuntimeError):
    """Base error that never includes credentials or response bodies."""


class IMDConfigurationError(IMDPortalError):
    pass


class IMDAuthenticationError(IMDPortalError):
    pass


class IMDResponseError(IMDPortalError):
    pass


class IMDApplicationError(IMDPortalError):
    pass


@dataclass(frozen=True)
class HTTPResult:
    endpoint_name: str
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes
    payload: Any
    retrieved_at_utc: str


Transport = Callable[[str, str, Mapping[str, str], Optional[bytes], float], tuple[int, Mapping[str, str], bytes]]


def _default_transport(
    method: str, url: str, headers: Mapping[str, str], body: Optional[bytes], timeout: float,
) -> tuple[int, Mapping[str, str], bytes]:
    request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
    proxy = os.getenv("IMD_PROXY_URL") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy})) if proxy else urllib.request.build_opener()
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310
            return int(response.status), dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        # Keep the body available to the caller for private inspection, but do
        # not interpolate it into an exception or log message.
        return int(exc.code), dict(exc.headers.items()), exc.read()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _json(body: bytes, *, context: str) -> Any:
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IMDResponseError(f"{context} returned malformed or non-UTF-8 JSON") from exc


def assert_application_success(payload: Any, *, context: str) -> None:
    """Reject common API error envelopes without declaring data rows valid."""
    if not isinstance(payload, dict):
        return
    if payload.get("success") is False:
        raise IMDApplicationError(f"{context} returned success=false")
    status = str(payload.get("status", "")).strip().lower()
    if status in {"error", "failed", "failure", "unauthorized", "forbidden"}:
        raise IMDApplicationError(f"{context} returned application status={status}")
    if payload.get("error") not in (None, "", False, [], {}):
        raise IMDApplicationError(f"{context} returned an application error envelope")
    if payload.get("errors") not in (None, "", False, [], {}):
        raise IMDApplicationError(f"{context} returned an application errors envelope")


class IMDPortalClient:
    """Thread-safe, bounded-retry IMD client with in-memory JWT caching."""

    def __init__(
        self,
        *,
        api_key: str,
        email: str,
        password: str,
        timeout_seconds: float = 30.0,
        refresh_margin_seconds: int = 120,
        transport: Transport = _default_transport,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key or not email or not password:
            raise IMDConfigurationError(
                "IMD_API_KEY, IMD_API_EMAIL and IMD_API_PASSWORD are required in backend secrets"
            )
        self._api_key = api_key.strip()
        self._email = email.strip()
        self._password = password
        self.timeout_seconds = timeout_seconds
        self.refresh_margin_seconds = max(5, refresh_margin_seconds)
        self._transport = transport
        self._clock = clock
        self._sleep = sleep
        self._token = ""
        self._token_expires_at = 0.0
        self._token_refresh_at = 0.0
        self._refreshing = False
        self._condition = threading.Condition()

    @classmethod
    def from_environment(cls, **kwargs: Any) -> "IMDPortalClient":
        return cls(
            api_key=os.getenv("IMD_API_KEY", ""),
            email=os.getenv("IMD_API_EMAIL", ""),
            password=os.getenv("IMD_API_PASSWORD", ""),
            **kwargs,
        )

    def _token_is_usable(self) -> bool:
        return bool(self._token and self._clock() < self._token_refresh_at)

    def invalidate_token(self) -> None:
        with self._condition:
            self._token = ""
            self._token_expires_at = 0.0
            self._token_refresh_at = 0.0

    def _request_new_token(self) -> tuple[str, int]:
        body = json.dumps({"email": self._email, "password": self._password}).encode("utf-8")
        last_status: Optional[int] = None
        for attempt in range(2):
            try:
                status, headers, response_body = self._transport(
                    "POST", TOKEN_ENDPOINT,
                    {"Content-Type": "application/json", "Accept": "application/json"},
                    body, self.timeout_seconds,
                )
            except (OSError, TimeoutError) as exc:
                if attempt == 0:
                    self._sleep(0.5)
                    continue
                raise IMDAuthenticationError("IMD token endpoint is unreachable after 2 attempts") from exc
            last_status = status
            if status in {429} or 500 <= status <= 599:
                if attempt == 0:
                    self._sleep(0.5)
                    continue
            if status != 200:
                raise IMDAuthenticationError(
                    f"IMD token request failed with HTTP {status}; verify account credentials and portal status"
                )
            if "json" not in str(headers.get("Content-Type", headers.get("content-type", ""))).lower():
                raise IMDAuthenticationError("IMD token endpoint returned a non-JSON content type")
            payload = _json(response_body, context="IMD token endpoint")
            assert_application_success(payload, context="IMD token endpoint")
            if not isinstance(payload, dict):
                raise IMDAuthenticationError("IMD token response is not a JSON object")
            token = str(payload.get("access_token") or "").strip()
            try:
                expires_in = int(payload.get("expires_in"))
            except (TypeError, ValueError) as exc:
                raise IMDAuthenticationError("IMD token response has invalid expires_in") from exc
            if not token or expires_in <= 0:
                raise IMDAuthenticationError("IMD token response is missing a usable access_token or expiry")
            return token, expires_in
        raise IMDAuthenticationError(f"IMD token request failed after 2 attempts (last HTTP {last_status})")

    def access_token(self) -> str:
        with self._condition:
            if self._token_is_usable():
                return self._token
            while self._refreshing:
                if not self._condition.wait(timeout=self.timeout_seconds + 2):
                    raise IMDAuthenticationError("Timed out waiting for the in-process IMD token refresh")
                if self._token_is_usable():
                    return self._token
            self._refreshing = True
        try:
            token, expires_in = self._request_new_token()
            with self._condition:
                self._token = token
                # Retain the exact server-provided lifetime; usability applies
                # the early-refresh margin instead of inventing another expiry.
                issued_at = self._clock()
                self._token_expires_at = issued_at + float(expires_in)
                margin = min(float(self.refresh_margin_seconds), max(1.0, float(expires_in) * 0.10))
                self._token_refresh_at = self._token_expires_at - margin
                return token
        finally:
            with self._condition:
                self._refreshing = False
                self._condition.notify_all()

    def download_raw(self, endpoint_name: str) -> HTTPResult:
        """Download one documented endpoint without interpreting its schema."""
        if endpoint_name not in AWS_ENDPOINTS:
            raise ValueError(f"Unsupported IMD endpoint name: {endpoint_name}")
        url = AWS_ENDPOINTS[endpoint_name]
        last_status: Optional[int] = None
        for attempt in range(2):
            token = self.access_token()
            headers = {
                "Accept": "application/json",
                "X-API-KEY": self._api_key,
                "Authorization": f"Bearer {token}",
                "User-Agent": "SkyGuard-SIH26073-private-inspector/1.0",
            }
            try:
                status, response_headers, body = self._transport(
                    "GET", url, headers, None, self.timeout_seconds,
                )
            except (OSError, TimeoutError) as exc:
                if attempt == 0:
                    self._sleep(0.5)
                    continue
                raise IMDResponseError(f"{endpoint_name} is unreachable after 2 attempts") from exc
            last_status = status
            if status == 401 and attempt == 0:
                self.invalidate_token()
                continue
            if status != 200:
                hint = ""
                if status in {401, 403}:
                    hint = "; verify key status, account match and registered source IP"
                elif status == 429:
                    hint = "; request limit reached, stop polling and inspect portal usage"
                raise IMDResponseError(f"{endpoint_name} returned HTTP {status}{hint}")
            content_type = str(response_headers.get("Content-Type", response_headers.get("content-type", "")))
            if "json" not in content_type.lower():
                raise IMDResponseError(f"{endpoint_name} returned non-JSON content type {content_type!r}")
            payload = _json(body, context=endpoint_name)
            return HTTPResult(
                endpoint_name=endpoint_name, url=url, status=status,
                headers=response_headers, body=body, payload=payload,
                retrieved_at_utc=_utc_now(),
            )
        raise IMDResponseError(f"{endpoint_name} failed after 2 attempts (last HTTP {last_status})")


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def structural_report(payload: Any, *, max_depth: int = 4) -> dict[str, Any]:
    """Describe JSON shape without copying station IDs or observation values."""
    def walk(value: Any, depth: int) -> dict[str, Any]:
        result: dict[str, Any] = {"type": _type_name(value)}
        if depth >= max_depth:
            result["truncated"] = True
            return result
        if isinstance(value, dict):
            keys = sorted(str(key) for key in value)
            result["keys"] = keys
            result["fields"] = {str(key): walk(item, depth + 1) for key, item in sorted(value.items())}
        elif isinstance(value, list):
            result["length"] = len(value)
            type_counts: dict[str, int] = {}
            for item in value:
                name = _type_name(item)
                type_counts[name] = type_counts.get(name, 0) + 1
            result["item_type_counts"] = type_counts
            if value and all(isinstance(item, dict) for item in value):
                all_keys = sorted({str(key) for item in value for key in item})
                result["object_keys"] = all_keys
                result["field_profiles"] = {
                    key: {
                        "present": sum(key in item for item in value),
                        "null": sum(item.get(key) is None for item in value if key in item),
                        "types": sorted({_type_name(item[key]) for item in value if key in item}),
                    }
                    for key in all_keys
                }
            elif value:
                result["first_item_shape"] = walk(value[0], depth + 1)
        return result

    report = walk(payload, 0)
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    report["schema_fingerprint_sha256"] = hashlib.sha256(canonical).hexdigest()
    report["contains_sample_values"] = False
    return report


def archive_download(result: HTTPResult, root: Path) -> tuple[Path, Path, Path]:
    """Write exact raw bytes, a safe receipt and a value-free shape report."""
    retrieved = datetime.fromisoformat(result.retrieved_at_utc.replace("Z", "+00:00"))
    stamp = retrieved.strftime("%Y%m%dT%H%M%S.%fZ")
    target_dir = Path(root) / retrieved.strftime("%Y/%m/%d") / result.endpoint_name
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_path = target_dir / f"{stamp}.json"
    receipt_path = target_dir / f"{stamp}.receipt.json"
    shape_path = target_dir / f"{stamp}.shape.json"
    for path in (raw_path, receipt_path, shape_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite immutable IMD artifact: {path}")
    raw_path.write_bytes(result.body)
    digest = hashlib.sha256(result.body).hexdigest()
    safe_headers = {
        key: value for key, value in result.headers.items()
        if key.lower() in {"content-type", "content-length", "date", "etag", "last-modified", "x-request-id"}
    }
    receipt = {
        "source": "IMD_AUTHENTICATED_AWS_API",
        "stage": "download_and_inspection_only",
        "endpoint_name": result.endpoint_name,
        "url": result.url,
        "http_status": result.status,
        "retrieved_at_utc": result.retrieved_at_utc,
        "payload_sha256": digest,
        "payload_bytes": len(result.body),
        "response_headers": safe_headers,
        "credentials_recorded": False,
        "normalized": False,
        "observation_claimed": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    shape_path.write_text(json.dumps(structural_report(result.payload), indent=2), encoding="utf-8")
    return raw_path, receipt_path, shape_path

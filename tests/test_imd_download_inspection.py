import hashlib
import json
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.providers.imd_portal import (
    IMDApplicationError,
    IMDAuthenticationError,
    IMDPortalClient,
    IMDResponseError,
    archive_download,
    assert_application_success,
    structural_report,
)


JSON_HEADERS = {"Content-Type": "application/json"}


class Clock:
    def __init__(self):
        self.value = 1_000.0

    def __call__(self):
        return self.value


def test_token_uses_returned_expiry_and_refreshes_shortly_before_it():
    clock = Clock()
    token_calls = 0

    def transport(method, url, headers, body, timeout):
        nonlocal token_calls
        token_calls += 1
        return 200, JSON_HEADERS, json.dumps({
            "access_token": f"token-{token_calls}", "token_type": "Bearer", "expires_in": 100,
        }).encode()

    client = IMDPortalClient(
        api_key="fake", email="fake@example.invalid", password="fake",
        transport=transport, clock=clock, refresh_margin_seconds=10,
    )
    assert client.access_token() == "token-1"
    clock.value += 89
    assert client.access_token() == "token-1"
    clock.value += 2
    assert client.access_token() == "token-2"
    assert token_calls == 2


def test_concurrent_callers_share_one_in_process_token_request():
    token_calls = 0
    lock = threading.Lock()

    def transport(method, url, headers, body, timeout):
        nonlocal token_calls
        with lock:
            token_calls += 1
        time.sleep(0.05)
        return 200, JSON_HEADERS, b'{"access_token":"shared","expires_in":3600}'

    client = IMDPortalClient(
        api_key="fake", email="fake@example.invalid", password="fake", transport=transport,
    )
    results = []
    threads = [threading.Thread(target=lambda: results.append(client.access_token())) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == ["shared"] * 8
    assert token_calls == 1


def test_authentication_failure_is_actionable_and_does_not_leak_body_or_password():
    def transport(method, url, headers, body, timeout):
        return 401, JSON_HEADERS, b'{"error":"password=fake-secret"}'

    client = IMDPortalClient(
        api_key="fake", email="fake@example.invalid", password="fake-secret", transport=transport,
    )
    with pytest.raises(IMDAuthenticationError) as raised:
        client.access_token()
    message = str(raised.value)
    assert "HTTP 401" in message
    assert "fake-secret" not in message


def test_malformed_json_and_application_errors_are_rejected():
    with pytest.raises(IMDResponseError, match="malformed"):
        from skyguard.providers.imd_portal import _json
        _json(b"not-json", context="aws_data")
    with pytest.raises(IMDApplicationError, match="success=false"):
        assert_application_success({"success": False, "data": []}, context="aws_data")
    with pytest.raises(IMDApplicationError, match="error envelope"):
        assert_application_success({"error": "temporarily unavailable"}, context="aws_data")


def test_structural_report_contains_no_values_and_detects_schema_change():
    first = [{"station_secret": "ABC", "temperature": 20.5}]
    second = [{"station_secret": "XYZ", "temperature": 20.5, "new_field": 1}]
    report = structural_report(first)
    serialized = json.dumps(report)
    assert "ABC" not in serialized
    assert report["contains_sample_values"] is False
    assert report["schema_fingerprint_sha256"] != structural_report(second)["schema_fingerprint_sha256"]


def test_archive_preserves_exact_bytes_and_safe_metadata(tmp_path):
    from skyguard.providers.imd_portal import HTTPResult

    body = b'[{"synthetic_field":"synthetic_value"}]'
    result = HTTPResult(
        endpoint_name="aws_data", url="https://api.imd.gov.in/api/v1/aws_data",
        status=200, headers={**JSON_HEADERS, "Authorization": "must-not-persist"},
        body=body, payload=json.loads(body), retrieved_at_utc="2026-09-23T01:02:03.004Z",
    )
    raw_path, receipt_path, shape_path = archive_download(result, tmp_path)
    assert raw_path.read_bytes() == body
    receipt = json.loads(receipt_path.read_text())
    assert receipt["payload_sha256"] == hashlib.sha256(body).hexdigest()
    assert receipt["normalized"] is False and receipt["observation_claimed"] is False
    assert "Authorization" not in json.dumps(receipt)
    assert "synthetic_value" not in shape_path.read_text()


def test_download_retries_one_unauthorized_response_with_new_token():
    token_number = 0
    get_number = 0

    def transport(method, url, headers, body, timeout):
        nonlocal token_number, get_number
        if method == "POST":
            token_number += 1
            return 200, JSON_HEADERS, json.dumps({
                "access_token": f"jwt-{token_number}", "expires_in": 3600,
            }).encode()
        get_number += 1
        if get_number == 1:
            return 401, JSON_HEADERS, b'{"error":"expired"}'
        assert headers["Authorization"] == "Bearer jwt-2"
        return 200, JSON_HEADERS, b'[]'

    client = IMDPortalClient(
        api_key="fake", email="fake@example.invalid", password="fake", transport=transport,
    )
    result = client.download_raw("aws_data")
    assert result.payload == []
    assert token_number == 2 and get_number == 2

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.providers.imd_api import IMDAWSAPIProvider


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_provider_requires_api_key_and_jwt_source(monkeypatch):
    monkeypatch.setenv("IMD_API_KEY", "key")
    monkeypatch.delenv("IMD_API_JWT_TOKEN", raising=False)
    monkeypatch.delenv("IMD_API_TOKEN", raising=False)
    monkeypatch.delenv("IMD_API_EMAIL", raising=False)
    monkeypatch.delenv("IMD_API_PASSWORD", raising=False)
    assert not IMDAWSAPIProvider().configured


def test_static_jwt_sends_both_required_headers(monkeypatch):
    monkeypatch.setenv("IMD_API_KEY", "key")
    monkeypatch.setenv("IMD_API_JWT_TOKEN", "jwt")
    provider = IMDAWSAPIProvider()
    assert provider.auth_headers == {"X-API-KEY": "key", "Authorization": "Bearer jwt"}


def test_password_flow_fetches_and_reuses_short_lived_jwt(monkeypatch):
    monkeypatch.setenv("IMD_API_KEY", "key")
    monkeypatch.setenv("IMD_API_EMAIL", "user@example.invalid")
    monkeypatch.setenv("IMD_API_PASSWORD", "secret")
    monkeypatch.delenv("IMD_API_JWT_TOKEN", raising=False)
    monkeypatch.delenv("IMD_API_TOKEN", raising=False)
    calls = []

    def fake_open(request, timeout):
        calls.append(request)
        return Response({"access_token": "generated-jwt", "expires_in": 3600})

    with patch("urllib.request.urlopen", side_effect=fake_open):
        provider = IMDAWSAPIProvider()
        assert provider.auth_headers["Authorization"] == "Bearer generated-jwt"
        assert provider.auth_headers["Authorization"] == "Bearer generated-jwt"
    assert len(calls) == 1
    assert calls[0].full_url.endswith("/api/oauth/token.php")
    assert json.loads(calls[0].data) == {
        "email": "user@example.invalid", "password": "secret"
    }

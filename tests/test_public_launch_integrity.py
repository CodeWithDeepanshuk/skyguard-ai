"""Public launch regressions: missing evidence must never become normal telemetry."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skyguard.api.app import create_app
from skyguard.live.metar import MetarLiveService, LIVE_PRESENTATION_CONTRACT


def test_catalog_station_without_reports_has_no_generated_trace():
    service = MetarLiveService(ROOT)
    service.payload = {"readings": [], "latest": []}
    station = next(iter(service.stations))
    assert service.readings(station_id=station) == []
    assert service.payload == {"readings": [], "latest": []}


def test_contaminated_cache_is_invalidated_without_rewriting_audit_file(tmp_path):
    service = MetarLiveService(ROOT)
    service.cache_path = tmp_path / "latest.json"
    evidence = {"presentation_contract": "r0_evidence_no_fabricated_health_v1",
        "readings": [{"source_quality": "VALIDATED_AWS_TELEMETRY"}],
        "latest": [{"station_id": "synthetic"}], "reporting_stations": 543,
        "observation_count": 12000, "latest_observation_utc": "2026-09-12T00:00:00Z"}
    service.cache_path.write_text(json.dumps(evidence))
    result = service._load_cache()
    assert result["readings"] == []
    assert result["latest"] == []
    assert result["observation_count"] == 0
    assert result["reporting_stations"] == 0
    assert result["latest_observation_utc"] is None
    assert result["presentation_contract"] == LIVE_PRESENTATION_CONTRACT
    assert json.loads(service.cache_path.read_text()) == evidence


def test_real_fetch_never_augments_with_generated_buddies(tmp_path):
    service = MetarLiveService(ROOT)
    service.cache_path = tmp_path / "clean.json"
    raw = [{"icaoId": "VIDP", "reportTime": "2026-09-12T00:00:00Z",
        "temp": 31, "dewp": 24, "altim": 1005, "rawOb": "METAR VIDP TEST"}]
    normalized = service._normalize(raw)
    with patch.object(service, "_request", return_value=raw), \
         patch.object(service, "_quality_alerts", return_value=[]), \
         patch.object(service, "_score", return_value=(normalized, [])) as score:
        result = service.refresh()
    score.assert_called_once_with(normalized, [])
    assert result["reporting_stations"] == 1
    assert result["observation_count"] == 1
    assert result["stations_without_observations"] == len(service.stations) - 1


def test_public_mode_disallows_shared_mutations_and_never_falls_back_to_history():
    with patch.dict('os.environ', {"SKYGUARD_PUBLIC_MODE": "true"}):
        app = create_app(ROOT, ":memory:")
    app.state.live.payload = {"incidents": []}
    try:
        with TestClient(app) as client:
            assert client.get('/api/incidents?mode=live').json() == []
            assert client.get('/api/incidents?mode=offline&limit=1').json()
            for route in ('/api/live/inject-fault', '/api/live/clear-faults', '/api/replay/reset'):
                assert client.post(route).status_code == 403
            assert client.get('/health').json()['public_read_only'] is True
    finally:
        app.state.runtime.store.close()

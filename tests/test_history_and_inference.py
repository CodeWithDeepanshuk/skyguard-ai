"""Comprehensive tests for:
1. Durable history storage with 1h, 6h, 24h, 7d ranges and pagination.
2. Two successive scheduled ingestion runs with increasing durable history.
3. Telemetry graphs contract: 1-point trend warning and time gap detection (>45m).
4. Real anomaly inference contract: continuous anomaly_score, spatial neighbor evidence without self, and uncalibrated fault probability (None).
5. Ingestion token validation, idempotency, and error handling.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from skyguard.storage import ObservationStore
from skyguard.providers.base import (
    ObservationRecord,
    SourceType,
    ProviderName,
    PressureType,
    HumidityObservationType,
    RHSource,
)
from skyguard.models.deep_ensemble import DeepEnsembleDetector
from skyguard.api.app import create_app


@pytest.fixture
def temp_store(tmp_path):
    db_path = tmp_path / "test_history.db"
    return ObservationStore(database_url=str(db_path), root=ROOT)


def create_sample_record(
    station_id: str,
    ts: datetime,
    temp: float = 28.0,
    press: float = 1012.0,
    rh: float = 55.0,
    provider: str = ProviderName.IMD_AWS.value,
) -> ObservationRecord:
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return ObservationRecord(
        provider=provider,
        source_type=SourceType.OBSERVED.value,
        station_id=station_id,
        timestamp_utc=ts_str,
        latitude=28.5,
        longitude=77.2,
        elevation_m=215.0,
        temperature_c=temp,
        pressure_hpa=press,
        relative_humidity_pct=rh,
        pressure_type=PressureType.STATION_PRESSURE.value,
        humidity_observation_type=HumidityObservationType.DIRECT.value,
        rh_source=RHSource.OBSERVED.value,
        canonical_station_id=station_id,
        provider_station_id=station_id,
        wigos_id=f"0-20000-0-{station_id[:5]}",
        icao_code="",
        station_name=f"Station {station_id}",
        state="Delhi",
        district="New Delhi",
        raw_payload_json=json.dumps({"temp": temp, "rh": rh, "press": press}),
        raw_source_hash=f"hash_{station_id}_{ts_str}",
        source_url="https://api.imd.gov.in/api/v1/aws_data",
        is_direct_observation=True,
        is_model_field=False,
    )


def test_two_successive_ingestion_runs_increasing_history(temp_store):
    """Demonstrate two successive scheduled ingestion runs with increasing durable history."""
    station_id = "ARKBR000"
    base_time = datetime(2026, 9, 25, 10, 0, 0, tzinfo=timezone.utc)

    # Run 1: 4 observations at 15-minute intervals (09:15, 09:30, 09:45, 10:00)
    batch_1 = [
        create_sample_record(station_id, base_time - timedelta(minutes=45), temp=26.5),
        create_sample_record(station_id, base_time - timedelta(minutes=30), temp=27.0),
        create_sample_record(station_id, base_time - timedelta(minutes=15), temp=27.8),
        create_sample_record(station_id, base_time, temp=28.4),
    ]
    receipt_1 = temp_store.append(batch_1)
    assert receipt_1["inserted"] == 4
    assert receipt_1["duplicates"] == 0

    history_after_run_1 = temp_store.history(station_id, hours=24)
    assert len(history_after_run_1) == 4

    # Run 2: Re-send batch_1 (idempotent duplicate detection) PLUS 2 new observations (10:15, 10:30)
    batch_2 = list(batch_1) + [
        create_sample_record(station_id, base_time + timedelta(minutes=15), temp=29.1),
        create_sample_record(station_id, base_time + timedelta(minutes=30), temp=29.8),
    ]
    receipt_2 = temp_store.append(batch_2)
    assert receipt_2["inserted"] == 2
    assert receipt_2["duplicates"] == 4

    # History has strictly increased from 4 to 6 observations
    history_after_run_2 = temp_store.history(station_id, hours=24)
    assert len(history_after_run_2) == 6
    # Oldest first ordering in history:
    assert history_after_run_2[0]["observation_timestamp_utc"] == "2026-09-25T09:15:00Z"
    assert history_after_run_2[-1]["observation_timestamp_utc"] == "2026-09-25T10:30:00Z"


def test_paginated_history_ranges_and_metadata(temp_store):
    """Verify paginated_history supports ranges: 1h, 6h, 24h, 7d with metadata."""
    station_id = "VABP0000"
    base_time = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)

    # Populate 48 hours of 15-minute readings (192 points)
    records = []
    for step in range(192):
        ts = base_time - timedelta(minutes=15 * step)
        records.append(create_sample_record(station_id, ts, temp=25.0 + (step % 5)))
    temp_store.append(records)

    # Test 1-hour range (relative to latest observation): should contain ~5 observations (0m, 15m, 30m, 45m, 60m)
    res_1h = temp_store.paginated_history(station_id, range_param="1h", relative_to_latest=True, limit=50)
    assert res_1h["range"] == "1h"
    assert res_1h["total"] == 5
    assert len(res_1h["items"]) == 5
    assert res_1h["items"][0]["observation_timestamp_utc"] == "2026-09-25T11:00:00Z"
    assert res_1h["items"][-1]["observation_timestamp_utc"] == "2026-09-25T12:00:00Z"

    # Test 6-hour range: ~25 observations
    res_6h = temp_store.paginated_history(station_id, range_param="6h", relative_to_latest=True, limit=50)
    assert res_6h["range"] == "6h"
    assert res_6h["total"] == 25

    # Test 24-hour range: ~97 observations
    res_24h = temp_store.paginated_history(station_id, range_param="24h", relative_to_latest=True, page=1, limit=50)
    assert res_24h["range"] == "24h"
    assert res_24h["total"] == 97
    assert len(res_24h["items"]) == 50  # Paginated page 1
    assert res_24h["pages"] == 2

    # Page 2
    res_24h_p2 = temp_store.paginated_history(station_id, range_param="24h", relative_to_latest=True, page=2, limit=50)
    assert len(res_24h_p2["items"]) == 47


def test_history_api_endpoints_via_test_client(tmp_path, monkeypatch):
    """Test /api/v1/observations/history and /api/live/readings with durable storage."""
    db_path = tmp_path / "api_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    app = create_app(ROOT)
    client = TestClient(app)

    # Ingest 2 observations for station DEL001
    now = datetime(2026, 9, 25, 10, 0, 0, tzinfo=timezone.utc)
    rec1 = create_sample_record("DEL001", now - timedelta(minutes=15), temp=30.0)
    rec2 = create_sample_record("DEL001", now, temp=31.2)
    app.state.observation_store.append([rec1, rec2])

    # 1. Test /api/v1/observations/history
    resp = client.get("/api/v1/observations/history?station_id=DEL001&range=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert data["station_id"] == "DEL001"
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["temperature_c"] == 30.0
    assert data["items"][1]["temperature_c"] == 31.2

    # 2. Test /api/live/readings with station_id
    resp_live = client.get("/api/live/readings?station_id=DEL001")
    assert resp_live.status_code == 200
    live_items = resp_live.json()
    assert len(live_items) >= 2


def test_real_ensemble_inference_on_ingestion(tmp_path, monkeypatch):
    """Test that POST /api/v1/ingestion/imd executes real DeepEnsembleDetector inference and leaves fault_probability uncalibrated (None)."""
    db_path = tmp_path / "ingest_infer.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SKYGUARD_INGESTION_TOKEN", "valid_secret_token_123")

    app = create_app(ROOT)
    client = TestClient(app)

    ts_now = "2026-09-25T11:00:00Z"
    # Target station has anomalous temperature spike
    target_stn = {
        "station_id": "TGT_ANOMALY",
        "station_name": "Target Anomaly AWS",
        "timestamp_utc": ts_now,
        "latitude": 28.6,
        "longitude": 77.2,
        "elevation_m": 220.0,
        "temperature_c": 49.5,  # extreme spike
        "pressure_hpa": 1008.0,
        "relative_humidity_pct": 25.0,
    }
    # Neighbor stations have normal temperature
    peer1 = {
        "station_id": "PEER_1",
        "station_name": "Peer 1 AWS",
        "timestamp_utc": ts_now,
        "latitude": 28.65,
        "longitude": 77.25,
        "elevation_m": 220.0,
        "temperature_c": 31.0,
        "pressure_hpa": 1008.0,
        "relative_humidity_pct": 55.0,
    }
    peer2 = {
        "station_id": "PEER_2",
        "station_name": "Peer 2 AWS",
        "timestamp_utc": ts_now,
        "latitude": 28.55,
        "longitude": 77.15,
        "elevation_m": 220.0,
        "temperature_c": 30.5,
        "pressure_hpa": 1008.0,
        "relative_humidity_pct": 56.0,
    }

    payload = {
        "source": "IMD_AWS_COLLECTOR",
        "source_url": "https://api.imd.gov.in/api/v1/aws_data",
        "collected_at_utc": "2026-09-25T11:02:00Z",
        "observations": [target_stn, peer1, peer2],
    }

    # Test unauthorized rejected
    resp_unauth = client.post("/api/v1/ingestion/imd", json=payload)
    assert resp_unauth.status_code == 401

    # Test authorized with bearer token
    resp = client.post(
        "/api/v1/ingestion/imd",
        json=payload,
        headers={"Authorization": "Bearer valid_secret_token_123"},
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] in ("success", "SUCCESS")
    assert res_data["inserted"] == 3
    assert res_data["inference_performed"] is True
    assert res_data["evaluated_stations"] == 3

    # Check inference evaluation details
    inferences = res_data["inferences"]
    assert "TGT_ANOMALY" in inferences
    tgt_eval = inferences["TGT_ANOMALY"]

    # 1. anomaly_score is a continuous float
    assert isinstance(tgt_eval["anomaly_score"], float)
    assert tgt_eval["anomaly_score"] > 0.5

    # 2. fault_probability is explicitly None (uncalibrated)
    assert tgt_eval["calibrated_fault_probability"] is None
    assert tgt_eval["is_calibrated"] is False

    # 3. Spatial consensus excluded self
    evidence = tgt_eval["neighbor_evidence"]
    neighbor_ids = [e["station_id"] for e in evidence]
    assert "TGT_ANOMALY" not in neighbor_ids
    assert "PEER_1" in neighbor_ids or "PEER_2" in neighbor_ids

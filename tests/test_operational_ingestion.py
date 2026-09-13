from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from skyguard.operational import OperationalQC
from skyguard.providers.base import ObservationRecord, PressureType, SourceType
from skyguard.providers.imd_api import IMDAWSAPIProvider
from skyguard.storage import ObservationStore


def record(
    station: str,
    timestamp: str,
    *,
    temperature: float | None = 25.0,
    pressure: float | None = 1005.0,
    humidity: float | None = 60.0,
    pressure_type: str = PressureType.MEAN_SEA_LEVEL_PRESSURE.value,
    message_id: str = "",
    raw_hash: str = "",
) -> ObservationRecord:
    return ObservationRecord(
        provider="IMD_WIS2",
        source_type=SourceType.OBSERVED.value,
        station_id=station,
        provider_station_id=station,
        canonical_station_id=station,
        timestamp_utc=timestamp,
        latitude=28.6,
        longitude=77.2,
        temperature_c=temperature,
        pressure_hpa=pressure,
        pressure_type=pressure_type,
        relative_humidity_pct=humidity,
        message_id=message_id,
        raw_source_hash=raw_hash,
    )


def row(item: ObservationRecord) -> dict[str, object]:
    payload = item.to_dict()
    payload["observation_timestamp_utc"] = payload.pop("timestamp_utc")
    return payload


def test_provider_message_id_deduplicates_different_cache_envelopes(tmp_path: Path) -> None:
    first = record("A", "2026-09-13T00:00:00Z", message_id="report-1", raw_hash="a" * 64)
    relay = record("A", "2026-09-13T00:00:00Z", message_id="report-1", raw_hash="b" * 64)
    assert first.observation_key == relay.observation_key
    store = ObservationStore(str(tmp_path / "observations.db"), root=Path(__file__).parents[1])
    receipt = store.append([first, relay])
    assert receipt["inserted"] == 1
    assert receipt["duplicates"] == 1


def test_sqlite_store_survives_new_repository_instance(tmp_path: Path) -> None:
    path = tmp_path / "observations.db"
    first = ObservationStore(str(path), root=Path(__file__).parents[1])
    first.append([record("A", "2026-09-13T00:00:00Z")])
    reopened = ObservationStore(str(path), root=Path(__file__).parents[1])
    assert reopened.ingestion_health()["observation_records"] == 1


def test_pressure_spatial_qc_never_mixes_semantics() -> None:
    target = row(record("A", "2026-09-13T12:00:00Z", pressure=1010.0))
    history = [row(record("A", f"2026-09-13T{hour:02d}:00:00Z", pressure=1009.0)) for hour in range(6)]
    neighbors = [
        row(record(f"N{index}", "2026-09-13T12:00:00Z", pressure=650.0,
                   pressure_type=PressureType.STATION_PRESSURE.value))
        for index in range(4)
    ]
    result = OperationalQC().analyze(
        target, history, neighbors, now=datetime(2026, 9, 13, 12, 5, tzinfo=timezone.utc)
    )
    assert result.neighbor_support["pressure"] == 0
    assert result.pressure_spatial_qc == "INSUFFICIENT_SAME_TYPE_NEIGHBORS"
    assert not any(item.code == "BUDDY_DISAGREEMENT" and item.sensor == "pressure" for item in result.evidence)


def test_isolated_temporal_and_spatial_spike_is_probable_fault() -> None:
    target = row(record("A", "2026-09-13T12:00:00Z", temperature=48.0))
    history = [row(record("A", f"2026-09-13T{hour:02d}:00:00Z", temperature=30.0)) for hour in range(6, 12)]
    neighbors = [row(record(f"N{index}", "2026-09-13T12:00:00Z", temperature=29.5 + index / 10)) for index in range(4)]
    result = OperationalQC().analyze(
        target, history, neighbors, now=datetime(2026, 9, 13, 12, 5, tzinfo=timezone.utc)
    )
    assert result.decision == "PROBABLE_SENSOR_FAULT"
    assert result.score_label == "uncalibrated_evidence_score"
    assert result.calibrated_probability_available is False
    assert {item.stage for item in result.evidence} >= {"temporal", "spatial"}


def test_coherent_regional_change_is_weather_not_single_station_fault() -> None:
    target = row(record("A", "2026-09-13T12:00:00Z", temperature=20.0))
    history = [row(record("A", f"2026-09-13T{hour:02d}:00:00Z", temperature=30.0)) for hour in range(6, 12)]
    neighbors = []
    for index, value in enumerate((19.8, 20.2, 20.5, 19.9)):
        item = row(record(f"N{index}", "2026-09-13T12:00:00Z", temperature=value))
        item["temperature_c_delta"] = -9.5
        neighbors.append(item)
    result = OperationalQC().analyze(
        target, history, neighbors, now=datetime(2026, 9, 13, 12, 5, tzinfo=timezone.utc)
    )
    assert result.decision == "GENUINE_WEATHER_EVENT"
    assert any(item.code == "REGIONAL_COHERENT_CHANGE" for item in result.evidence)


def test_future_history_is_excluded_and_gap_is_separate_decision() -> None:
    target = row(record("A", "2026-09-13T12:00:00Z"))
    before = row(record("A", "2026-09-13T11:00:00Z"))
    after = row(record("A", "2026-09-13T13:00:00Z", temperature=60.0))
    result = OperationalQC().analyze(target, [before, after], now=datetime(2026, 9, 13, 12, 5, tzinfo=timezone.utc))
    assert result.history_observations == 1

    cadence = [
        row(record("A", (datetime(2026, 9, 12, tzinfo=timezone.utc) + timedelta(hours=i)).isoformat()))
        for i in range(8)
    ]
    communication = OperationalQC().assess_communication(
        "A", cadence, now=datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)
    )
    assert communication["decision"] == "COMMUNICATION_FAILURE"


def test_imd_api_normalization_preserves_direct_rh_and_mslp() -> None:
    provider = IMDAWSAPIProvider()
    payload = [{
        "CALL_SIGN": "DLH001", "STATION": "Delhi Test", "STATE": "DELHI",
        "DISTRICT": "NEW DELHI", "DATE": "2026-09-13", "TIME": "06:30:00",
        "CURR_TEMP": "31.2", "MSLP": "1007.8", "RH": "74",
        "LATITUDE": "28.61", "LONGITUDE": "77.21",
    }]
    rows = provider._normalize_payload(payload, provider.endpoint)
    assert len(rows) == 1
    assert rows[0].pressure_type == PressureType.MEAN_SEA_LEVEL_PRESSURE.value
    assert rows[0].humidity_observation_type == "DIRECT"
    assert rows[0].temperature_c == 31.2

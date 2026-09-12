import pytest

from skyguard.features.adaptive_buddy import buddy_expectation, haversine_km
from skyguard.providers.base import ObservationRecord, SourceType


def test_model_value_cannot_be_direct_observation():
    with pytest.raises(ValueError):
        ObservationRecord("model", SourceType.REFERENCE_MODEL.value, "x", "2026-01-01T00:00:00Z", 20, 75,
                          is_model_field=True, is_direct_observation=True)


def test_observed_requires_direct_evidence():
    with pytest.raises(ValueError):
        ObservationRecord("unknown", SourceType.OBSERVED.value, "x", "2026-01-01T00:00:00Z", 20, 75,
                          is_direct_observation=False)


def test_buddy_check_excludes_target_and_expands_radius():
    rows = [
        {"station_id":"target", "latitude":20, "longitude":75, "temperature_c":999},
        {"station_id":"a", "latitude":20.4, "longitude":75, "temperature_c":25},
        {"station_id":"b", "latitude":20.5, "longitude":75, "temperature_c":27},
    ]
    result = buddy_expectation("target", 20, 75, rows, "temperature_c")
    assert result["available"] and result["target_excluded"]
    assert result["neighbor_ids"] == ["a", "b"]
    assert result["expected"] in (25.0, 27.0)
    assert result["radius_km"] == 100


def test_haversine_identity_and_known_scale():
    assert haversine_km(20, 75, 20, 75) == 0
    assert 110 < haversine_km(20, 75, 21, 75) < 112

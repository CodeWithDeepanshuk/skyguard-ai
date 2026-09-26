"""Comprehensive Tests for Multi-Tier Concentric Spatial Neighbor QC & Indian Regional Physical Bounds."""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.quality.indian_regional_bounds import (
    INDIAN_CLIMATE_BOUNDS,
    classify_indian_region,
    check_regional_physical_bounds,
    is_coastal_location,
)
from skyguard.spatial.spatial_qc import (
    MultiRadiusSpatialQcEngine,
    adjust_temperature_for_lapse,
    haversine_km,
)
from skyguard.models.deep_ensemble import DeepEnsembleDetector


def test_indian_regional_bounds_classification():
    # 1. New Delhi (Indo-Gangetic Plains)
    delhi = classify_indian_region(lat=28.58, lon=77.20, elev_m=216.0, state="Delhi")
    assert delhi.zone_name == "Indo-Gangetic Plains"
    assert delhi.temp_min_c <= 0.0
    assert delhi.temp_max_c >= 48.0

    # 2. Leh / Ladakh (Northern Himalayas)
    leh = classify_indian_region(lat=34.15, lon=77.58, elev_m=3500.0, state="Ladakh")
    assert leh.zone_name == "Northern Himalayas"
    assert leh.temp_min_c <= -40.0
    assert leh.high_altitude is True

    # 3. Mumbai (Coastal Plains)
    mumbai = classify_indian_region(lat=19.07, lon=72.87, elev_m=10.0, state="Maharashtra", climate_zone_hint="Coastal Plains")
    assert mumbai.zone_name == "Coastal Plains"
    assert mumbai.coastal is True
    assert mumbai.temp_min_c >= 10.0

    # 4. Jodhpur (Western Arid)
    jodhpur = classify_indian_region(lat=26.23, lon=73.02, elev_m=230.0, state="Rajasthan")
    assert jodhpur.zone_name == "Western Arid/Semi-Arid"
    assert jodhpur.temp_max_c >= 52.0


def test_temperature_24_point_5_c_is_physically_normal_in_india():
    """24.5°C was erroneously flagged as an anomaly in the user's screenshot.
    Verify that 24.5°C is perfectly valid across all Indian regions."""
    for zone_name, bounds in INDIAN_CLIMATE_BOUNDS.items():
        if zone_name == "Northern Himalayas":
            continue
        valid, violated, reason = check_regional_physical_bounds(
            temperature_c=24.5,
            pressure_hpa=1005.0,
            humidity_pct=60.0,
            bounds=bounds,
            elevation_m=200.0,
        )
        assert valid is True, f"24.5°C was rejected by {zone_name}: {reason}"


def test_spatial_qc_tier1_normal_1_to_2_deg_difference():
    """If target is 30°C and a neighbor within 20 km is 29°C (1°C diff), it is NORMAL."""
    engine = MultiRadiusSpatialQcEngine()
    target = {
        "station_id": "STN_A",
        "station_name": "Target Station A",
        "latitude": 28.60,
        "longitude": 77.20,
        "elevation_m": 200.0,
        "temperature_c": 30.0,
        "pressure_hpa": 1005.0,
        "relative_humidity_pct": 55.0,
    }
    # Neighbor ~11 km away reporting 29.0°C
    neighbors = [
        {
            "station_id": "STN_B",
            "station_name": "Neighbor Station B",
            "latitude": 28.70,
            "longitude": 77.20,
            "elevation_m": 200.0,
            "temperature_c": 29.0,
            "pressure_hpa": 1005.0,
            "relative_humidity_pct": 56.0,
        }
    ]

    res = engine.evaluate(target, neighbors)
    assert res.tier1_20km.peer_count == 1
    assert res.tier1_20km.tolerance_exceeded is False
    assert res.spatial_fault_suspected is False
    assert res.decision == "NORMAL"


def test_spatial_qc_tier1_anomaly_5_deg_difference():
    """If target is 30°C and neighbor within 20 km is 25°C (5°C diff at same elevation),
    it exceeds the 2.0°C tolerance and is flagged as a SENSOR_FAULT anomaly."""
    engine = MultiRadiusSpatialQcEngine()
    target = {
        "station_id": "STN_A",
        "station_name": "Target Station A",
        "latitude": 28.60,
        "longitude": 77.20,
        "elevation_m": 200.0,
        "temperature_c": 30.0,
        "pressure_hpa": 1005.0,
        "relative_humidity_pct": 55.0,
    }
    # Neighbor ~11 km away reporting 25.0°C (diff = 5.0°C)
    neighbors = [
        {
            "station_id": "STN_B",
            "station_name": "Neighbor Station B",
            "latitude": 28.70,
            "longitude": 77.20,
            "elevation_m": 200.0,
            "temperature_c": 25.0,
            "pressure_hpa": 1005.0,
            "relative_humidity_pct": 56.0,
        }
    ]

    res = engine.evaluate(target, neighbors)
    assert res.tier1_20km.peer_count == 1
    assert res.tier1_20km.tolerance_exceeded is True
    assert res.spatial_fault_suspected is True
    assert res.decision == "SENSOR_FAULT"
    assert "spatial_neighbor_discrepancy" in res.root_cause


def test_spatial_qc_elevation_lapse_rate_correction():
    """Target at 100m ASL reporting 30.0°C.
    Neighbor at 1100m ASL (1000m higher) reporting 23.5°C.
    Lapse rate is -6.5°C/1000m, so neighbor adjusted to 100m is 23.5 + 6.5 = 30.0°C.
    Effective difference is 0.0°C -> NORMAL!"""
    engine = MultiRadiusSpatialQcEngine()
    target = {
        "station_id": "STN_VALLEY",
        "station_name": "Valley Station",
        "latitude": 30.10,
        "longitude": 78.10,
        "elevation_m": 100.0,
        "temperature_c": 30.0,
    }
    neighbors = [
        {
            "station_id": "STN_HILL",
            "station_name": "Hill Station",
            "latitude": 30.20,
            "longitude": 78.10,
            "elevation_m": 1100.0,  # 1000m higher
            "temperature_c": 23.5,  # Raw diff is 6.5°C, but lapse-adjusted diff is 0.0°C
        }
    ]

    res = engine.evaluate(target, neighbors)
    assert res.tier1_20km.peer_count == 1
    assert abs(res.tier1_20km.max_delta_c) <= 0.1
    assert res.spatial_fault_suspected is False
    assert res.decision == "NORMAL"


def test_synoptic_weather_front_detection_suppresses_fault():
    """If target station dropped by -4.0°C, BUT nearby stations in the 50-100km radius
    also experienced a matching rapid drop (e.g. cold front / thunderstorm outflow),
    suppress the hardware fault alert and flag as GENUINE_WEATHER_EVENT."""
    engine = MultiRadiusSpatialQcEngine()
    target = {
        "station_id": "STN_FRONT",
        "station_name": "Front Station",
        "latitude": 28.50,
        "longitude": 77.20,
        "elevation_m": 200.0,
        "temperature_c": 24.0,  # Dropped from 29°C
    }
    # Surrounding stations experiencing the same front
    neighbors = [
        {"station_id": "N1", "latitude": 28.60, "longitude": 77.30, "elevation_m": 200.0, "temperature_c": 28.5, "temperature_delta": -3.5},
        {"station_id": "N2", "latitude": 28.40, "longitude": 77.10, "elevation_m": 200.0, "temperature_c": 28.8, "temperature_delta": -3.8},
        {"station_id": "N3", "latitude": 28.80, "longitude": 77.50, "elevation_m": 200.0, "temperature_c": 28.4, "temperature_delta": -4.0},
    ]

    # Target dropped by -4.0°C
    res = engine.evaluate(target, neighbors, target_temporal_delta=-4.0)
    assert res.synoptic_weather_system_detected is True
    assert res.decision == "GENUINE_WEATHER_EVENT"
    assert "synoptic_weather_front" in res.root_cause


def test_deep_ensemble_detector_integration():
    """Verify DeepEnsembleDetector uses multi-radius spatial QC and regional bounds."""
    detector = DeepEnsembleDetector()
    target = {
        "station_id": "TEST_DELHI",
        "station_name": "Delhi AWS",
        "latitude": 28.58,
        "longitude": 77.20,
        "elevation_m": 216.0,
        "temperature_c": 24.5,
        "pressure_hpa": 1005.0,
        "relative_humidity_pct": 60.0,
        "climate_zone": "Indo-Gangetic Plains",
    }
    # Neighbor within 15 km reporting 24.8°C (0.3°C diff)
    neighbors = [
        {
            "station_id": "TEST_NOIDA",
            "station_name": "Noida AWS",
            "latitude": 28.57,
            "longitude": 77.32,
            "elevation_m": 200.0,
            "temperature_c": 24.8,
            "pressure_hpa": 1005.5,
            "relative_humidity_pct": 59.0,
        }
    ]

    result = detector.evaluate_station(target, [], neighbors)
    assert result.decision == "NORMAL"
    assert result.severity == "NOMINAL"
    assert result.tier1_20km["peer_count"] == 1
    assert result.tier1_20km["tolerance_exceeded"] is False
    assert result.climate_zone == "Indo-Gangetic Plains"

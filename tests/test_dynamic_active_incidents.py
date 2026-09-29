"""Test dynamic active incident evaluation and neighbor-based calculations."""
from pathlib import Path
from skyguard.quality.active_incidents import evaluate_active_network_incidents


def test_dynamic_active_incidents_calculation():
    root = Path(__file__).resolve().parents[1]

    # Create a cluster of stations with one genuine sensor fault (temperature spike)
    readings = [
        {
            "station_id": "STN_A",
            "station_name": "Station A",
            "latitude": 28.6,
            "longitude": 77.2,
            "elevation_m": 210.0,
            "temperature_c": 52.0,  # Extreme spike (+24°C from neighbors)
            "pressure_hpa": 988.0,
            "relative_humidity_pct": 65.0,
            "state": "Indo-Gangetic Plains",
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            "station_id": "STN_B",
            "station_name": "Station B",
            "latitude": 28.5,
            "longitude": 77.1,
            "elevation_m": 215.0,
            "temperature_c": 28.0,
            "pressure_hpa": 988.5,
            "relative_humidity_pct": 66.0,
            "state": "Indo-Gangetic Plains",
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            "station_id": "STN_C",
            "station_name": "Station C",
            "latitude": 28.7,
            "longitude": 77.3,
            "elevation_m": 208.0,
            "temperature_c": 28.5,
            "pressure_hpa": 988.2,
            "relative_humidity_pct": 64.0,
            "state": "Indo-Gangetic Plains",
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            "station_id": "STN_D",
            "station_name": "Station D",
            "latitude": 28.65,
            "longitude": 77.15,
            "elevation_m": 212.0,
            "temperature_c": 27.8,
            "pressure_hpa": 988.3,
            "relative_humidity_pct": 67.0,
            "state": "Indo-Gangetic Plains",
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            # Normal station reporting 100% relative humidity (monsoon/fog condition)
            "station_id": "STN_E",
            "station_name": "Station E",
            "latitude": 23.0,
            "longitude": 78.0,
            "elevation_m": 450.0,
            "temperature_c": 24.0,
            "pressure_hpa": 965.0,
            "relative_humidity_pct": 100.0,  # Should NOT violate physical bounds!
            "state": "Central Plateau",
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            "station_id": "STN_F",
            "station_name": "Station F",
            "latitude": 23.1,
            "longitude": 78.1,
            "elevation_m": 445.0,
            "temperature_c": 23.8,
            "pressure_hpa": 965.2,
            "relative_humidity_pct": 98.0,
            "state": "Central Plateau",
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
    ]

    incidents, alerts = evaluate_active_network_incidents(readings, root)

    # STN_A should be detected as an incident
    stn_a_inc = next((i for i in incidents if i["station_id"] == "STN_A"), None)
    assert stn_a_inc is not None, "STN_A must be flagged as an anomaly"
    assert stn_a_inc["affected_parameter"] == "temperature"
    assert stn_a_inc["observed_value_numeric"] == 52.0
    assert abs(stn_a_inc["residual"]) > 15.0
    assert stn_a_inc["z_spatial"] >= 3.0

    # STN_E with 100% RH in Central Plateau must NOT be flagged as a physical bounds violation
    stn_e_inc = next((i for i in incidents if i["station_id"] == "STN_E"), None)
    assert stn_e_inc is None or "bounds" not in stn_e_inc.get("root_cause", ""), (
        "100% RH in Central Plateau must not trigger a physical bounds violation"
    )


def test_mountain_elevation_pressure_tadong():
    """Verify that Tadong AWS (888.1 hPa at 1,322m ASL in Sikkim) is not flagged as a physical violation."""
    root = Path(__file__).resolve().parents[1]

    readings = [
        {
            "station_id": "5B76500A",
            "station_name": "Tadong AWS",
            "latitude": 27.3197,
            "longitude": 88.5994,
            "state": "Sikkim",
            "temperature_c": 21.4,
            "pressure_hpa": 888.1,
            "relative_humidity_pct": 78.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            "station_id": "5B76500B",
            "station_name": "Gangtok AWS",
            "latitude": 27.33,
            "longitude": 88.61,
            "state": "Sikkim",
            "temperature_c": 20.8,
            "pressure_hpa": 886.5,
            "relative_humidity_pct": 80.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
    ]

    incidents, alerts = evaluate_active_network_incidents(readings, root)
    tadong_inc = next((i for i in incidents if i["station_id"] == "5B76500A"), None)
    assert tadong_inc is None, f"Tadong 888.1 hPa must be recognized as normal mountain pressure, got: {tadong_inc}"


def test_wmo_low_humidity_scientific_bounds_and_attribution():
    """Verify that dry air (e.g. 16.0% RH in Northeast or 7.0% RH in Plains) does not trigger gross bounds violation,
    but if spatial peer consensus reveals a real sensor fault, it attributes relative_humidity with 16.0%."""
    root = Path(__file__).resolve().parents[1]

    # Cluster in Assam where peers have 88-90% RH and one faulty sensor is stuck at 16.0%
    readings = [
        {
            "station_id": "55D20514",
            "station_name": "Harinagar AWS",
            "latitude": 24.8,
            "longitude": 92.8,
            "state": "Assam",
            "temperature_c": 28.0,
            "pressure_hpa": 1008.0,
            "relative_humidity_pct": 16.0,  # Highly anomalous relative to peers (88-90%)
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            "station_id": "AS_PEER_1",
            "station_name": "Silchar AWS",
            "latitude": 24.82,
            "longitude": 92.79,
            "state": "Assam",
            "temperature_c": 28.2,
            "pressure_hpa": 1008.2,
            "relative_humidity_pct": 89.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            "station_id": "AS_PEER_2",
            "station_name": "Hailakandi AWS",
            "latitude": 24.68,
            "longitude": 92.56,
            "state": "Assam",
            "temperature_c": 28.5,
            "pressure_hpa": 1007.8,
            "relative_humidity_pct": 88.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        {
            "station_id": "AS_PEER_3",
            "station_name": "Karimganj AWS",
            "latitude": 24.86,
            "longitude": 92.35,
            "state": "Assam",
            "temperature_c": 27.9,
            "pressure_hpa": 1008.1,
            "relative_humidity_pct": 91.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
    ]

    incidents, alerts = evaluate_active_network_incidents(readings, root)
    harinagar_inc = next((i for i in incidents if i["station_id"] == "55D20514"), None)
    assert harinagar_inc is not None, "Harinagar must be detected as spatial anomaly against peer consensus"
    assert harinagar_inc["affected_parameter"] == "relative_humidity"
    assert harinagar_inc["observed_value_numeric"] == 16.0
    assert harinagar_inc["unit"] == "%"
    # Root cause should be spatial consensus / discrepancy failure, NOT a physical boundary violation
    assert "spatial" in harinagar_inc["root_cause"].lower() or "consensus" in harinagar_inc["root_cause"].lower()
    assert "boundary" not in harinagar_inc["root_cause"].lower()


def test_strict_parameter_fidelity_no_fallbacks():
    """Verify that incidents strictly attribute the exact reported parameter and never inject 
    synthetic fallbacks (25.0°C, 1013.25 hPa, 65.0% RH) into incident reports."""
    root = Path(__file__).resolve().parents[1]

    # Cluster with 1 pressure fault station and 1 humidity fault station
    readings = [
        # Target 1: Pure barometric pressure sensor fault (1048.5 hPa vs 1012 hPa peers)
        {
            "station_id": "STN_PRESS_FAULT",
            "station_name": "Pressure Anomaly Station",
            "latitude": 22.5,
            "longitude": 88.3,
            "elevation_m": 12.0,
            "temperature_c": 30.1,
            "pressure_hpa": 1048.5,
            "relative_humidity_pct": 75.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        # Target 2: Pure humidity sensor fault (12.0% vs 75% peers)
        {
            "station_id": "STN_HUMID_FAULT",
            "station_name": "Humidity Anomaly Station",
            "latitude": 22.55,
            "longitude": 88.35,
            "elevation_m": 14.0,
            "temperature_c": 30.2,
            "pressure_hpa": 1012.2,
            "relative_humidity_pct": 12.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        # Normal Peer 1
        {
            "station_id": "STN_NORM_1",
            "station_name": "Normal Peer 1",
            "latitude": 22.52,
            "longitude": 88.32,
            "elevation_m": 13.0,
            "temperature_c": 30.0,
            "pressure_hpa": 1012.0,
            "relative_humidity_pct": 74.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        # Normal Peer 2
        {
            "station_id": "STN_NORM_2",
            "station_name": "Normal Peer 2",
            "latitude": 22.48,
            "longitude": 88.28,
            "elevation_m": 11.0,
            "temperature_c": 30.3,
            "pressure_hpa": 1012.4,
            "relative_humidity_pct": 76.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
        # Normal Peer 3
        {
            "station_id": "STN_NORM_3",
            "station_name": "Normal Peer 3",
            "latitude": 22.58,
            "longitude": 88.38,
            "elevation_m": 15.0,
            "temperature_c": 29.9,
            "pressure_hpa": 1011.9,
            "relative_humidity_pct": 75.0,
            "timestamp_utc": "2026-09-29T04:00:00Z",
        },
    ]

    incidents, alerts = evaluate_active_network_incidents(readings, root)

    # 1. Target 1 must be flagged with affected_parameter == "pressure"
    p_inc = next((i for i in incidents if i["station_id"] == "STN_PRESS_FAULT"), None)
    assert p_inc is not None, "STN_PRESS_FAULT must be flagged"
    assert p_inc["affected_parameter"] == "pressure"
    assert p_inc["observed_value_numeric"] == 1048.5
    assert p_inc["unit"] == "hPa"
    assert p_inc["observed_value"] == "1048.5 hPa"

    # 2. Target 2 must be flagged with affected_parameter == "relative_humidity"
    rh_inc = next((i for i in incidents if i["station_id"] == "STN_HUMID_FAULT"), None)
    assert rh_inc is not None, "STN_HUMID_FAULT must be flagged"
    assert rh_inc["affected_parameter"] == "relative_humidity"
    assert rh_inc["observed_value_numeric"] == 12.0
    assert rh_inc["unit"] == "%"
    assert rh_inc["observed_value"] == "12.0 %"

    # 3. Normal peers must not be flagged
    assert next((i for i in incidents if i["station_id"] == "STN_NORM_1"), None) is None
    assert next((i for i in incidents if i["station_id"] == "STN_NORM_2"), None) is None
    assert next((i for i in incidents if i["station_id"] == "STN_NORM_3"), None) is None

    # 4. Across all incidents, ensure no synthetic fallback defaults appear
    for inc in incidents:
        assert inc["affected_parameter"] in ("temperature", "pressure", "relative_humidity")
        assert inc["observed_value_numeric"] is not None
        # Verify observed_value_numeric matches one of the station's actual reported values
        stn_raw = next(r for r in readings if r["station_id"] == inc["station_id"])
        reported_values = [
            stn_raw.get("temperature_c"),
            stn_raw.get("pressure_hpa"),
            stn_raw.get("relative_humidity_pct"),
        ]
        assert inc["observed_value_numeric"] in reported_values, (
            f"Incident observed value {inc['observed_value_numeric']} does not match any reported sensor value: {reported_values}"
        )


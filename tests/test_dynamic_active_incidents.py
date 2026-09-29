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

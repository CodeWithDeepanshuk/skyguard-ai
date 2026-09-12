import json
from unittest.mock import patch

from skyguard.providers.imd_wis2 import IMDWIS2Provider


class Response:
    status = 200
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode()


def feature(report, name, value):
    return {"type":"Feature", "geometry":{"type":"Point", "coordinates":[77.2, 28.6]},
            "properties":{"wigos_station_identifier":"0-20000-0-42182", "reportId":report,
                          "reportTime":"2026-09-13T00:00:00Z", "name":name, "value":value}}


def test_wis2_parameter_features_group_into_one_observed_report():
    payload = {"features":[feature("r1", "air_temperature", 30.0),
                           feature("r1", "dewpoint_temperature", 20.0),
                           feature("r1", "pressure_reduced_to_mean_sea_level", 1005.2)]}
    provider = IMDWIS2Provider()
    provider._cached_stations = [{"wigos_id":"0-20000-0-42182", "traditional_id":"42182",
                                  "latitude":28.6, "longitude":77.2, "elevation_m":210}]
    with patch.object(provider, "station_metadata", return_value=provider._cached_stations), \
         patch("urllib.request.urlopen", return_value=Response(payload)) as opened:
        rows = provider.fetch_history("0-20000-0-42182", 24)
    assert len(rows) == 1
    row = rows[0]
    assert row.source_type == "OBSERVED" and row.is_direct_observation
    assert row.temperature_c == 30.0 and row.pressure_hpa == 1005.2
    assert 54 < row.relative_humidity_pct < 56 and row.rh_source == "DERIVED"
    assert len(row.raw_source_hash) == 64
    assert "wigos_station_identifier=0-20000-0-42182" in opened.call_args.args[0].full_url
    assert "datetime=" in opened.call_args.args[0].full_url


def test_wis2_rejects_other_station_and_empty_weather_report():
    wrong = feature("r1", "wind_speed", 3.0)
    wrong["properties"]["wigos_station_identifier"] = "other"
    provider = IMDWIS2Provider()
    with patch.object(provider, "station_metadata", return_value=[]), \
         patch("urllib.request.urlopen", return_value=Response({"features":[wrong]})):
        assert provider.fetch_history("0-20000-0-42182", 24) == []

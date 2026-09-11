from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data.normalize_noaa_isd import normalize_file, parse_ma1  # noqa: E402


class NoaaNormalizationTests(unittest.TestCase):
    def test_ma1_keeps_station_pressure_when_altimeter_is_missing(self) -> None:
        altimeter, altimeter_quality, station, station_quality = parse_ma1("99999,9,09133,1")
        self.assertIsNone(altimeter)
        self.assertEqual(altimeter_quality, "9")
        self.assertAlmostEqual(station, 913.3)
        self.assertEqual(station_quality, "1")

    def test_ma1_keeps_altimeter_when_station_pressure_is_missing(self) -> None:
        altimeter, altimeter_quality, station, station_quality = parse_ma1("10190,1,99999,9")
        self.assertAlmostEqual(altimeter, 1019.0)
        self.assertEqual(altimeter_quality, "1")
        self.assertIsNone(station)
        self.assertEqual(station_quality, "9")

    def test_normalizer_falls_back_to_genuine_station_pressure(self) -> None:
        temporary = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8", newline="")
        path = Path(temporary.name)
        writer = csv.DictWriter(temporary, fieldnames=[
            "STATION", "DATE", "TMP", "DEW", "SLP", "MA1", "NAME", "LATITUDE",
            "LONGITUDE", "ELEVATION", "REPORT_TYPE",
        ])
        writer.writeheader()
        writer.writerow({
            "STATION": "43295099999", "DATE": "2022-01-01T00:00:00", "TMP": "+0250,1",
            "DEW": "+0150,1", "SLP": "99999,9", "MA1": "99999,9,09133,1",
            "NAME": "BANGALORE", "LATITUDE": "12.967", "LONGITUDE": "77.583",
            "ELEVATION": "921.0", "REPORT_TYPE": "FM-12",
        })
        temporary.close()
        self.addCleanup(path.unlink)
        station = {
            "station_id": "43295099999", "cluster": "bengaluru", "evaluation_role": "development",
            "station_name": "Bangalore", "latitude": "12.967", "longitude": "77.583",
            "elevation_m": "921.0",
        }
        record = next(iter(normalize_file(path, station, 2022).values()))
        self.assertEqual(record["pressure_source"], "ma1_station")
        self.assertEqual(record["pressure_hpa"], "913.3000")


if __name__ == "__main__":
    unittest.main()

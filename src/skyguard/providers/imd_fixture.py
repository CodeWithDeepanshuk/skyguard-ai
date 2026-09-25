"""Synthetic IMD-shaped fixture and offline replay provider.

Values are controlled simulations for tests and demos. They are never presented
as downloaded IMD observations and are never substituted when live IMD fails.
The provisional field names are isolated from the live schema-review path.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from skyguard.providers.base import (
    ObservationRecord,
    PressureType,
    ProviderName,
    RHSource,
    SourceType,
    WeatherProvider,
)

ROOT = Path(__file__).resolve().parents[3]

# Synthetic representative stations across broad Indian climate zones.
CANONICAL_STATIONS = [
    {"CALL_SIGN": "VIDP", "STATION": "DELHI SAFDARJUNG", "DISTRICT": "NEW DELHI", "STATE": "DELHI", "LAT": 28.58, "LON": 77.20, "ELEV": 216.0, "BASE_T": 32.0, "BASE_P": 1005.0, "BASE_RH": 55.0},
    {"CALL_SIGN": "VABB", "STATION": "MUMBAI SANTACRUZ", "DISTRICT": "MUMBAI", "STATE": "MAHARASHTRA", "LAT": 19.11, "LON": 72.85, "ELEV": 14.0, "BASE_T": 29.5, "BASE_P": 1010.5, "BASE_RH": 80.0},
    {"CALL_SIGN": "VECC", "STATION": "KOLKATA ALIPORE", "DISTRICT": "KOLKATA", "STATE": "WEST BENGAL", "LAT": 22.53, "LON": 88.33, "ELEV": 6.0, "BASE_T": 30.0, "BASE_P": 1008.0, "BASE_RH": 78.0},
    {"CALL_SIGN": "VOMM", "STATION": "CHENNAI MEENAMBAKKAM", "DISTRICT": "CHENNAI", "STATE": "TAMIL NADU", "LAT": 12.99, "LON": 80.18, "ELEV": 16.0, "BASE_T": 31.0, "BASE_P": 1011.0, "BASE_RH": 72.0},
    {"CALL_SIGN": "VOBL", "STATION": "BENGALURU HAL", "DISTRICT": "BENGALURU URBAN", "STATE": "KARNATAKA", "LAT": 12.95, "LON": 77.66, "ELEV": 888.0, "BASE_T": 25.0, "BASE_P": 1012.0, "BASE_RH": 65.0},
    {"CALL_SIGN": "VISR", "STATION": "SRINAGAR AIRPORT", "DISTRICT": "SRINAGAR", "STATE": "JAMMU AND KASHMIR", "LAT": 34.00, "LON": 74.77, "ELEV": 1587.0, "BASE_T": 18.0, "BASE_P": 1014.0, "BASE_RH": 50.0},
    {"CALL_SIGN": "VIJO", "STATION": "JODHPUR AWS", "DISTRICT": "JODHPUR", "STATE": "RAJASTHAN", "LAT": 26.25, "LON": 73.04, "ELEV": 224.0, "BASE_T": 36.0, "BASE_P": 1003.0, "BASE_RH": 35.0},
    {"CALL_SIGN": "VABP", "STATION": "BHOPAL BAIRAGARH", "DISTRICT": "BHOPAL", "STATE": "MADHYA PRADESH", "LAT": 23.28, "LON": 77.33, "ELEV": 523.0, "BASE_T": 28.5, "BASE_P": 1007.5, "BASE_RH": 60.0},
    {"CALL_SIGN": "VILK", "STATION": "LUCKNOW AMAUSI", "DISTRICT": "LUCKNOW", "STATE": "UTTAR PRADESH", "LAT": 26.76, "LON": 80.88, "ELEV": 123.0, "BASE_T": 31.5, "BASE_P": 1006.0, "BASE_RH": 62.0},
    {"CALL_SIGN": "VAPO", "STATION": "PUNE SHIVAJINAGAR", "DISTRICT": "PUNE", "STATE": "MAHARASHTRA", "LAT": 18.53, "LON": 73.85, "ELEV": 559.0, "BASE_T": 27.0, "BASE_P": 1010.0, "BASE_RH": 68.0},
]


class IMDFixtureProvider(WeatherProvider):
    """Deterministic, schema-faithful IMD AWS fixture and historical replay provider."""

    def __init__(self, root: Path = ROOT) -> None:
        super().__init__(name="IMD_FIXTURE_REPLAY", source_type=SourceType.CONTROLLED_SIMULATION)
        self.root = root
        self.quarantine_dir = root / "data" / "quarantine"
        self.raw_dir = root / "data" / "raw" / "fixtures"
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def configured(self) -> bool:
        return True

    def generate_snapshot(
        self,
        base_time: Optional[datetime] = None,
        *,
        step_index: int = 0,
        inject_corruptions: bool = False,
    ) -> List[Dict[str, Any]]:
        """Generate deterministic synthetic rows for offline tests only."""
        ts = base_time or datetime.now(timezone.utc)
        hour = ts.hour + (ts.minute / 60.0)
        date_str = ts.strftime("%Y-%m-%d")
        time_str = ts.strftime("%H:%M:%S")

        rows: List[Dict[str, Any]] = []
        for i, meta in enumerate(CANONICAL_STATIONS):
            # Realistic physical diurnal solar cycle (peak at 14:00 local, trough at 05:00)
            solar_phase = 2.0 * math.pi * (hour - 5.0) / 24.0
            diurnal_temp = 5.0 * math.sin(solar_phase)
            diurnal_rh = -15.0 * math.sin(solar_phase)
            diurnal_pres = 1.8 * math.cos(4.0 * math.pi * hour / 24.0)  # semi-diurnal atmospheric tide

            temp = round(meta["BASE_T"] + diurnal_temp + (math.sin(step_index + i) * 0.4), 1)
            rh = round(max(5.0, min(98.0, meta["BASE_RH"] + diurnal_rh + (math.cos(step_index + i) * 0.8))), 1)
            mslp = round(meta["BASE_P"] + diurnal_pres + (math.sin(step_index * 0.5 + i) * 0.2), 1)

            sensor_id = hashlib.sha256(f"{meta['CALL_SIGN']}_{meta['STATION']}".encode("utf-8")).hexdigest()[:8].upper()

            row = {
                "ID": sensor_id,
                "CALL_SIGN": meta["CALL_SIGN"],
                "DISTRICT": meta["DISTRICT"],
                "STATE": meta["STATE"],
                "STATION": meta["STATION"],
                "DATE": date_str,
                "TIME": time_str,
                "CURR_TEMP": f"{temp:.1f}",
                "RH": f"{rh:.1f}",
                "MSLP": f"{mslp:.1f}",
                "Latitude": f"{meta['LAT']:.4f}",
                "Longitude": f"{meta['LON']:.4f}",
            }
            rows.append(row)

        if inject_corruptions:
            # Add one malformed row to test quarantine handling
            rows.append({
                "ID": "BAD99999",
                "CALL_SIGN": "MALFORMED_TEST",
                "DATE": date_str,
                "TIME": time_str,
                "CURR_TEMP": "NaN_CORRUPT",
                "RH": "-99.0",
                "MSLP": "INVALID",
                "Latitude": "999.0",
                "Longitude": "999.0",
            })

        return rows

    def quarantine_record(self, raw_row: Dict[str, Any], reason: str) -> None:
        """Store unparseable or rejected raw payloads for audit."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        record = {
            "quarantined_at_utc": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "raw_payload": raw_row,
        }
        file_path = self.quarantine_dir / f"quarantine_{stamp}_{raw_row.get('CALL_SIGN', 'UNKNOWN')}.json"
        file_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def fetch_network(self, base_time: Optional[datetime] = None) -> List[ObservationRecord]:
        """Fetch and normalize fixture records with raw preservation."""
        raw_rows = self.generate_snapshot(base_time)
        return self._normalize_payload(raw_rows)

    def _normalize_payload(self, raw_rows: List[Dict[str, Any]]) -> List[ObservationRecord]:
        observations: List[ObservationRecord] = []
        for row in raw_rows:
            call_sign = str(row.get("CALL_SIGN") or "").strip()
            date = str(row.get("DATE") or "").strip()
            clock = str(row.get("TIME") or "").strip()
            
            if not call_sign or not date:
                self.quarantine_record(row, "Missing mandatory CALL_SIGN or DATE field")
                continue

            # Parse coordinates
            try:
                lat = float(row.get("Latitude", ""))
                lon = float(row.get("Longitude", ""))
                if not (5.0 <= lat <= 40.0 and 65.0 <= lon <= 100.0):
                    self.quarantine_record(row, f"Coordinates ({lat}, {lon}) outside India domain")
                    continue
            except (ValueError, TypeError):
                self.quarantine_record(row, "Unparseable latitude/longitude")
                continue

            # Parse timestamps strictly to UTC
            try:
                dt_str = f"{date} {clock or '00:00:00'}"
                parsed_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                timestamp_utc = parsed_dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            except (ValueError, TypeError):
                self.quarantine_record(row, f"Invalid date/time format: {date} {clock}")
                continue

            # Parse meteorological numbers
            def parse_num(val: Any) -> Optional[float]:
                try:
                    num = float(val)
                    return num if math.isfinite(num) else None
                except (ValueError, TypeError):
                    return None

            temp_c = parse_num(row.get("CURR_TEMP"))
            rh_pct = parse_num(row.get("RH"))
            mslp_hpa = parse_num(row.get("MSLP"))

            if temp_c is None and rh_pct is None and mslp_hpa is None:
                self.quarantine_record(row, "All three meteorological values are missing or unparseable")
                continue

            raw_json = json.dumps(row, sort_keys=True, separators=(",", ":"))
            payload_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

            record = ObservationRecord(
                provider="IMD_FIXTURE_REPLAY",
                source_type=SourceType.CONTROLLED_SIMULATION.value,
                station_id=call_sign,
                provider_station_id=call_sign,
                canonical_station_id=call_sign,
                station_name=str(row.get("STATION") or call_sign).strip(),
                state=str(row.get("STATE") or "").strip(),
                district=str(row.get("DISTRICT") or "").strip(),
                timestamp_utc=timestamp_utc,
                latitude=lat,
                longitude=lon,
                temperature_c=temp_c,
                pressure_hpa=mslp_hpa,
                pressure_type=PressureType.MEAN_SEA_LEVEL_PRESSURE.value,
                relative_humidity_pct=rh_pct,
                rh_source=RHSource.OBSERVED.value if rh_pct is not None else RHSource.UNAVAILABLE.value,
                is_direct_observation=False,
                is_interpolated=False,
                is_model_field=False,
                raw_source_hash=payload_hash,
                source_url="fixture://canonical_imd_aws_replay",
                message_id=f"{call_sign}|{timestamp_utc}",
                raw_payload_json=raw_json,
                source_quality_flags=("SYNTHETIC_FIXTURE", "NOT_LIVE_IMD_DATA"),
            )
            observations.append(record)

        return observations

    def fetch_current(self, station_id: str) -> Optional[ObservationRecord]:
        for rec in self.fetch_network():
            if rec.station_id == station_id:
                return rec
        return None

    def fetch_history(self, station_id: str, hours: int = 24) -> List[ObservationRecord]:
        now = datetime.now(timezone.utc)
        history: List[ObservationRecord] = []
        for h in range(hours, -1, -1):
            t = now - timedelta(hours=h)
            for rec in self.fetch_network(base_time=t):
                if rec.station_id == station_id:
                    history.append(rec)
        return history

    def station_metadata(self) -> List[Dict[str, Any]]:
        return [
            {
                "station_id": s["CALL_SIGN"],
                "station_name": s["STATION"],
                "district": s["DISTRICT"],
                "state": s["STATE"],
                "latitude": s["LAT"],
                "longitude": s["LON"],
                "elevation_m": s["ELEV"],
            }
            for s in CANONICAL_STATIONS
        ]

    def healthcheck(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "ready",
            "mode": "CANONICAL_FIXTURE_REPLAY",
            "data_class": "CONTROLLED_SIMULATION",
            "eligible_as_live_observation": False,
            "stations_available": len(CANONICAL_STATIONS),
            "pressure_semantics": "MEAN_SEA_LEVEL_PRESSURE",
            "model_inputs": ["temperature_c", "pressure_hpa", "relative_humidity_pct"],
        }

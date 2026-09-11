"""Local SQLite persistence for offline replay."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class ReplayStore:
    def __init__(self, path: Path | str = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS readings (
                sequence INTEGER PRIMARY KEY, row_id TEXT, station_id TEXT, timestamp_utc TEXT,
                temperature REAL, pressure REAL, humidity REAL, event_decision TEXT,
                fault_probability REAL, root_cause TEXT, payload_json TEXT
            );
            CREATE TABLE IF NOT EXISTS alerts (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, alert_id TEXT UNIQUE, station_id TEXT,
                timestamp_utc TEXT, alert_type TEXT, severity TEXT, explanation TEXT,
                target_episode_id TEXT
            );
        """)

    def reset(self) -> None:
        self.connection.execute("DELETE FROM readings")
        self.connection.execute("DELETE FROM alerts")
        self.connection.commit()

    def add_reading(self, sequence: int, row: dict[str, str]) -> None:
        def value(key: str) -> float | None:
            try:
                return float(row.get(key, ""))
            except (TypeError, ValueError):
                return None
        self.connection.execute(
            "INSERT OR REPLACE INTO readings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sequence, row["row_id"], row["station_id"], row["emitted_timestamp_utc"],
             value("temperature_value"), value("pressure_value"), value("humidity_value"),
             row.get("event_decision", ""), value("fault_probability"), row.get("root_cause_prediction", ""),
             json.dumps(row)),
        )
        self.connection.commit()

    def add_alert(self, alert: dict[str, str]) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO alerts (alert_id,station_id,timestamp_utc,alert_type,severity,explanation,target_episode_id) VALUES (?,?,?,?,?,?,?)",
            tuple(alert[key] for key in ("alert_id", "station_id", "timestamp_utc", "alert_type", "severity", "explanation", "target_episode_id")),
        )
        self.connection.commit()

    def readings(self, limit: int = 100, station_id: str | None = None) -> list[dict[str, object]]:
        if station_id:
            rows = self.connection.execute("SELECT * FROM readings WHERE station_id=? ORDER BY sequence DESC LIMIT ?", (station_id, limit))
        else:
            rows = self.connection.execute("SELECT * FROM readings ORDER BY sequence DESC LIMIT ?", (limit,))
        return [dict(row) for row in rows]

    def alerts(self, limit: int = 100) -> list[dict[str, object]]:
        rows = self.connection.execute("SELECT * FROM alerts ORDER BY sequence DESC LIMIT ?", (limit,))
        return [dict(row) for row in rows]

    def counts(self) -> dict[str, int]:
        return {
            "readings": int(self.connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0]),
            "alerts": int(self.connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]),
        }

    def close(self) -> None:
        self.connection.close()

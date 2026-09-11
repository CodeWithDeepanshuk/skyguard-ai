from __future__ import annotations

import csv
import gzip
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.streaming.engine import ReplayEngine  # noqa: E402
from skyguard.streaming.store import ReplayStore  # noqa: E402


FIELDS = [
    "row_id", "station_id", "timestamp_utc", "emitted_timestamp_utc", "temperature_value",
    "pressure_value", "humidity_value", "stream_action", "available_to_detector", "episode_id",
    "packet_id",
]


def row(identity: str, timestamp: str, values: tuple[str, str, str] = ("30", "1000", "50"), action: str = "emit", available: str = "1", episode: str = "", packet_id: str | None = None) -> dict[str, str]:
    return {
        "row_id": identity, "station_id": "A", "timestamp_utc": timestamp, "emitted_timestamp_utc": timestamp,
        "temperature_value": values[0], "pressure_value": values[1], "humidity_value": values[2],
        "stream_action": action, "available_to_detector": available, "episode_id": episode,
        "packet_id": packet_id or identity,
    }


class StreamingTests(unittest.TestCase):
    def engine(self, rows: list[dict[str, str]]) -> ReplayEngine:
        temporary = tempfile.NamedTemporaryFile(suffix=".csv.gz", delete=False)
        temporary.close()
        path = Path(temporary.name)
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(rows)
        self.addCleanup(path.unlink)
        engine = ReplayEngine(
            path,
            ReplayStore(),
            {"A": 30.0},
            {"A": 75.0},
            contract_source="unit_test_verified_adapter",
        )
        self.addCleanup(engine.store.close)
        return engine

    def unknown_contract_engine(self, rows: list[dict[str, str]]) -> ReplayEngine:
        temporary = tempfile.NamedTemporaryFile(suffix=".csv.gz", delete=False)
        temporary.close()
        path = Path(temporary.name)
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(rows)
        self.addCleanup(path.unlink)
        engine = ReplayEngine(path, ReplayStore(), advisory_gap_minutes=360.0)
        self.addCleanup(engine.store.close)
        return engine

    def test_dropout_becomes_gap_on_next_packet(self) -> None:
        engine = self.engine([
            row("1", "2024-01-01T00:00:00Z"),
            row("2", "2024-01-01T00:30:00Z", action="drop", available="0", episode="DROP"),
            row("3", "2024-01-01T02:00:00Z", values=("31", "1001", "51")),
        ])
        result = engine.step(3)
        self.assertEqual(result["new_alerts"][0]["alert_type"], "communication_gap")
        self.assertEqual(result["new_alerts"][0]["target_episode_id"], "DROP")

    def test_unknown_cadence_gap_is_advisory_not_fault(self) -> None:
        engine = self.unknown_contract_engine([
            row("1", "2024-01-01T00:00:00Z"),
            row("2", "2024-01-01T07:00:00Z", values=("31", "1001", "51")),
        ])
        result = engine.step(2)
        self.assertEqual(result["new_alerts"][0]["alert_type"], "unverified_data_gap")
        self.assertEqual(result["new_alerts"][0]["severity"], "low")
        self.assertNotIn("communication_gap", engine.status()["alert_counts"])

    def test_duplicate_values_emit_one_alert_per_run(self) -> None:
        engine = self.engine([
            row("1", "2024-01-01T00:00:00Z", packet_id="same"), row("2", "2024-01-01T00:30:00Z", packet_id="same"),
            row("3", "2024-01-01T01:00:00Z", packet_id="same"),
        ])
        engine.step(3)
        self.assertEqual(engine.status()["alert_counts"]["duplicate_packet"], 1)

    def test_out_of_order_timestamp_is_detected(self) -> None:
        rows = [row("1", "2024-01-01T01:00:00Z"), row("2", "2024-01-01T00:30:00Z", values=("31", "1001", "51"))]
        engine = self.engine(rows); engine.step(2)
        self.assertEqual(engine.status()["alert_counts"]["timestamp_disorder"], 1)


if __name__ == "__main__":
    unittest.main()

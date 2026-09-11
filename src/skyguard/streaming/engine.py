"""Deterministic offline replay with stateful communication checks."""

from __future__ import annotations

import csv
import gzip
import hashlib
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .models import StreamAlert
from .store import ReplayStore


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ReplayEngine:
    def __init__(
        self,
        scenario_file: Path,
        store: ReplayStore,
        expected_minutes: dict[str, float] | None = None,
        heartbeat_sla_minutes: dict[str, float] | None = None,
        advisory_gap_minutes: float = 360.0,
        contract_source: str = "unverified_source",
    ) -> None:
        self.scenario_file = scenario_file
        self.store = store
        self.expected_minutes = expected_minutes or {}
        self.heartbeat_sla_minutes = heartbeat_sla_minutes or {}
        self.advisory_gap_minutes = float(advisory_gap_minutes)
        self.contract_source = contract_source
        self.rows = self._load(scenario_file)
        self.reset()

    @staticmethod
    def _load(path: Path) -> list[dict[str, str]]:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def reset(self) -> None:
        self.index = 0
        self.emitted = 0
        self.dropped = 0
        self.alert_counts: dict[str, int] = defaultdict(int)
        self.last_time: dict[str, datetime] = {}
        self.last_values: dict[str, tuple[str, str, str]] = {}
        self.last_packet_id: dict[str, str] = {}
        self.repeat_active: set[str] = set()
        self.pending_drop_episode: dict[str, str] = {}
        self.store.reset()

    def _alert(self, row: dict[str, str], alert_type: str, explanation: str, episode: str = "") -> dict[str, str]:
        identity = f"{row['station_id']}|{row['emitted_timestamp_utc']}|{alert_type}|{episode}"
        alert = StreamAlert(
            alert_id="STR-" + hashlib.sha1(identity.encode()).hexdigest()[:14].upper(),
            station_id=row["station_id"], timestamp_utc=row["emitted_timestamp_utc"],
            alert_type=alert_type,
            severity=(
                "high" if alert_type == "communication_gap"
                else "low" if alert_type == "unverified_data_gap"
                else "medium"
            ),
            explanation=explanation, target_episode_id=episode,
        ).as_dict()
        self.store.add_alert(alert)
        self.alert_counts[alert_type] += 1
        return alert

    def step(self, count: int = 1) -> dict[str, object]:
        started = time.perf_counter()
        new_alerts: list[dict[str, str]] = []
        processed = 0
        while processed < count and self.index < len(self.rows):
            row = self.rows[self.index]
            self.index += 1
            processed += 1
            station = row["station_id"]
            if row.get("available_to_detector") == "0" or row.get("stream_action") == "drop":
                self.dropped += 1
                if row.get("episode_id"):
                    self.pending_drop_episode[station] = row["episode_id"]
                continue

            current = parse_time(row["emitted_timestamp_utc"])
            previous = self.last_time.get(station)
            expected = self.expected_minutes.get(station)
            heartbeat_sla = self.heartbeat_sla_minutes.get(station)
            if previous is not None:
                elapsed = (current - previous).total_seconds() / 60.0
                if elapsed < 0:
                    new_alerts.append(self._alert(row, "timestamp_disorder", f"Timestamp moved backward by {abs(elapsed):.1f} minutes.", row.get("episode_id", "")))
                elif expected is not None and heartbeat_sla is not None and elapsed > heartbeat_sla:
                    episode = self.pending_drop_episode.pop(station, "")
                    new_alerts.append(self._alert(
                        row,
                        "communication_gap",
                        f"Verified heartbeat SLA was exceeded: {elapsed:.1f} minutes without a packet; "
                        f"expected cadence {expected:.1f} minutes and SLA {heartbeat_sla:.1f} minutes.",
                        episode,
                    ))
                elif (expected is None or heartbeat_sla is None) and elapsed > self.advisory_gap_minutes:
                    episode = self.pending_drop_episode.pop(station, "")
                    new_alerts.append(self._alert(
                        row,
                        "unverified_data_gap",
                        f"A {elapsed:.1f}-minute data gap was observed, but the source supplied no verified "
                        "cadence and heartbeat SLA. This is an advisory, not a sensor-fault claim.",
                        episode,
                    ))

            current_values = (row.get("temperature_value", ""), row.get("pressure_value", ""), row.get("humidity_value", ""))
            packet_id = row.get("packet_id", "")
            same_packet_id = bool(packet_id and self.last_packet_id.get(station) == packet_id)
            same_timestamp_and_values = bool(previous is not None and current == previous and current_values == self.last_values.get(station))
            if same_packet_id or same_timestamp_and_values:
                if station not in self.repeat_active:
                    new_alerts.append(self._alert(row, "duplicate_packet", "Transport packet identity repeats the previous packet; probable duplicate transmission.", row.get("episode_id", "")))
                    self.repeat_active.add(station)
            else:
                self.repeat_active.discard(station)

            self.last_values[station] = current_values
            self.last_packet_id[station] = packet_id
            if previous is None or current >= previous:
                self.last_time[station] = current
            self.emitted += 1
            self.store.add_reading(self.emitted, row)
        elapsed_seconds = time.perf_counter() - started
        return {
            "processed_source_rows": processed, "emitted_readings": self.emitted,
            "new_alerts": new_alerts, "finished": self.index >= len(self.rows),
            "position": self.index, "total_rows": len(self.rows),
            "batch_seconds": elapsed_seconds,
            "throughput_rows_per_second": processed / elapsed_seconds if elapsed_seconds else 0.0,
        }

    def status(self) -> dict[str, object]:
        return {
            "scenario_file": self.scenario_file.name, "position": self.index, "total_rows": len(self.rows),
            "emitted_readings": self.emitted, "dropped_source_rows": self.dropped,
            "alert_counts": dict(self.alert_counts), "finished": self.index >= len(self.rows),
            "communication_policy": {
                "contract_source": self.contract_source,
                "verified_station_contracts": len(set(self.expected_minutes) & set(self.heartbeat_sla_minutes)),
                "automatic_gap_requires_verified_heartbeat": True,
                "unknown_cadence_output": "unverified_data_gap",
                "advisory_gap_minutes": self.advisory_gap_minutes,
            },
            **self.store.counts(),
        }

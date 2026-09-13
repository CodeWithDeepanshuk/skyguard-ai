"""Idempotent SQLite/PostgreSQL observation repository.

SQLite is a local development and offline-replay fallback.  A configured
``DATABASE_URL`` selects PostgreSQL and is the only mode reported as durable in
production because Render's free-service filesystem is ephemeral.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional

from skyguard.providers.base import ObservationRecord


ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = ROOT / "migrations"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_utc(value: object) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class ObservationStore:
    """Append-only normalized observation storage with ingestion receipts."""

    columns = (
        "observation_key", "provider", "provider_station_id", "canonical_station_id",
        "wigos_id", "icao_code", "station_name", "state", "district", "latitude",
        "longitude", "elevation_m", "observation_timestamp_utc",
        "provider_publication_timestamp_utc", "ingestion_timestamp_utc", "temperature_c",
        "pressure_hpa", "pressure_type", "relative_humidity_pct",
        "humidity_observation_type", "source_quality_flags_json", "raw_payload_hash",
        "source_url", "message_id", "schema_version", "source_type",
        "is_direct_observation", "is_interpolated", "is_model_field",
    )

    def __init__(self, database_url: Optional[str] = None, *, root: Path = ROOT) -> None:
        configured = database_url if database_url is not None else os.getenv("DATABASE_URL", "").strip()
        self.root = root
        if configured.startswith("postgres://"):
            configured = "postgresql://" + configured[len("postgres://"):]
        self.database_url = configured
        self.backend = "postgresql" if configured.startswith(("postgresql://", "postgresql+")) else "sqlite"
        if self.backend == "sqlite":
            if configured.startswith("sqlite:///"):
                self.sqlite_path = Path(configured[len("sqlite:///"):])
            elif configured and "://" not in configured:
                self.sqlite_path = Path(configured)
            else:
                self.sqlite_path = root / "data" / "runtime" / "observations.db"
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.sqlite_path = None
        self.migrate()

    @property
    def durability(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "durable": self.backend == "postgresql",
            "status": "durable_database" if self.backend == "postgresql" else "local_development_fallback",
        }

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        if self.backend == "postgresql":
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:  # pragma: no cover - exercised only in PostgreSQL deployment
                raise RuntimeError("PostgreSQL requires psycopg[binary]") from exc
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                yield connection
        else:
            connection = sqlite3.connect(str(self.sqlite_path), timeout=30.0)
            connection.row_factory = sqlite3.Row
            try:
                yield connection
                connection.commit()
            finally:
                connection.close()

    def migrate(self) -> None:
        migration = MIGRATIONS / (
            "001_observation_store_postgres.sql" if self.backend == "postgresql"
            else "001_observation_store_sqlite.sql"
        )
        sql = migration.read_text(encoding="utf-8")
        with self._connection() as connection:
            if self.backend == "sqlite":
                connection.executescript(sql)
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at_utc) VALUES (?, ?)",
                    (migration.name, _now()),
                )
            else:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    cursor.execute(
                        "INSERT INTO schema_migrations(version) VALUES (%s) ON CONFLICT(version) DO NOTHING",
                        (migration.name,),
                    )

    def _record_values(self, record: ObservationRecord) -> tuple[object, ...]:
        return (
            record.observation_key, record.provider, record.provider_station_id,
            record.canonical_station_id, record.wigos_id or None, record.icao_code or None,
            record.station_name or None, record.state or None, record.district or None,
            record.latitude, record.longitude, record.elevation_m, record.timestamp_utc,
            record.provider_publication_timestamp_utc or None, record.ingestion_timestamp_utc,
            record.temperature_c, record.pressure_hpa, record.pressure_type,
            record.relative_humidity_pct, record.humidity_observation_type,
            self._json_param(list(record.source_quality_flags)), record.raw_source_hash,
            record.source_url or None, record.message_id or None, record.schema_version,
            record.source_type, bool(record.is_direct_observation), bool(record.is_interpolated),
            bool(record.is_model_field),
        )

    def _json_param(self, value: object) -> object:
        if self.backend == "postgresql":  # pragma: no cover - deployment path
            from psycopg.types.json import Jsonb
            return Jsonb(value)
        return json.dumps(value)

    def append(self, records: Iterable[ObservationRecord]) -> dict[str, int]:
        items = list(records)
        if not items:
            return {"fetched": 0, "inserted": 0, "duplicates": 0, "raw_payloads": 0}
        placeholders = ",".join(["%s" if self.backend == "postgresql" else "?"] * len(self.columns))
        insert_prefix = "INSERT INTO" if self.backend == "postgresql" else "INSERT OR IGNORE INTO"
        conflict = " ON CONFLICT(observation_key) DO NOTHING" if self.backend == "postgresql" else ""
        sql = f"{insert_prefix} observations ({','.join(self.columns)}) VALUES ({placeholders}){conflict}"
        inserted = 0
        raw_inserted = 0
        with self._connection() as connection:
            cursor = connection.cursor()
            for record in items:
                cursor.execute(sql, self._record_values(record))
                if cursor.rowcount > 0:
                    inserted += 1
                if record.raw_payload_json:
                    if self.backend == "postgresql":
                        cursor.execute(
                            "INSERT INTO raw_payloads(raw_payload_hash,provider,payload_json,first_seen_at_utc) "
                            "VALUES (%s,%s,%s::jsonb,%s) ON CONFLICT(raw_payload_hash) DO NOTHING",
                            (record.raw_source_hash, record.provider, record.raw_payload_json, record.ingestion_timestamp_utc),
                        )
                    else:
                        cursor.execute(
                            "INSERT OR IGNORE INTO raw_payloads(raw_payload_hash,provider,payload_json,first_seen_at_utc) "
                            "VALUES (?,?,?,?)",
                            (record.raw_source_hash, record.provider, record.raw_payload_json, record.ingestion_timestamp_utc),
                        )
                    if cursor.rowcount > 0:
                        raw_inserted += 1
        return {
            "fetched": len(items), "inserted": inserted,
            "duplicates": len(items) - inserted, "raw_payloads": raw_inserted,
        }

    @staticmethod
    def _decode_row(row: Mapping[str, Any]) -> dict[str, Any]:
        output = dict(row)
        flags = output.pop("source_quality_flags_json", [])
        if isinstance(flags, str):
            try:
                flags = json.loads(flags)
            except json.JSONDecodeError:
                flags = [flags]
        output["source_quality_flags"] = flags or []
        for key in (
            "observation_timestamp_utc", "provider_publication_timestamp_utc",
            "ingestion_timestamp_utc", "started_at_utc", "finished_at_utc", "watermark_utc",
            "updated_at_utc", "latest_observation_utc", "latest_ingestion_utc",
            "occurred_at_utc", "received_at_utc",
        ):
            if isinstance(output.get(key), datetime):
                output[key] = output[key].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        for key in ("is_direct_observation", "is_interpolated", "is_model_field"):
            if key in output:
                output[key] = bool(output[key])
        return output

    def latest_observations(self, *, limit: int = 2000, provider: Optional[str] = None) -> list[dict[str, Any]]:
        parameter = "%s" if self.backend == "postgresql" else "?"
        where = f"WHERE provider={parameter}" if provider else ""
        sql = f"""
            SELECT * FROM (
                SELECT o.*, ROW_NUMBER() OVER (
                    PARTITION BY canonical_station_id
                    ORDER BY observation_timestamp_utc DESC, ingestion_timestamp_utc DESC
                ) AS row_rank
                FROM observations o {where}
            ) ranked
            WHERE row_rank=1
            ORDER BY observation_timestamp_utc DESC
            LIMIT {parameter}
        """
        params: tuple[object, ...] = (provider, limit) if provider else (limit,)
        with self._connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._decode_row(row) for row in rows]

    def history(self, station_id: str, *, hours: int = 24, limit: int = 5000) -> list[dict[str, Any]]:
        parameter = "%s" if self.backend == "postgresql" else "?"
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, min(hours, 24 * 365)))
        sql = f"""
            SELECT * FROM observations
            WHERE canonical_station_id={parameter} AND observation_timestamp_utc>={parameter}
            ORDER BY observation_timestamp_utc ASC LIMIT {parameter}
        """
        with self._connection() as connection:
            rows = connection.execute(sql, (station_id, cutoff.isoformat(), limit)).fetchall()
        return [self._decode_row(row) for row in rows]

    def begin_run(self, provider: str, metadata: Optional[dict[str, Any]] = None) -> str:
        run_id = str(uuid.uuid4())
        parameter = "%s" if self.backend == "postgresql" else "?"
        sql = (
            "INSERT INTO ingestion_runs(run_id,provider,started_at_utc,status,metadata_json) "
            f"VALUES ({','.join([parameter] * 5)})"
        )
        values = (run_id, provider, _now(), "RUNNING", self._json_param(metadata or {}))
        with self._connection() as connection:
            connection.execute(sql, values)
        return run_id

    def finish_run(
        self, run_id: str, *, status: str, fetched_count: int = 0, inserted_count: int = 0,
        duplicate_count: int = 0, dead_letter_count: int = 0, error_message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        parameter = "%s" if self.backend == "postgresql" else "?"
        sql = f"""
            UPDATE ingestion_runs SET finished_at_utc={parameter},status={parameter},
                fetched_count={parameter},inserted_count={parameter},duplicate_count={parameter},
                dead_letter_count={parameter},error_message={parameter},metadata_json={parameter}
            WHERE run_id={parameter}
        """
        with self._connection() as connection:
            connection.execute(sql, (
                _now(), status, fetched_count, inserted_count, duplicate_count,
                dead_letter_count, error_message or None, self._json_param(metadata or {}), run_id,
            ))

    def set_watermark(self, provider: str, watermark_utc: str, metadata: Optional[dict[str, Any]] = None) -> None:
        parameter = "%s" if self.backend == "postgresql" else "?"
        values = (provider, watermark_utc, _now(), json.dumps(metadata or {}))
        if self.backend == "postgresql":
            sql = (
                "INSERT INTO provider_watermarks(provider,watermark_utc,updated_at_utc,metadata_json) "
                "VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(provider) DO UPDATE SET "
                "watermark_utc=EXCLUDED.watermark_utc,updated_at_utc=EXCLUDED.updated_at_utc,"
                "metadata_json=EXCLUDED.metadata_json"
            )
        else:
            sql = (
                "INSERT INTO provider_watermarks(provider,watermark_utc,updated_at_utc,metadata_json) "
                "VALUES (?,?,?,?) ON CONFLICT(provider) DO UPDATE SET "
                "watermark_utc=excluded.watermark_utc,updated_at_utc=excluded.updated_at_utc,"
                "metadata_json=excluded.metadata_json"
            )
        with self._connection() as connection:
            connection.execute(sql, values)

    def get_watermark(self, provider: str) -> Optional[dict[str, Any]]:
        parameter = "%s" if self.backend == "postgresql" else "?"
        with self._connection() as connection:
            row = connection.execute(
                f"SELECT * FROM provider_watermarks WHERE provider={parameter}", (provider,)
            ).fetchone()
        return self._decode_row(row) if row else None

    def latest_run(self, provider: str) -> Optional[dict[str, Any]]:
        parameter = "%s" if self.backend == "postgresql" else "?"
        with self._connection() as connection:
            row = connection.execute(
                f"SELECT * FROM ingestion_runs WHERE provider={parameter} "
                "ORDER BY started_at_utc DESC LIMIT 1",
                (provider,),
            ).fetchone()
        return self._decode_row(row) if row else None

    def record_source_event(self, provider: str, event_type: str, details: Optional[dict[str, Any]] = None) -> None:
        parameter = "%s" if self.backend == "postgresql" else "?"
        value = self._json_param(details or {})
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO source_events(provider,event_type,occurred_at_utc,details_json) "
                f"VALUES ({parameter},{parameter},{parameter},{parameter})",
                (provider, event_type, _now(), value),
            )

    def record_dead_letter(self, provider: str, reason: str, payload: object) -> None:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        raw_hash = __import__("hashlib").sha256(serialized.encode("utf-8")).hexdigest()
        parameter = "%s" if self.backend == "postgresql" else "?"
        cast = "::jsonb" if self.backend == "postgresql" else ""
        sql = (
            "INSERT INTO dead_letters(provider,received_at_utc,reason,raw_payload_hash,payload_json) "
            f"VALUES ({parameter},{parameter},{parameter},{parameter},{parameter}{cast})"
        )
        with self._connection() as connection:
            connection.execute(sql, (provider, _now(), reason, raw_hash, serialized))

    def ingestion_health(self) -> dict[str, Any]:
        parameter = "%s" if self.backend == "postgresql" else "?"
        del parameter
        sql = """
            SELECT * FROM (
                SELECT r.*, ROW_NUMBER() OVER (PARTITION BY provider ORDER BY started_at_utc DESC) AS row_rank
                FROM ingestion_runs r
            ) ranked WHERE row_rank=1 ORDER BY provider
        """
        with self._connection() as connection:
            rows = connection.execute(sql).fetchall()
            count_row = connection.execute("SELECT COUNT(*) AS count FROM observations").fetchone()
            count = int(count_row["count"] if isinstance(count_row, Mapping) else count_row[0])
        return {
            "storage": self.durability,
            "observation_records": count,
            "providers": [self._decode_row(row) for row in rows],
            "checked_at_utc": _now(),
        }

    def source_freshness(self) -> list[dict[str, Any]]:
        sql = """
            SELECT provider, MAX(observation_timestamp_utc) AS latest_observation_utc,
                   MAX(ingestion_timestamp_utc) AS latest_ingestion_utc,
                   COUNT(*) AS observation_records,
                   COUNT(DISTINCT canonical_station_id) AS stations_seen
            FROM observations GROUP BY provider ORDER BY provider
        """
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            rows = connection.execute(sql).fetchall()
        output = []
        for row in rows:
            decoded = self._decode_row(row)
            latest = _parse_utc(decoded.get("latest_observation_utc"))
            age = (now - latest).total_seconds() / 60.0 if latest else None
            decoded["observation_age_minutes"] = round(max(0.0, age), 1) if age is not None else None
            decoded["freshness"] = (
                "FRESH" if age is not None and age <= 90
                else "DELAYED" if age is not None and age <= 180
                else "STALE" if age is not None else "UNAVAILABLE"
            )
            output.append(decoded)
        return output

    def source_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        parameter = "%s" if self.backend == "postgresql" else "?"
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM source_events ORDER BY occurred_at_utc DESC LIMIT {parameter}",
                (max(1, min(limit, 1000)),),
            ).fetchall()
        output: list[dict[str, Any]] = []
        for row in rows:
            decoded = self._decode_row(row)
            details = decoded.get("details_json")
            if isinstance(details, str):
                try:
                    decoded["details"] = json.loads(details)
                except json.JSONDecodeError:
                    decoded["details"] = {"raw": details}
            else:
                decoded["details"] = details or {}
            decoded.pop("details_json", None)
            output.append(decoded)
        return output

    def network_summary(
        self, catalog_station_ids: Iterable[str], *, freshness_minutes: int = 90,
        reporting_window_hours: int = 24,
    ) -> dict[str, Any]:
        catalog = set(str(item) for item in catalog_station_ids if str(item))
        latest = self.latest_observations(limit=max(2000, len(catalog) * 2))
        now = datetime.now(timezone.utc)
        fresh = delayed = stale = 0
        reporting_ids: set[str] = set()
        latest_timestamp: Optional[datetime] = None
        source_counts: dict[str, int] = {}
        for row in latest:
            timestamp = _parse_utc(row.get("observation_timestamp_utc"))
            if timestamp is None:
                continue
            if latest_timestamp is None or timestamp > latest_timestamp:
                latest_timestamp = timestamp
            age = max(0.0, (now - timestamp).total_seconds() / 60.0)
            if age <= reporting_window_hours * 60:
                reporting_ids.add(str(row["canonical_station_id"]))
                source = str(row.get("provider") or "UNKNOWN")
                source_counts[source] = source_counts.get(source, 0) + 1
                if age <= freshness_minutes:
                    fresh += 1
                elif age <= freshness_minutes * 2:
                    delayed += 1
                else:
                    stale += 1
        return {
            "catalog_stations": len(catalog),
            "currently_reporting_stations": len(reporting_ids),
            "fresh_stations": fresh,
            "delayed_stations": delayed,
            "stale_reporting_stations": stale,
            "offline_or_silent_catalog_stations": max(0, len(catalog - reporting_ids)),
            "observation_records": self.ingestion_health()["observation_records"],
            "latest_observation_utc": latest_timestamp.isoformat().replace("+00:00", "Z") if latest_timestamp else None,
            "latest_observation_age_minutes": round((now - latest_timestamp).total_seconds() / 60.0, 1) if latest_timestamp else None,
            "reporting_window_hours": reporting_window_hours,
            "freshness_threshold_minutes": freshness_minutes,
            "reporting_by_source": source_counts,
            "storage": self.durability,
        }

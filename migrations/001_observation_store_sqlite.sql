PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    observation_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    provider_station_id TEXT NOT NULL,
    canonical_station_id TEXT NOT NULL,
    wigos_id TEXT,
    icao_code TEXT,
    station_name TEXT,
    state TEXT,
    district TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    elevation_m REAL,
    observation_timestamp_utc TEXT NOT NULL,
    provider_publication_timestamp_utc TEXT,
    ingestion_timestamp_utc TEXT NOT NULL,
    temperature_c REAL,
    pressure_hpa REAL,
    pressure_type TEXT NOT NULL,
    relative_humidity_pct REAL,
    humidity_observation_type TEXT NOT NULL,
    source_quality_flags_json TEXT NOT NULL DEFAULT '[]',
    raw_payload_hash TEXT NOT NULL,
    source_url TEXT,
    message_id TEXT,
    schema_version TEXT NOT NULL,
    source_type TEXT NOT NULL,
    is_direct_observation INTEGER NOT NULL,
    is_interpolated INTEGER NOT NULL,
    is_model_field INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observations_station_time
    ON observations(canonical_station_id, observation_timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_observations_provider_time
    ON observations(provider, observation_timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_observations_geo_time
    ON observations(latitude, longitude, observation_timestamp_utc DESC);

CREATE TABLE IF NOT EXISTS raw_payloads (
    raw_payload_hash TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    first_seen_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_watermarks (
    provider TEXT PRIMARY KEY,
    watermark_utc TEXT,
    updated_at_utc TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    finished_at_utc TEXT,
    status TEXT NOT NULL,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    dead_letter_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_provider_started
    ON ingestion_runs(provider, started_at_utc DESC);

CREATE TABLE IF NOT EXISTS dead_letters (
    dead_letter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    received_at_utc TEXT NOT NULL,
    reason TEXT NOT NULL,
    raw_payload_hash TEXT,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS source_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at_utc TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}'
);


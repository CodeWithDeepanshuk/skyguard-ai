CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    elevation_m DOUBLE PRECISION,
    observation_timestamp_utc TIMESTAMPTZ NOT NULL,
    provider_publication_timestamp_utc TIMESTAMPTZ,
    ingestion_timestamp_utc TIMESTAMPTZ NOT NULL,
    temperature_c DOUBLE PRECISION,
    pressure_hpa DOUBLE PRECISION,
    pressure_type TEXT NOT NULL CHECK (pressure_type IN (
        'STATION_PRESSURE', 'MEAN_SEA_LEVEL_PRESSURE', 'ALTIMETER_QNH', 'UNKNOWN'
    )),
    relative_humidity_pct DOUBLE PRECISION,
    humidity_observation_type TEXT NOT NULL CHECK (humidity_observation_type IN (
        'DIRECT', 'DERIVED', 'UNAVAILABLE'
    )),
    source_quality_flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw_payload_hash TEXT NOT NULL,
    source_url TEXT,
    message_id TEXT,
    schema_version TEXT NOT NULL,
    source_type TEXT NOT NULL,
    is_direct_observation BOOLEAN NOT NULL,
    is_interpolated BOOLEAN NOT NULL,
    is_model_field BOOLEAN NOT NULL
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
    payload_json JSONB NOT NULL,
    first_seen_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_watermarks (
    provider TEXT PRIMARY KEY,
    watermark_utc TIMESTAMPTZ,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id UUID PRIMARY KEY,
    provider TEXT NOT NULL,
    started_at_utc TIMESTAMPTZ NOT NULL,
    finished_at_utc TIMESTAMPTZ,
    status TEXT NOT NULL,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    dead_letter_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_provider_started
    ON ingestion_runs(provider, started_at_utc DESC);

CREATE TABLE IF NOT EXISTS dead_letters (
    dead_letter_id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    received_at_utc TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL,
    raw_payload_hash TEXT,
    payload_json JSONB
);

CREATE TABLE IF NOT EXISTS source_events (
    event_id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at_utc TIMESTAMPTZ NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb
);


-- Optional migration for a TimescaleDB-enabled PostgreSQL service.
-- Plain Render PostgreSQL remains fully supported when the extension is absent.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable(
            'observations',
            'observation_timestamp_utc',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
    END IF;
END
$$;


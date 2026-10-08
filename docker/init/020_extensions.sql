\set ON_ERROR_STOP on
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
    IF (SELECT count(*) FROM pg_extension
        WHERE extname IN ('postgis', 'timescaledb', 'vector')) <> 3 THEN
        RAISE EXCEPTION 'All three PostgreSQL extensions are required';
    END IF;
END
$$;
SELECT extname, extversion FROM pg_extension
WHERE extname IN ('postgis', 'timescaledb', 'vector') ORDER BY extname;

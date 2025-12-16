-- PostgreSQL initialization script for Ollama Monitor
-- Creates database, tables, indexes, and optional TimescaleDB setup

-- Create database (run as superuser)
-- CREATE DATABASE ollama_metrics;

-- Connect to the database
\c ollama_metrics;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Enable TimescaleDB if available (comment out if not using TimescaleDB)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Metrics table
CREATE TABLE IF NOT EXISTS ollama_metrics (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metadata JSONB,
    CONSTRAINT ollama_metrics_pkey PRIMARY KEY (id, timestamp)
);

-- Request logs table
CREATE TABLE IF NOT EXISTS request_logs (
    id BIGSERIAL,
    request_id UUID NOT NULL UNIQUE DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL,
    model VARCHAR(255) NOT NULL,
    tokens_generated INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    CONSTRAINT request_logs_pkey PRIMARY KEY (id, timestamp)
);

-- Convert to TimescaleDB hypertables (comment out if not using TimescaleDB)
SELECT create_hypertable('ollama_metrics', 'timestamp', if_not_exists => TRUE, migrate_data => TRUE);
SELECT create_hypertable('request_logs', 'timestamp', if_not_exists => TRUE, migrate_data => TRUE);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON ollama_metrics (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_service_time ON ollama_metrics (service_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_type_time ON ollama_metrics (metric_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON ollama_metrics (metric_name);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON request_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_model_time ON request_logs (model, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_status_time ON request_logs (status, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_request_id ON request_logs (request_id);

-- Create composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_metrics_composite ON ollama_metrics (service_name, metric_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_composite ON request_logs (model, status, timestamp DESC);

-- Set up compression policy (TimescaleDB only)
-- Compress data older than 7 days
SELECT add_compression_policy('ollama_metrics', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('request_logs', INTERVAL '7 days', if_not_exists => TRUE);

-- Set up retention policy (TimescaleDB only)
-- Keep data for 90 days
SELECT add_retention_policy('ollama_metrics', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('request_logs', INTERVAL '90 days', if_not_exists => TRUE);

-- Create continuous aggregates for hourly stats (TimescaleDB only)
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    service_name,
    metric_name,
    SUM(metric_value) AS total_value,
    AVG(metric_value) AS avg_value,
    MIN(metric_value) AS min_value,
    MAX(metric_value) AS max_value,
    COUNT(*) AS sample_count
FROM ollama_metrics
GROUP BY hour, service_name, metric_name
WITH NO DATA;

-- Create continuous aggregate for model stats
CREATE MATERIALIZED VIEW IF NOT EXISTS model_stats_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    model,
    COUNT(*) AS request_count,
    COUNT(*) FILTER (WHERE status = 'success') AS success_count,
    COUNT(*) FILTER (WHERE status = 'error') AS error_count,
    SUM(tokens_generated) AS total_tokens,
    AVG(latency_ms) AS avg_latency_ms,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms) AS p50_latency_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99_latency_ms
FROM request_logs
GROUP BY hour, model
WITH NO DATA;

-- Refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy('metrics_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('model_stats_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Create daily summary view for dashboard
CREATE OR REPLACE VIEW daily_summary AS
SELECT
    date_trunc('day', timestamp) AS day,
    COUNT(*) AS total_requests,
    COUNT(*) FILTER (WHERE status = 'success') AS successful_requests,
    COUNT(*) FILTER (WHERE status = 'error') AS failed_requests,
    SUM(tokens_generated) AS total_tokens_generated,
    AVG(latency_ms)::NUMERIC(10,2) AS avg_latency_ms,
    COUNT(DISTINCT model) AS unique_models
FROM request_logs
GROUP BY date_trunc('day', timestamp)
ORDER BY day DESC;

-- Create function for real-time stats
CREATE OR REPLACE FUNCTION get_current_stats(time_window INTERVAL DEFAULT '1 hour')
RETURNS TABLE (
    total_requests BIGINT,
    successful_requests BIGINT,
    failed_requests BIGINT,
    total_tokens BIGINT,
    avg_latency NUMERIC,
    requests_per_minute NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE status = 'success')::BIGINT,
        COUNT(*) FILTER (WHERE status = 'error')::BIGINT,
        COALESCE(SUM(tokens_generated), 0)::BIGINT,
        COALESCE(AVG(latency_ms), 0)::NUMERIC(10,2),
        (COUNT(*) / EXTRACT(EPOCH FROM time_window) * 60)::NUMERIC(10,2)
    FROM request_logs
    WHERE timestamp >= NOW() - time_window;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO ollama_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ollama_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ollama_app;

-- Add comments for documentation
COMMENT ON TABLE ollama_metrics IS 'Stores all OTEL metrics from Ollama service';
COMMENT ON TABLE request_logs IS 'Stores detailed request logs for analysis';
COMMENT ON VIEW daily_summary IS 'Aggregated daily statistics for dashboard';
COMMENT ON FUNCTION get_current_stats IS 'Returns real-time statistics for the specified time window';

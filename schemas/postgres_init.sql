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
    metric_metadata JSONB,
    CONSTRAINT ollama_metrics_pkey PRIMARY KEY (id, timestamp)
);

-- Request logs table
CREATE TABLE IF NOT EXISTS request_logs (
    id BIGSERIAL,
    request_id UUID NOT NULL UNIQUE DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL,
    model VARCHAR(255) NOT NULL,
    prompt_text TEXT DEFAULT '',
    response_text TEXT DEFAULT '',
    prompt_tokens INTEGER DEFAULT 0,
    tokens_generated INTEGER NOT NULL,
    total_tokens INTEGER DEFAULT 0,
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

-- Model repository table for storing model metadata and user preferences
CREATE TABLE IF NOT EXISTS model_repository (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    description TEXT,
    category VARCHAR(100) DEFAULT 'general',
    size_label VARCHAR(50),
    size_bytes BIGINT DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE,
    is_installed BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    total_tokens_generated BIGINT DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    installed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for model repository
CREATE INDEX IF NOT EXISTS idx_model_repo_name ON model_repository (model_name);
CREATE INDEX IF NOT EXISTS idx_model_repo_favorite ON model_repository (is_favorite) WHERE is_favorite = TRUE;
CREATE INDEX IF NOT EXISTS idx_model_repo_installed ON model_repository (is_installed) WHERE is_installed = TRUE;
CREATE INDEX IF NOT EXISTS idx_model_repo_category ON model_repository (category);
CREATE INDEX IF NOT EXISTS idx_model_repo_usage ON model_repository (usage_count DESC);

-- Function to update model usage stats
CREATE OR REPLACE FUNCTION update_model_usage()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO model_repository (model_name, usage_count, total_tokens_generated, last_used_at, is_installed)
    VALUES (NEW.model, 1, NEW.tokens_generated, NEW.timestamp, TRUE)
    ON CONFLICT (model_name) DO UPDATE SET
        usage_count = model_repository.usage_count + 1,
        total_tokens_generated = model_repository.total_tokens_generated + NEW.tokens_generated,
        last_used_at = NEW.timestamp,
        is_installed = TRUE,
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update model usage on new request logs
DROP TRIGGER IF EXISTS trigger_update_model_usage ON request_logs;
CREATE TRIGGER trigger_update_model_usage
    AFTER INSERT ON request_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_model_usage();

-- Insert default popular models into repository
INSERT INTO model_repository (model_name, display_name, description, category, size_label) VALUES
    ('llama3.2', 'Llama 3.2', 'Meta''s Llama 3.2 - latest and most capable', 'general', '1B-90B'),
    ('llama3.1', 'Llama 3.1', 'Meta''s Llama 3.1 - powerful open model', 'general', '8B-405B'),
    ('gemma3:1b', 'Gemma 3 1B', 'Google''s Gemma 3 - compact 1B model', 'general', '1B'),
    ('gemma3:4b', 'Gemma 3 4B', 'Google''s Gemma 3 - balanced 4B model', 'general', '4B'),
    ('gemma2', 'Gemma 2', 'Google''s Gemma 2 model', 'general', '2B-27B'),
    ('nemotron-mini', 'Nemotron Mini', 'NVIDIA Nemotron Mini - efficient small model', 'general', '4B'),
    ('mistral', 'Mistral 7B', 'Mistral AI''s 7B model - fast and efficient', 'general', '7B'),
    ('mixtral', 'Mixtral 8x7B', 'Mistral''s mixture of experts model', 'general', '8x7B'),
    ('phi3', 'Phi-3', 'Microsoft''s small but capable model', 'general', '3.8B'),
    ('phi3:mini', 'Phi-3 Mini', 'Microsoft Phi-3 Mini', 'general', '3.8B'),
    ('qwen2.5', 'Qwen 2.5', 'Alibaba''s Qwen 2.5 model', 'general', '0.5B-72B'),
    ('qwen2.5:1.5b', 'Qwen 2.5 1.5B', 'Alibaba''s Qwen 2.5 - tiny variant', 'general', '1.5B'),
    ('codellama', 'Code Llama', 'Meta''s code-specialized Llama', 'coding', '7B-34B'),
    ('deepseek-coder', 'DeepSeek Coder', 'DeepSeek''s coding model', 'coding', '1.3B-33B'),
    ('deepseek-coder-v2', 'DeepSeek Coder V2', 'DeepSeek Coder V2 - improved coding', 'coding', '16B-236B'),
    ('starcoder2', 'StarCoder 2', 'BigCode''s StarCoder 2', 'coding', '3B-15B'),
    ('tinyllama', 'TinyLlama', 'Tiny but fast for testing', 'general', '1.1B'),
    ('neural-chat', 'Neural Chat', 'Intel''s neural chat model', 'chat', '7B'),
    ('starling-lm', 'Starling LM', 'Berkeley''s Starling model', 'chat', '7B'),
    ('dolphin-mixtral', 'Dolphin Mixtral', 'Uncensored Mixtral variant', 'general', '8x7B')
ON CONFLICT (model_name) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    description  = EXCLUDED.description,
    category     = EXCLUDED.category,
    size_label   = EXCLUDED.size_label;

-- View for model repository with usage stats
CREATE OR REPLACE VIEW model_repository_stats AS
SELECT
    mr.*,
    COALESCE(rs.request_count, 0) AS total_requests,
    COALESCE(rs.avg_latency, 0) AS avg_latency_ms,
    COALESCE(rs.error_rate, 0) AS error_rate
FROM model_repository mr
LEFT JOIN (
    SELECT
        model,
        COUNT(*) AS request_count,
        AVG(latency_ms) AS avg_latency,
        (COUNT(*) FILTER (WHERE status = 'error')::FLOAT / NULLIF(COUNT(*), 0) * 100) AS error_rate
    FROM request_logs
    WHERE timestamp > NOW() - INTERVAL '30 days'
    GROUP BY model
) rs ON mr.model_name = rs.model;

COMMENT ON TABLE model_repository IS 'Stores model metadata, preferences, and usage statistics';
COMMENT ON VIEW model_repository_stats IS 'Model repository with aggregated usage statistics';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO ollama_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ollama_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ollama_app;

-- Add comments for documentation
COMMENT ON TABLE ollama_metrics IS 'Stores all OTEL metrics from Ollama service';
COMMENT ON TABLE request_logs IS 'Stores detailed request logs for analysis';
COMMENT ON VIEW daily_summary IS 'Aggregated daily statistics for dashboard';
COMMENT ON FUNCTION get_current_stats IS 'Returns real-time statistics for the specified time window';

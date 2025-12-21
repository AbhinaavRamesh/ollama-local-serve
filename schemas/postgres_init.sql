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

-- Insert default popular models into repository (general and reasoning only)
INSERT INTO model_repository (model_name, display_name, description, category, size_label, is_default) VALUES
    -- Gemma 3 (General)
    ('gemma3', 'Gemma 3', 'Google''s most capable single GPU model', 'general', '270M-27B', FALSE),
    ('gemma3:1b', 'Gemma 3 1B', 'Google Gemma 3 - compact 1B variant', 'general', '1B', FALSE),
    ('gemma3:4b', 'Gemma 3 4B', 'Google Gemma 3 - balanced 4B variant', 'general', '4B', FALSE),
    ('gemma3:12b', 'Gemma 3 12B', 'Google Gemma 3 - 12B variant', 'general', '12B', FALSE),
    ('gemma3:27b', 'Gemma 3 27B', 'Google Gemma 3 - largest 27B variant', 'general', '27B', FALSE),
    -- Gemma 2 (General)
    ('gemma2', 'Gemma 2', 'Google Gemma 2 - high-performing and efficient', 'general', '2B-27B', FALSE),
    ('gemma2:2b', 'Gemma 2 2B', 'Google Gemma 2 - compact 2B variant', 'general', '2B', FALSE),
    ('gemma2:9b', 'Gemma 2 9B', 'Google Gemma 2 - balanced 9B variant', 'general', '9B', FALSE),
    -- Llama 3.1 (General)
    ('llama3.1', 'Llama 3.1', 'Meta''s state-of-the-art with tool support', 'general', '8B-405B', FALSE),
    ('llama3.1:8b', 'Llama 3.1 8B', 'Meta Llama 3.1 - efficient 8B variant', 'general', '8B', FALSE),
    ('llama3.1:70b', 'Llama 3.1 70B', 'Meta Llama 3.1 - powerful 70B variant', 'general', '70B', FALSE),
    -- Llama 3.2 (General)
    ('llama3.2', 'Llama 3.2', 'Meta''s compact models with tool support', 'general', '1B-3B', FALSE),
    ('llama3.2:1b', 'Llama 3.2 1B', 'Meta Llama 3.2 - tiny efficient 1B model', 'general', '1B', TRUE),
    ('llama3.2:3b', 'Llama 3.2 3B', 'Meta Llama 3.2 - compact 3B model', 'general', '3B', FALSE),
    -- Llama 3.3 (General)
    ('llama3.3', 'Llama 3.3', 'Similar performance to Llama 3.1 405B', 'general', '70B', FALSE),
    ('llama3.3:70b', 'Llama 3.3 70B', 'Meta Llama 3.3 - 70B with 405B performance', 'general', '70B', FALSE),
    -- Qwen 3 (General)
    ('qwen3', 'Qwen 3', 'Alibaba''s latest with MoE and thinking mode', 'general', '0.6B-235B', FALSE),
    ('qwen3:0.6b', 'Qwen 3 0.6B', 'Qwen 3 - tiny 0.6B variant', 'general', '0.6B', FALSE),
    ('qwen3:4b', 'Qwen 3 4B', 'Qwen 3 - compact 4B variant', 'general', '4B', FALSE),
    ('qwen3:8b', 'Qwen 3 8B', 'Qwen 3 - balanced 8B variant', 'general', '8B', FALSE),
    ('qwen3:14b', 'Qwen 3 14B', 'Qwen 3 - capable 14B variant', 'general', '14B', FALSE),
    ('qwen3:32b', 'Qwen 3 32B', 'Qwen 3 - powerful 32B variant', 'general', '32B', FALSE),
    -- Qwen 2.5 (General)
    ('qwen2.5', 'Qwen 2.5', '128K context, multilingual, tool support', 'general', '0.5B-72B', FALSE),
    ('qwen2.5:0.5b', 'Qwen 2.5 0.5B', 'Qwen 2.5 - tiny 0.5B variant', 'general', '0.5B', FALSE),
    ('qwen2.5:1.5b', 'Qwen 2.5 1.5B', 'Qwen 2.5 - small 1.5B variant', 'general', '1.5B', FALSE),
    ('qwen2.5:3b', 'Qwen 2.5 3B', 'Qwen 2.5 - compact 3B variant', 'general', '3B', FALSE),
    ('qwen2.5:7b', 'Qwen 2.5 7B', 'Qwen 2.5 - balanced 7B variant', 'general', '7B', FALSE),
    ('qwen2.5:14b', 'Qwen 2.5 14B', 'Qwen 2.5 - capable 14B variant', 'general', '14B', FALSE),
    ('qwen2.5:32b', 'Qwen 2.5 32B', 'Qwen 2.5 - powerful 32B variant', 'general', '32B', FALSE),
    -- DeepSeek R1 (Reasoning)
    ('deepseek-r1', 'DeepSeek R1', 'Open reasoning models with thinking mode', 'reasoning', '1.5B-671B', FALSE),
    ('deepseek-r1:1.5b', 'DeepSeek R1 1.5B', 'DeepSeek R1 - tiny reasoning model', 'reasoning', '1.5B', FALSE),
    ('deepseek-r1:7b', 'DeepSeek R1 7B', 'DeepSeek R1 - compact reasoning model', 'reasoning', '7B', FALSE),
    ('deepseek-r1:8b', 'DeepSeek R1 8B', 'DeepSeek R1 - balanced reasoning model', 'reasoning', '8B', FALSE),
    ('deepseek-r1:14b', 'DeepSeek R1 14B', 'DeepSeek R1 - capable reasoning model', 'reasoning', '14B', FALSE),
    ('deepseek-r1:32b', 'DeepSeek R1 32B', 'DeepSeek R1 - powerful reasoning model', 'reasoning', '32B', FALSE),
    ('deepseek-r1:70b', 'DeepSeek R1 70B', 'DeepSeek R1 - large reasoning model', 'reasoning', '70B', FALSE),
    -- DeepSeek V3 (General)
    ('deepseek-v3', 'DeepSeek V3', 'MoE with 671B total, 37B active params', 'general', '671B', FALSE),
    -- GPT-OSS (Reasoning)
    ('gpt-oss', 'GPT-OSS', 'OpenAI''s open-weight models with thinking mode', 'reasoning', '20B-120B', FALSE),
    ('gpt-oss:20b', 'GPT-OSS 20B', 'OpenAI GPT-OSS - compact 20B variant', 'reasoning', '20B', FALSE),
    ('gpt-oss:120b', 'GPT-OSS 120B', 'OpenAI GPT-OSS - large 120B variant', 'reasoning', '120B', FALSE),
    -- Phi 3 & 4 (General)
    ('phi3', 'Phi-3', 'Microsoft''s lightweight state-of-the-art', 'general', '3.8B-14B', FALSE),
    ('phi3:mini', 'Phi-3 Mini', 'Microsoft Phi-3 Mini - 3.8B', 'general', '3.8B', FALSE),
    ('phi4', 'Phi-4', 'Microsoft''s state-of-the-art 14B model', 'general', '14B', FALSE),
    -- Mistral (General)
    ('mistral', 'Mistral 7B', 'Mistral AI 7B v0.3 with tool support', 'general', '7B', FALSE),
    ('mistral-nemo', 'Mistral Nemo', 'Mistral 12B with 128K context', 'general', '12B', FALSE),
    ('mistral-small', 'Mistral Small', 'Mistral 22-24B with tool support', 'general', '22B-24B', FALSE),
    -- Mixtral (General - MoE)
    ('mixtral', 'Mixtral', 'Mistral Mixture of Experts with tool support', 'general', '8x7B-8x22B', FALSE),
    ('mixtral:8x7b', 'Mixtral 8x7B', 'Mixtral - 8x7B MoE variant', 'general', '8x7B', FALSE),
    ('mixtral:8x22b', 'Mixtral 8x22B', 'Mixtral - 8x22B MoE variant', 'general', '8x22B', FALSE)
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

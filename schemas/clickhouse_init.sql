-- ClickHouse initialization script for Ollama Monitor
-- Creates database, tables, and materialized views for metrics storage

-- Create database
CREATE DATABASE IF NOT EXISTS ollama_metrics;

USE ollama_metrics;

-- Metrics table with ReplacingMergeTree for efficient deduplication
CREATE TABLE IF NOT EXISTS ollama_metrics (
    timestamp DateTime,
    service_name String,
    metric_type String,
    metric_name String,
    metric_value Float64,
    metadata String,
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_metric metric_type TYPE set(1) GRANULARITY 1,
    INDEX idx_service service_name TYPE set(1) GRANULARITY 1
) ENGINE = ReplacingMergeTree()
ORDER BY (timestamp, service_name, metric_type, metric_name)
PARTITION BY toYYYYMMDD(timestamp)
TTL timestamp + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

-- Request logs table for detailed request tracking
CREATE TABLE IF NOT EXISTS request_logs (
    request_id String,
    timestamp DateTime,
    model String,
    tokens_generated UInt32,
    latency_ms UInt32,
    status String,
    error_message Nullable(String),
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_model model TYPE set(100) GRANULARITY 1,
    INDEX idx_status status TYPE set(10) GRANULARITY 1
) ENGINE = MergeTree()
ORDER BY (timestamp, model, status)
PARTITION BY toYYYYMMDD(timestamp)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Materialized view for hourly aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_hourly_mv
ENGINE = SummingMergeTree()
ORDER BY (hour, service_name, metric_name)
PARTITION BY toYYYYMM(hour)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    service_name,
    metric_name,
    sum(metric_value) AS total_value,
    avg(metric_value) AS avg_value,
    min(metric_value) AS min_value,
    max(metric_value) AS max_value,
    count() AS sample_count
FROM ollama_metrics
GROUP BY hour, service_name, metric_name;

-- Materialized view for request statistics per model
CREATE MATERIALIZED VIEW IF NOT EXISTS model_stats_hourly_mv
ENGINE = SummingMergeTree()
ORDER BY (hour, model)
PARTITION BY toYYYYMM(hour)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    model,
    count() AS request_count,
    countIf(status = 'success') AS success_count,
    countIf(status = 'error') AS error_count,
    sum(tokens_generated) AS total_tokens,
    avg(latency_ms) AS avg_latency_ms,
    quantile(0.50)(latency_ms) AS p50_latency_ms,
    quantile(0.95)(latency_ms) AS p95_latency_ms,
    quantile(0.99)(latency_ms) AS p99_latency_ms
FROM request_logs
GROUP BY hour, model;

-- Daily summary table for dashboard overview
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_summary_mv
ENGINE = SummingMergeTree()
ORDER BY (day, service_name)
PARTITION BY toYYYYMM(day)
AS SELECT
    toDate(timestamp) AS day,
    service_name,
    count() AS total_requests,
    countIf(status = 'success') AS successful_requests,
    countIf(status = 'error') AS failed_requests,
    sum(tokens_generated) AS total_tokens_generated,
    avg(latency_ms) AS avg_latency_ms
FROM request_logs
GROUP BY day, service_name;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT ON ollama_metrics.* TO 'ollama_app';

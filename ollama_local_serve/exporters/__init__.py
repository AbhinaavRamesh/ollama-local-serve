"""
Metrics exporters package for Ollama Local Serve.

Provides exporters for exporting metrics and request logs to various
time-series databases including ClickHouse and PostgreSQL.

Components:
    - BaseExporter: Abstract base class for all exporters
    - ClickHouseExporter: Exports to ClickHouse with ReplacingMergeTree
    - PostgresExporter: Exports to PostgreSQL with optional TimescaleDB support
    - MetricRecord: Data class for metric records
    - RequestLogRecord: Data class for request log records
    - ExporterConfig: Base configuration for exporters

Example:
    ```python
    from ollama_local_serve.exporters import (
        ClickHouseExporter,
        ClickHouseConfig,
        PostgresExporter,
        PostgresConfig,
        MetricRecord,
        RequestLogRecord,
        MetricType,
    )
    from datetime import datetime

    # Use ClickHouse
    ch_config = ClickHouseConfig(host="localhost", database="ollama_metrics")
    async with ClickHouseExporter(ch_config) as exporter:
        await exporter.add_metric(
            MetricRecord(
                timestamp=datetime.utcnow(),
                service_name="my-service",
                metric_type=MetricType.REQUEST,
                metric_name="requests_total",
                metric_value=1.0,
            )
        )

    # Or use PostgreSQL
    pg_config = PostgresConfig(host="localhost", database="ollama_metrics")
    async with PostgresExporter(pg_config) as exporter:
        await exporter.add_log(
            RequestLogRecord(
                request_id="uuid-here",
                timestamp=datetime.utcnow(),
                model="llama2",
                tokens_generated=150,
                latency_ms=250,
                status="success",
            )
        )
    ```
"""

from ollama_local_serve.exporters.base import (
    BaseExporter,
    ExporterConfig,
    MetricRecord,
    MetricType,
    RequestLogRecord,
)
from ollama_local_serve.exporters.clickhouse_exporter import (
    ClickHouseConfig,
    ClickHouseExporter,
)
from ollama_local_serve.exporters.postgres_exporter import (
    PostgresConfig,
    PostgresExporter,
)

__all__ = [
    # Base classes
    "BaseExporter",
    "ExporterConfig",
    "MetricRecord",
    "RequestLogRecord",
    "MetricType",
    # ClickHouse
    "ClickHouseExporter",
    "ClickHouseConfig",
    # PostgreSQL
    "PostgresExporter",
    "PostgresConfig",
]

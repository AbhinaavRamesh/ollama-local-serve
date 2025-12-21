"""
ClickHouse exporter for Ollama metrics.

Exports metrics and request logs to ClickHouse for time-series analysis.
Uses batch processing and ReplacingMergeTree for efficient storage.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any

from clickhouse_driver import Client as ClickHouseClient
from clickhouse_driver.errors import Error as ClickHouseError

from ollama_local_serve.exporters.base import (
    BaseExporter,
    ExporterConfig,
    MetricRecord,
    RequestLogRecord,
)

logger = logging.getLogger(__name__)


# SQL for creating metrics table
CREATE_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS ollama_metrics (
    timestamp DateTime,
    service_name String,
    metric_type String,
    metric_name String,
    metric_value Float64,
    metric_metadata String,
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_metric metric_type TYPE set(1) GRANULARITY 1
) ENGINE = ReplacingMergeTree()
ORDER BY (timestamp, service_name, metric_type)
PARTITION BY toYYYYMMDD(timestamp)
"""

# SQL for creating request logs table
CREATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS request_logs (
    request_id String,
    timestamp DateTime,
    model String,
    tokens_generated UInt32,
    latency_ms UInt32,
    status String,
    error_message Nullable(String),
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_model model TYPE set(1) GRANULARITY 1
) ENGINE = MergeTree()
ORDER BY (timestamp, model)
PARTITION BY toYYYYMMDD(timestamp)
"""


@dataclass
class ClickHouseConfig(ExporterConfig):
    """
    ClickHouse-specific exporter configuration.

    Attributes:
        host: ClickHouse server host.
        port: ClickHouse native protocol port.
        database: Database name.
        user: Database user.
        password: Database password.
        secure: Whether to use secure connection.
        connect_timeout: Connection timeout in seconds.
    """

    host: str = "localhost"
    port: int = 9000
    database: str = "ollama_metrics"
    user: str = "default"
    password: str = ""
    secure: bool = False
    connect_timeout: int = 10


class ClickHouseExporter(BaseExporter):
    """
    ClickHouse exporter for metrics and logs.

    Implements batch processing with configurable intervals and automatic
    table creation using ReplacingMergeTree engine.

    Example:
        ```python
        from ollama_local_serve.exporters import ClickHouseExporter, ClickHouseConfig

        config = ClickHouseConfig(
            host="localhost",
            port=9000,
            database="ollama_metrics",
        )
        exporter = ClickHouseExporter(config)

        async with exporter:
            # Add metrics
            await exporter.add_metric(metric_record)
            await exporter.add_log(log_record)
        ```
    """

    def __init__(self, config: Optional[ClickHouseConfig] = None) -> None:
        """
        Initialize the ClickHouse exporter.

        Args:
            config: ClickHouse configuration. Uses defaults if None.
        """
        self._ch_config = config or ClickHouseConfig()
        super().__init__(self._ch_config)
        self._client: Optional[ClickHouseClient] = None

        logger.info(
            f"ClickHouseExporter initialized: {self._ch_config.host}:"
            f"{self._ch_config.port}/{self._ch_config.database}"
        )

    async def _connect(self) -> None:
        """Establish connection to ClickHouse."""
        try:
            self._client = ClickHouseClient(
                host=self._ch_config.host,
                port=self._ch_config.port,
                database=self._ch_config.database,
                user=self._ch_config.user,
                password=self._ch_config.password,
                secure=self._ch_config.secure,
                connect_timeout=self._ch_config.connect_timeout,
            )

            # Test connection
            self._client.execute("SELECT 1")
            logger.info("Connected to ClickHouse successfully")

        except ClickHouseError as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise ConnectionError(f"ClickHouse connection failed: {e}")

    async def _disconnect(self) -> None:
        """Close ClickHouse connection."""
        if self._client is not None:
            try:
                self._client.disconnect()
                logger.info("Disconnected from ClickHouse")
            except Exception as e:
                logger.warning(f"Error disconnecting from ClickHouse: {e}")
            finally:
                self._client = None

    async def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        if self._client is None:
            raise RuntimeError("Not connected to ClickHouse")

        try:
            # Create database if not exists
            self._client.execute(
                f"CREATE DATABASE IF NOT EXISTS {self._ch_config.database}"
            )

            # Create metrics table
            self._client.execute(CREATE_METRICS_TABLE)
            logger.debug("Ensured ollama_metrics table exists")

            # Create logs table
            self._client.execute(CREATE_LOGS_TABLE)
            logger.debug("Ensured request_logs table exists")

            logger.info("ClickHouse tables verified/created")

        except ClickHouseError as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def _write_metrics_batch(self, records: List[MetricRecord]) -> None:
        """Write metrics batch to ClickHouse."""
        if self._client is None:
            raise RuntimeError("Not connected to ClickHouse")

        if not records:
            return

        try:
            # Prepare data for batch insert
            data = [
                (
                    record.timestamp,
                    record.service_name,
                    record.metric_type.value,
                    record.metric_name,
                    record.metric_value,
                    json.dumps(record.metadata),
                )
                for record in records
            ]

            self._client.execute(
                """
                INSERT INTO ollama_metrics
                (timestamp, service_name, metric_type, metric_name, metric_value, metric_metadata)
                VALUES
                """,
                data,
            )

            logger.debug(f"Wrote {len(records)} metrics to ClickHouse")

        except ClickHouseError as e:
            logger.error(f"Failed to write metrics batch: {e}")
            raise

    async def _write_logs_batch(self, records: List[RequestLogRecord]) -> None:
        """Write request logs batch to ClickHouse."""
        if self._client is None:
            raise RuntimeError("Not connected to ClickHouse")

        if not records:
            return

        try:
            # Prepare data for batch insert
            data = [
                (
                    record.request_id,
                    record.timestamp,
                    record.model,
                    record.tokens_generated,
                    record.latency_ms,
                    record.status,
                    record.error_message,
                )
                for record in records
            ]

            self._client.execute(
                """
                INSERT INTO request_logs
                (request_id, timestamp, model, tokens_generated, latency_ms, status, error_message)
                VALUES
                """,
                data,
            )

            logger.debug(f"Wrote {len(records)} logs to ClickHouse")

        except ClickHouseError as e:
            logger.error(f"Failed to write logs batch: {e}")
            raise

    async def query_metrics(
        self,
        metric_name: Optional[str] = None,
        metric_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[dict]:
        """
        Query metrics from ClickHouse.

        Args:
            metric_name: Filter by metric name.
            metric_type: Filter by metric type.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum number of results.

        Returns:
            List of metric records as dictionaries.
        """
        if self._client is None:
            raise RuntimeError("Not connected to ClickHouse")

        conditions = []
        params = {}

        if metric_name:
            conditions.append("metric_name = %(metric_name)s")
            params["metric_name"] = metric_name

        if metric_type:
            conditions.append("metric_type = %(metric_type)s")
            params["metric_type"] = metric_type

        if start_time:
            conditions.append("timestamp >= %(start_time)s")
            params["start_time"] = start_time

        if end_time:
            conditions.append("timestamp <= %(end_time)s")
            params["end_time"] = end_time

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT
                timestamp, service_name, metric_type, metric_name,
                metric_value, metric_metadata
            FROM ollama_metrics
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %(limit)s
        """
        params["limit"] = limit

        try:
            result = self._client.execute(query, params, with_column_types=True)
            rows, columns = result
            column_names = [col[0] for col in columns]

            return [dict(zip(column_names, row)) for row in rows]

        except ClickHouseError as e:
            logger.error(f"Failed to query metrics: {e}")
            raise

    async def query_logs(
        self,
        model: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """
        Query request logs from ClickHouse.

        Args:
            model: Filter by model name.
            status: Filter by status (success/error).
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of log records as dictionaries.
        """
        if self._client is None:
            raise RuntimeError("Not connected to ClickHouse")

        conditions = []
        params = {}

        if model:
            conditions.append("model = %(model)s")
            params["model"] = model

        if status:
            conditions.append("status = %(status)s")
            params["status"] = status

        if start_time:
            conditions.append("timestamp >= %(start_time)s")
            params["start_time"] = start_time

        if end_time:
            conditions.append("timestamp <= %(end_time)s")
            params["end_time"] = end_time

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT
                request_id, timestamp, model, tokens_generated,
                latency_ms, status, error_message
            FROM request_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """
        params["limit"] = limit
        params["offset"] = offset

        try:
            result = self._client.execute(query, params, with_column_types=True)
            rows, columns = result
            column_names = [col[0] for col in columns]

            return [dict(zip(column_names, row)) for row in rows]

        except ClickHouseError as e:
            logger.error(f"Failed to query logs: {e}")
            raise

    async def get_aggregated_stats(
        self,
        time_range_hours: int = 1,
        granularity_minutes: int = 1,
    ) -> List[dict]:
        """
        Get aggregated statistics over a time range.

        Args:
            time_range_hours: Number of hours to look back.
            granularity_minutes: Aggregation granularity in minutes.

        Returns:
            List of aggregated statistics.
        """
        if self._client is None:
            raise RuntimeError("Not connected to ClickHouse")

        query = """
            SELECT
                toStartOfInterval(timestamp, INTERVAL %(granularity)s MINUTE) as time_bucket,
                sum(CASE WHEN metric_name = 'ollama_tokens_generated_total'
                    THEN metric_value ELSE 0 END) as tokens_total,
                avg(CASE WHEN metric_name = 'ollama_request_latency_ms'
                    THEN metric_value ELSE NULL END) as avg_latency_ms,
                count(CASE WHEN metric_name = 'ollama_requests_total'
                    THEN 1 ELSE NULL END) as request_count
            FROM ollama_metrics
            WHERE timestamp >= now() - INTERVAL %(hours)s HOUR
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
        """

        try:
            result = self._client.execute(
                query,
                {"hours": time_range_hours, "granularity": granularity_minutes},
                with_column_types=True,
            )
            rows, columns = result
            column_names = [col[0] for col in columns]

            return [dict(zip(column_names, row)) for row in rows]

        except ClickHouseError as e:
            logger.error(f"Failed to get aggregated stats: {e}")
            raise

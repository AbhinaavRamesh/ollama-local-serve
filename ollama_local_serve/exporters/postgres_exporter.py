"""
PostgreSQL exporter for Ollama metrics.

Exports metrics and request logs to PostgreSQL with optional TimescaleDB
support for time-series optimization. Uses SQLAlchemy with asyncpg.
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    BigInteger,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from ollama_local_serve.exporters.base import (
    BaseExporter,
    ExporterConfig,
    MetricRecord,
    RequestLogRecord,
)

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class OllamaMetrics(Base):
    """SQLAlchemy model for ollama_metrics table."""

    __tablename__ = "ollama_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    service_name = Column(String(255), nullable=False)
    metric_type = Column(String(50), nullable=False)
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    metadata = Column(JSONB, nullable=True)


class RequestLogs(Base):
    """SQLAlchemy model for request_logs table."""

    __tablename__ = "request_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(UUID(as_uuid=True), unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    model = Column(String(255), nullable=False, index=True)
    tokens_generated = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, index=True)
    error_message = Column(Text, nullable=True)


@dataclass
class PostgresConfig(ExporterConfig):
    """
    PostgreSQL-specific exporter configuration.

    Attributes:
        host: PostgreSQL server host.
        port: PostgreSQL port.
        database: Database name.
        user: Database user.
        password: Database password.
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections.
        use_timescale: Whether to use TimescaleDB hypertables.
        ssl_mode: SSL mode for connection.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "ollama_metrics"
    user: str = "postgres"
    password: str = "postgres"
    pool_size: int = 5
    max_overflow: int = 10
    use_timescale: bool = True
    ssl_mode: str = "prefer"

    @property
    def connection_url(self) -> str:
        """Get async connection URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


class PostgresExporter(BaseExporter):
    """
    PostgreSQL exporter for metrics and logs.

    Implements batch processing with connection pooling and optional
    TimescaleDB hypertable support for time-series optimization.

    Example:
        ```python
        from ollama_local_serve.exporters import PostgresExporter, PostgresConfig

        config = PostgresConfig(
            host="localhost",
            port=5432,
            database="ollama_metrics",
            use_timescale=True,
        )
        exporter = PostgresExporter(config)

        async with exporter:
            await exporter.add_metric(metric_record)
            await exporter.add_log(log_record)
        ```
    """

    def __init__(self, config: Optional[PostgresConfig] = None) -> None:
        """
        Initialize the PostgreSQL exporter.

        Args:
            config: PostgreSQL configuration. Uses defaults if None.
        """
        self._pg_config = config or PostgresConfig()
        super().__init__(self._pg_config)
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None

        logger.info(
            f"PostgresExporter initialized: {self._pg_config.host}:"
            f"{self._pg_config.port}/{self._pg_config.database}"
        )

    async def _connect(self) -> None:
        """Establish connection to PostgreSQL."""
        try:
            self._engine = create_async_engine(
                self._pg_config.connection_url,
                pool_size=self._pg_config.pool_size,
                max_overflow=self._pg_config.max_overflow,
                echo=False,
            )

            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Test connection
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            logger.info("Connected to PostgreSQL successfully")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise ConnectionError(f"PostgreSQL connection failed: {e}")

    async def _disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if self._engine is not None:
            try:
                await self._engine.dispose()
                logger.info("Disconnected from PostgreSQL")
            except Exception as e:
                logger.warning(f"Error disconnecting from PostgreSQL: {e}")
            finally:
                self._engine = None
                self._session_factory = None

    async def _ensure_tables(self) -> None:
        """Create tables if they don't exist, optionally with TimescaleDB."""
        if self._engine is None:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            # Create tables using SQLAlchemy models
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.debug("Created base tables")

            # Setup TimescaleDB if enabled
            if self._pg_config.use_timescale:
                await self._setup_timescale()

            logger.info("PostgreSQL tables verified/created")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def _setup_timescale(self) -> None:
        """Setup TimescaleDB hypertables."""
        if self._engine is None:
            return

        async with self._engine.connect() as conn:
            try:
                # Enable TimescaleDB extension
                await conn.execute(
                    text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
                )
                await conn.commit()

                # Convert metrics table to hypertable
                try:
                    await conn.execute(
                        text(
                            """
                            SELECT create_hypertable(
                                'ollama_metrics', 'timestamp',
                                if_not_exists => TRUE
                            )
                            """
                        )
                    )
                    await conn.commit()
                    logger.debug("Created hypertable for ollama_metrics")
                except Exception as e:
                    logger.debug(f"Hypertable may already exist: {e}")

                # Convert logs table to hypertable
                try:
                    await conn.execute(
                        text(
                            """
                            SELECT create_hypertable(
                                'request_logs', 'timestamp',
                                if_not_exists => TRUE
                            )
                            """
                        )
                    )
                    await conn.commit()
                    logger.debug("Created hypertable for request_logs")
                except Exception as e:
                    logger.debug(f"Hypertable may already exist: {e}")

                # Create indexes for efficient queries
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS idx_metrics_service_time
                        ON ollama_metrics (service_name, timestamp DESC)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS idx_metrics_type_time
                        ON ollama_metrics (metric_type, timestamp DESC)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS idx_logs_model_time
                        ON request_logs (model, timestamp DESC)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS idx_logs_status_time
                        ON request_logs (status, timestamp DESC)
                        """
                    )
                )
                await conn.commit()

                logger.info("TimescaleDB setup completed")

            except Exception as e:
                logger.warning(f"TimescaleDB setup failed (may not be installed): {e}")

    async def _write_metrics_batch(self, records: List[MetricRecord]) -> None:
        """Write metrics batch to PostgreSQL."""
        if self._session_factory is None:
            raise RuntimeError("Not connected to PostgreSQL")

        if not records:
            return

        async with self._session_factory() as session:
            try:
                # Create ORM objects
                db_records = [
                    OllamaMetrics(
                        timestamp=record.timestamp,
                        service_name=record.service_name,
                        metric_type=record.metric_type.value,
                        metric_name=record.metric_name,
                        metric_value=record.metric_value,
                        metadata=record.metadata,
                    )
                    for record in records
                ]

                session.add_all(db_records)
                await session.commit()

                logger.debug(f"Wrote {len(records)} metrics to PostgreSQL")

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to write metrics batch: {e}")
                raise

    async def _write_logs_batch(self, records: List[RequestLogRecord]) -> None:
        """Write request logs batch to PostgreSQL."""
        if self._session_factory is None:
            raise RuntimeError("Not connected to PostgreSQL")

        if not records:
            return

        async with self._session_factory() as session:
            try:
                # Create ORM objects
                db_records = [
                    RequestLogs(
                        request_id=uuid.UUID(record.request_id)
                        if isinstance(record.request_id, str)
                        else record.request_id,
                        timestamp=record.timestamp,
                        model=record.model,
                        tokens_generated=record.tokens_generated,
                        latency_ms=record.latency_ms,
                        status=record.status,
                        error_message=record.error_message,
                    )
                    for record in records
                ]

                session.add_all(db_records)
                await session.commit()

                logger.debug(f"Wrote {len(records)} logs to PostgreSQL")

            except Exception as e:
                await session.rollback()
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
        Query metrics from PostgreSQL.

        Args:
            metric_name: Filter by metric name.
            metric_type: Filter by metric type.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum number of results.

        Returns:
            List of metric records as dictionaries.
        """
        if self._session_factory is None:
            raise RuntimeError("Not connected to PostgreSQL")

        conditions = []
        params = {"limit": limit}

        if metric_name:
            conditions.append("metric_name = :metric_name")
            params["metric_name"] = metric_name

        if metric_type:
            conditions.append("metric_type = :metric_type")
            params["metric_type"] = metric_type

        if start_time:
            conditions.append("timestamp >= :start_time")
            params["start_time"] = start_time

        if end_time:
            conditions.append("timestamp <= :end_time")
            params["end_time"] = end_time

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = text(
            f"""
            SELECT
                id, timestamp, service_name, metric_type, metric_name,
                metric_value, metadata
            FROM ollama_metrics
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit
            """
        )

        async with self._session_factory() as session:
            try:
                result = await session.execute(query, params)
                rows = result.fetchall()

                return [
                    {
                        "id": row[0],
                        "timestamp": row[1],
                        "service_name": row[2],
                        "metric_type": row[3],
                        "metric_name": row[4],
                        "metric_value": row[5],
                        "metadata": row[6],
                    }
                    for row in rows
                ]

            except Exception as e:
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
        Query request logs from PostgreSQL.

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
        if self._session_factory is None:
            raise RuntimeError("Not connected to PostgreSQL")

        conditions = []
        params = {"limit": limit, "offset": offset}

        if model:
            conditions.append("model = :model")
            params["model"] = model

        if status:
            conditions.append("status = :status")
            params["status"] = status

        if start_time:
            conditions.append("timestamp >= :start_time")
            params["start_time"] = start_time

        if end_time:
            conditions.append("timestamp <= :end_time")
            params["end_time"] = end_time

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = text(
            f"""
            SELECT
                id, request_id, timestamp, model, tokens_generated,
                latency_ms, status, error_message
            FROM request_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
            """
        )

        async with self._session_factory() as session:
            try:
                result = await session.execute(query, params)
                rows = result.fetchall()

                return [
                    {
                        "id": row[0],
                        "request_id": str(row[1]),
                        "timestamp": row[2],
                        "model": row[3],
                        "tokens_generated": row[4],
                        "latency_ms": row[5],
                        "status": row[6],
                        "error_message": row[7],
                    }
                    for row in rows
                ]

            except Exception as e:
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
        if self._session_factory is None:
            raise RuntimeError("Not connected to PostgreSQL")

        # Use time_bucket if TimescaleDB is available, otherwise date_trunc
        if self._pg_config.use_timescale:
            bucket_expr = f"time_bucket('{granularity_minutes} minutes', timestamp)"
        else:
            bucket_expr = "date_trunc('minute', timestamp)"

        query = text(
            f"""
            SELECT
                {bucket_expr} as time_bucket,
                SUM(CASE WHEN metric_name = 'ollama_tokens_generated_total'
                    THEN metric_value ELSE 0 END) as tokens_total,
                AVG(CASE WHEN metric_name = 'ollama_request_latency_ms'
                    THEN metric_value ELSE NULL END) as avg_latency_ms,
                COUNT(CASE WHEN metric_name = 'ollama_requests_total'
                    THEN 1 ELSE NULL END) as request_count
            FROM ollama_metrics
            WHERE timestamp >= NOW() - INTERVAL ':hours hours'
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
            """
        )

        async with self._session_factory() as session:
            try:
                result = await session.execute(query, {"hours": time_range_hours})
                rows = result.fetchall()

                return [
                    {
                        "time_bucket": row[0],
                        "tokens_total": float(row[1]) if row[1] else 0,
                        "avg_latency_ms": float(row[2]) if row[2] else 0,
                        "request_count": int(row[3]) if row[3] else 0,
                    }
                    for row in rows
                ]

            except Exception as e:
                logger.error(f"Failed to get aggregated stats: {e}")
                raise

    async def get_logs_count(
        self,
        model: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """
        Get total count of logs matching filters.

        Args:
            model: Filter by model name.
            status: Filter by status.

        Returns:
            Total count of matching logs.
        """
        if self._session_factory is None:
            raise RuntimeError("Not connected to PostgreSQL")

        conditions = []
        params = {}

        if model:
            conditions.append("model = :model")
            params["model"] = model

        if status:
            conditions.append("status = :status")
            params["status"] = status

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = text(
            f"""
            SELECT COUNT(*) FROM request_logs WHERE {where_clause}
            """
        )

        async with self._session_factory() as session:
            try:
                result = await session.execute(query, params)
                return result.scalar() or 0

            except Exception as e:
                logger.error(f"Failed to get logs count: {e}")
                raise

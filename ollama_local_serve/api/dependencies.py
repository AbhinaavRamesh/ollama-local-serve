"""
Database connection management and dependencies for FastAPI.

Provides unified interface for querying both ClickHouse and PostgreSQL.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration from environment variables."""

    exporter_type: Literal["clickhouse", "postgres", "both"] = "clickhouse"

    # ClickHouse settings
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_database: str = "ollama_metrics"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""

    # PostgreSQL settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "ollama_metrics"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load configuration from environment variables."""
        return cls(
            exporter_type=os.getenv("EXPORTER_TYPE", "clickhouse"),
            clickhouse_host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            clickhouse_port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
            clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "ollama_metrics"),
            clickhouse_user=os.getenv("CLICKHOUSE_USER", "default"),
            clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_database=os.getenv("POSTGRES_DATABASE", "ollama_metrics"),
            postgres_user=os.getenv("POSTGRES_USER", "postgres"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        )


class DatabaseManager:
    """
    Unified database manager supporting both ClickHouse and PostgreSQL.

    Provides a common interface for querying metrics and logs regardless
    of the underlying database.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        """
        Initialize the database manager.

        Args:
            config: Database configuration. Loads from env if None.
        """
        self.config = config or DatabaseConfig.from_env()
        self._clickhouse_client: Optional[Any] = None
        self._postgres_engine: Optional[Any] = None
        self._postgres_session_factory: Optional[Any] = None
        self._connected = False
        self._start_time = datetime.utcnow()

    async def connect(self) -> None:
        """Establish database connections based on configuration."""
        try:
            if self.config.exporter_type in ("clickhouse", "both"):
                await self._connect_clickhouse()

            if self.config.exporter_type in ("postgres", "both"):
                await self._connect_postgres()

            self._connected = True
            logger.info(
                f"Database connections established (type: {self.config.exporter_type})"
            )

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def _connect_clickhouse(self) -> None:
        """Connect to ClickHouse."""
        try:
            from clickhouse_driver import Client as ClickHouseClient

            self._clickhouse_client = ClickHouseClient(
                host=self.config.clickhouse_host,
                port=self.config.clickhouse_port,
                database=self.config.clickhouse_database,
                user=self.config.clickhouse_user,
                password=self.config.clickhouse_password,
            )
            # Test connection
            self._clickhouse_client.execute("SELECT 1")
            logger.info("Connected to ClickHouse")

        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    async def _connect_postgres(self) -> None:
        """Connect to PostgreSQL."""
        try:
            from sqlalchemy.ext.asyncio import (
                create_async_engine,
                AsyncSession,
                async_sessionmaker,
            )

            connection_url = (
                f"postgresql+asyncpg://{self.config.postgres_user}:"
                f"{self.config.postgres_password}@{self.config.postgres_host}:"
                f"{self.config.postgres_port}/{self.config.postgres_database}"
            )

            self._postgres_engine = create_async_engine(
                connection_url, pool_size=5, max_overflow=10
            )
            self._postgres_session_factory = async_sessionmaker(
                self._postgres_engine, class_=AsyncSession, expire_on_commit=False
            )

            # Test connection
            async with self._postgres_engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))

            logger.info("Connected to PostgreSQL")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def disconnect(self) -> None:
        """Close all database connections."""
        if self._clickhouse_client:
            try:
                self._clickhouse_client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from ClickHouse: {e}")
            self._clickhouse_client = None

        if self._postgres_engine:
            try:
                await self._postgres_engine.dispose()
            except Exception as e:
                logger.warning(f"Error disconnecting from PostgreSQL: {e}")
            self._postgres_engine = None
            self._postgres_session_factory = None

        self._connected = False
        logger.info("Database connections closed")

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected

    @property
    def uptime_seconds(self) -> float:
        """Get manager uptime in seconds."""
        return (datetime.utcnow() - self._start_time).total_seconds()

    # ========================================================================
    # Query Methods
    # ========================================================================

    async def get_current_stats(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            return await self._get_current_stats_clickhouse()
        elif self._postgres_session_factory:
            return await self._get_current_stats_postgres()
        else:
            return self._get_empty_stats()

    async def _get_current_stats_clickhouse(self) -> Dict[str, Any]:
        """Get current stats from ClickHouse."""
        try:
            # Get totals
            totals_query = """
                SELECT
                    sum(CASE WHEN metric_name = 'ollama_tokens_generated_total'
                        THEN metric_value ELSE 0 END) as tokens_total,
                    sum(CASE WHEN metric_name = 'ollama_errors_total'
                        THEN metric_value ELSE 0 END) as error_count,
                    count(CASE WHEN metric_name = 'ollama_requests_total'
                        THEN 1 ELSE NULL END) as request_count,
                    avg(CASE WHEN metric_name = 'ollama_request_latency_ms'
                        THEN metric_value ELSE NULL END) as avg_latency_ms
                FROM ollama_metrics
            """
            totals = self._clickhouse_client.execute(totals_query)

            # Get tokens per second (last hour)
            tps_query = """
                SELECT
                    sum(metric_value) / 3600.0 as tokens_per_sec
                FROM ollama_metrics
                WHERE metric_name = 'ollama_tokens_generated_total'
                AND timestamp >= now() - INTERVAL 1 HOUR
            """
            tps = self._clickhouse_client.execute(tps_query)

            # Get uptime
            uptime_query = """
                SELECT max(metric_value) as uptime_hours
                FROM ollama_metrics
                WHERE metric_name = 'ollama_uptime_seconds'
            """
            uptime = self._clickhouse_client.execute(uptime_query)

            return {
                "tokens_total": int(totals[0][0] or 0),
                "tokens_per_sec": float(tps[0][0] or 0),
                "uptime_hours": float((uptime[0][0] or 0) / 3600),
                "error_count": int(totals[0][1] or 0),
                "request_count": int(totals[0][2] or 0),
                "avg_latency_ms": float(totals[0][3] or 0),
                "models_available": 0,  # Would need separate query
                "timestamp": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error getting stats from ClickHouse: {e}")
            return self._get_empty_stats()

    async def _get_current_stats_postgres(self) -> Dict[str, Any]:
        """Get current stats from PostgreSQL."""
        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                # Get totals
                totals_query = text("""
                    SELECT
                        COALESCE(SUM(CASE WHEN metric_name = 'ollama_tokens_generated_total'
                            THEN metric_value ELSE 0 END), 0) as tokens_total,
                        COALESCE(SUM(CASE WHEN metric_name = 'ollama_errors_total'
                            THEN metric_value ELSE 0 END), 0) as error_count,
                        COUNT(CASE WHEN metric_name = 'ollama_requests_total'
                            THEN 1 ELSE NULL END) as request_count,
                        COALESCE(AVG(CASE WHEN metric_name = 'ollama_request_latency_ms'
                            THEN metric_value ELSE NULL END), 0) as avg_latency_ms
                    FROM ollama_metrics
                """)
                result = await session.execute(totals_query)
                totals = result.fetchone()

                # Get tokens per second (last hour)
                tps_query = text("""
                    SELECT
                        COALESCE(SUM(metric_value) / 3600.0, 0) as tokens_per_sec
                    FROM ollama_metrics
                    WHERE metric_name = 'ollama_tokens_generated_total'
                    AND timestamp >= NOW() - INTERVAL '1 hour'
                """)
                result = await session.execute(tps_query)
                tps = result.fetchone()

                return {
                    "tokens_total": int(totals[0] or 0),
                    "tokens_per_sec": float(tps[0] or 0),
                    "uptime_hours": self.uptime_seconds / 3600,
                    "error_count": int(totals[1] or 0),
                    "request_count": int(totals[2] or 0),
                    "avg_latency_ms": float(totals[3] or 0),
                    "models_available": 0,
                    "timestamp": datetime.utcnow(),
                }

        except Exception as e:
            logger.error(f"Error getting stats from PostgreSQL: {e}")
            return self._get_empty_stats()

    def _get_empty_stats(self) -> Dict[str, Any]:
        """Return empty stats when no database is available."""
        return {
            "tokens_total": 0,
            "tokens_per_sec": 0.0,
            "uptime_hours": self.uptime_seconds / 3600,
            "error_count": 0,
            "request_count": 0,
            "avg_latency_ms": 0.0,
            "models_available": 0,
            "timestamp": datetime.utcnow(),
        }

    async def get_history(
        self,
        time_range: str = "1h",
        granularity: str = "1m",
    ) -> List[Dict[str, Any]]:
        """
        Get time-series history data.

        Args:
            time_range: Time range (1h, 6h, 24h)
            granularity: Data granularity (1m, 5m, 1h)
        """
        # Parse time range
        range_map = {"1h": 1, "6h": 6, "24h": 24}
        hours = range_map.get(time_range, 1)

        # Parse granularity
        granularity_map = {"1m": 1, "5m": 5, "1h": 60}
        minutes = granularity_map.get(granularity, 1)

        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            return await self._get_history_clickhouse(hours, minutes)
        elif self._postgres_session_factory:
            return await self._get_history_postgres(hours, minutes)
        else:
            return []

    async def _get_history_clickhouse(
        self, hours: int, granularity_minutes: int
    ) -> List[Dict[str, Any]]:
        """Get history from ClickHouse."""
        try:
            query = f"""
                SELECT
                    toStartOfInterval(timestamp, INTERVAL {granularity_minutes} MINUTE) as time_bucket,
                    sum(CASE WHEN metric_name = 'ollama_tokens_generated_total'
                        THEN metric_value ELSE 0 END) as tokens_total,
                    avg(CASE WHEN metric_name = 'ollama_request_latency_ms'
                        THEN metric_value ELSE NULL END) as latency_ms,
                    count(CASE WHEN metric_name = 'ollama_requests_total'
                        THEN 1 ELSE NULL END) / {granularity_minutes} as throughput,
                    sum(CASE WHEN metric_name = 'ollama_errors_total'
                        THEN metric_value ELSE 0 END) as error_count
                FROM ollama_metrics
                WHERE timestamp >= now() - INTERVAL {hours} HOUR
                GROUP BY time_bucket
                ORDER BY time_bucket DESC
            """
            rows = self._clickhouse_client.execute(query)

            return [
                {
                    "timestamp": row[0],
                    "tokens_total": int(row[1] or 0),
                    "latency_ms": float(row[2] or 0),
                    "throughput": float(row[3] or 0),
                    "error_count": int(row[4] or 0),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting history from ClickHouse: {e}")
            return []

    async def _get_history_postgres(
        self, hours: int, granularity_minutes: int
    ) -> List[Dict[str, Any]]:
        """Get history from PostgreSQL."""
        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                # Use time_bucket if TimescaleDB available, otherwise date_trunc
                query = text(f"""
                    SELECT
                        date_trunc('minute', timestamp) as time_bucket,
                        COALESCE(SUM(CASE WHEN metric_name = 'ollama_tokens_generated_total'
                            THEN metric_value ELSE 0 END), 0) as tokens_total,
                        COALESCE(AVG(CASE WHEN metric_name = 'ollama_request_latency_ms'
                            THEN metric_value ELSE NULL END), 0) as latency_ms,
                        COUNT(CASE WHEN metric_name = 'ollama_requests_total'
                            THEN 1 ELSE NULL END)::float / {granularity_minutes} as throughput,
                        COALESCE(SUM(CASE WHEN metric_name = 'ollama_errors_total'
                            THEN metric_value ELSE 0 END), 0) as error_count
                    FROM ollama_metrics
                    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                    GROUP BY time_bucket
                    ORDER BY time_bucket DESC
                """)
                result = await session.execute(query)
                rows = result.fetchall()

                return [
                    {
                        "timestamp": row[0],
                        "tokens_total": int(row[1] or 0),
                        "latency_ms": float(row[2] or 0),
                        "throughput": float(row[3] or 0),
                        "error_count": int(row[4] or 0),
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Error getting history from PostgreSQL: {e}")
            return []

    async def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get paginated request logs.

        Args:
            limit: Maximum number of logs to return
            offset: Offset for pagination
            status: Filter by status (success/error)
            model: Filter by model name
        """
        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            return await self._get_logs_clickhouse(limit, offset, status, model)
        elif self._postgres_session_factory:
            return await self._get_logs_postgres(limit, offset, status, model)
        else:
            return {"total": 0, "logs": []}

    async def _get_logs_clickhouse(
        self,
        limit: int,
        offset: int,
        status: Optional[str],
        model: Optional[str],
    ) -> Dict[str, Any]:
        """Get logs from ClickHouse."""
        try:
            conditions = []
            params = {}

            if status:
                conditions.append("status = %(status)s")
                params["status"] = status
            if model:
                conditions.append("model = %(model)s")
                params["model"] = model

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Get total count
            count_query = f"SELECT count() FROM request_logs WHERE {where_clause}"
            total = self._clickhouse_client.execute(count_query, params)[0][0]

            # Get logs
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
            rows = self._clickhouse_client.execute(query, params)

            logs = [
                {
                    "request_id": row[0],
                    "timestamp": row[1],
                    "model": row[2],
                    "tokens": row[3],
                    "latency": row[4],
                    "status": row[5],
                    "error_message": row[6],
                }
                for row in rows
            ]

            return {"total": total, "logs": logs}

        except Exception as e:
            logger.error(f"Error getting logs from ClickHouse: {e}")
            return {"total": 0, "logs": []}

    async def _get_logs_postgres(
        self,
        limit: int,
        offset: int,
        status: Optional[str],
        model: Optional[str],
    ) -> Dict[str, Any]:
        """Get logs from PostgreSQL."""
        try:
            from sqlalchemy import text

            conditions = []
            params = {"limit": limit, "offset": offset}

            if status:
                conditions.append("status = :status")
                params["status"] = status
            if model:
                conditions.append("model = :model")
                params["model"] = model

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            async with self._postgres_session_factory() as session:
                # Get total count
                count_query = text(
                    f"SELECT COUNT(*) FROM request_logs WHERE {where_clause}"
                )
                result = await session.execute(count_query, params)
                total = result.scalar() or 0

                # Get logs
                query = text(f"""
                    SELECT
                        request_id::text, timestamp, model, tokens_generated,
                        latency_ms, status, error_message
                    FROM request_logs
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT :limit OFFSET :offset
                """)
                result = await session.execute(query, params)
                rows = result.fetchall()

                logs = [
                    {
                        "request_id": row[0],
                        "timestamp": row[1],
                        "model": row[2],
                        "tokens": row[3],
                        "latency": row[4],
                        "status": row[5],
                        "error_message": row[6],
                    }
                    for row in rows
                ]

                return {"total": total, "logs": logs}

        except Exception as e:
            logger.error(f"Error getting logs from PostgreSQL: {e}")
            return {"total": 0, "logs": []}

    async def get_model_stats(self) -> List[Dict[str, Any]]:
        """Get statistics per model."""
        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            return await self._get_model_stats_clickhouse()
        elif self._postgres_session_factory:
            return await self._get_model_stats_postgres()
        else:
            return []

    async def _get_model_stats_clickhouse(self) -> List[Dict[str, Any]]:
        """Get model stats from ClickHouse."""
        try:
            query = """
                SELECT
                    model,
                    count() as requests_count,
                    sum(tokens_generated) as tokens_generated,
                    avg(latency_ms) as avg_latency_ms,
                    sum(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                    max(timestamp) as last_used
                FROM request_logs
                GROUP BY model
                ORDER BY requests_count DESC
            """
            rows = self._clickhouse_client.execute(query)

            return [
                {
                    "model_name": row[0],
                    "requests_count": row[1],
                    "tokens_generated": row[2],
                    "avg_latency_ms": float(row[3] or 0),
                    "error_count": row[4],
                    "last_used": row[5],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting model stats from ClickHouse: {e}")
            return []

    async def _get_model_stats_postgres(self) -> List[Dict[str, Any]]:
        """Get model stats from PostgreSQL."""
        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                query = text("""
                    SELECT
                        model,
                        COUNT(*) as requests_count,
                        COALESCE(SUM(tokens_generated), 0) as tokens_generated,
                        COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                        MAX(timestamp) as last_used
                    FROM request_logs
                    GROUP BY model
                    ORDER BY requests_count DESC
                """)
                result = await session.execute(query)
                rows = result.fetchall()

                return [
                    {
                        "model_name": row[0],
                        "requests_count": row[1],
                        "tokens_generated": row[2],
                        "avg_latency_ms": float(row[3] or 0),
                        "error_count": row[4],
                        "last_used": row[5],
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Error getting model stats from PostgreSQL: {e}")
            return []


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def init_database() -> DatabaseManager:
    """Initialize the database manager and connect."""
    global _db_manager
    _db_manager = DatabaseManager()
    await _db_manager.connect()
    return _db_manager


async def close_database() -> None:
    """Close database connections."""
    global _db_manager
    if _db_manager is not None:
        await _db_manager.disconnect()
        _db_manager = None

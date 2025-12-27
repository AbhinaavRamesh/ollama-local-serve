"""
Database connection management and dependencies for FastAPI.

Provides unified interface for querying both ClickHouse and PostgreSQL.
"""

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

logger = logging.getLogger(__name__)


def _sanitize_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float, replacing NaN/Inf with default."""
    try:
        f = float(value) if value is not None else default
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


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

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        """
        Initialize the database manager.

        Args:
            config: Database configuration. Loads from env if None.
        """
        self.config = config or DatabaseConfig.from_env()
        self._clickhouse_client: Any | None = None
        self._postgres_engine: Any | None = None
        self._postgres_session_factory: Any | None = None
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
            logger.info(f"Database connections established (type: {self.config.exporter_type})")

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
                AsyncSession,
                async_sessionmaker,
                create_async_engine,
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

    async def get_current_stats(self) -> dict[str, Any]:
        """Get current metrics snapshot."""
        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            return await self._get_current_stats_clickhouse()
        elif self._postgres_session_factory:
            return await self._get_current_stats_postgres()
        else:
            return self._get_empty_stats()

    async def _get_current_stats_clickhouse(self) -> dict[str, Any]:
        """Get current stats from ClickHouse request_logs table."""
        try:
            # Get totals from request_logs
            totals_query = """
                SELECT
                    COALESCE(SUM(tokens_generated), 0) as tokens_total,
                    COUNT(*) as request_count,
                    COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                FROM request_logs
            """
            totals = self._clickhouse_client.execute(totals_query)

            # Get tokens per second (last hour)
            tps_query = """
                SELECT
                    COALESCE(SUM(tokens_generated), 0) / 3600.0 as tokens_per_sec
                FROM request_logs
                WHERE timestamp >= now() - INTERVAL 1 HOUR
            """
            tps = self._clickhouse_client.execute(tps_query)

            # Get model count
            models_query = """
                SELECT COUNT(DISTINCT model) as models_count
                FROM request_logs
            """
            models = self._clickhouse_client.execute(models_query)

            return {
                "tokens_total": int(totals[0][0] or 0),
                "tokens_per_sec": _sanitize_float(tps[0][0]),
                "uptime_hours": _sanitize_float(self.uptime_seconds / 3600),
                "error_count": int(totals[0][3] or 0),
                "request_count": int(totals[0][1] or 0),
                "avg_latency_ms": _sanitize_float(totals[0][2]),
                "models_available": int(models[0][0] or 0),
                "timestamp": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error getting stats from ClickHouse: {e}")
            return self._get_empty_stats()

    async def _get_current_stats_postgres(self) -> dict[str, Any]:
        """Get current stats from PostgreSQL request_logs table."""
        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                # Get totals from request_logs
                totals_query = text(
                    """
                    SELECT
                        COALESCE(SUM(tokens_generated), 0) as tokens_total,
                        COUNT(*) as request_count,
                        COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                    FROM request_logs
                """
                )
                result = await session.execute(totals_query)
                totals = result.fetchone()

                # Get tokens per second (last hour)
                tps_query = text(
                    """
                    SELECT
                        COALESCE(SUM(tokens_generated), 0) / 3600.0 as tokens_per_sec
                    FROM request_logs
                    WHERE timestamp >= NOW() - INTERVAL '1 hour'
                """
                )
                result = await session.execute(tps_query)
                tps = result.fetchone()

                # Get model count
                models_query = text(
                    """
                    SELECT COUNT(DISTINCT model) as models_count
                    FROM request_logs
                """
                )
                result = await session.execute(models_query)
                models = result.fetchone()

                return {
                    "tokens_total": int(totals[0] or 0),
                    "tokens_per_sec": _sanitize_float(tps[0]),
                    "uptime_hours": _sanitize_float(self.uptime_seconds / 3600),
                    "error_count": int(totals[3] or 0),
                    "request_count": int(totals[1] or 0),
                    "avg_latency_ms": _sanitize_float(totals[2]),
                    "models_available": int(models[0] or 0),
                    "timestamp": datetime.utcnow(),
                }

        except Exception as e:
            logger.error(f"Error getting stats from PostgreSQL: {e}")
            return self._get_empty_stats()

    def _get_empty_stats(self) -> dict[str, Any]:
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
    ) -> list[dict[str, Any]]:
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
    ) -> list[dict[str, Any]]:
        """Get history from ClickHouse request_logs table."""
        try:
            query = f"""
                SELECT
                    toStartOfInterval(timestamp, INTERVAL {granularity_minutes} MINUTE) as time_bucket,
                    COALESCE(SUM(tokens_generated), 0) as tokens_total,
                    COALESCE(AVG(latency_ms), 0) as latency_ms,
                    COUNT(*) / {granularity_minutes}.0 as throughput,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                FROM request_logs
                WHERE timestamp >= now() - INTERVAL {hours} HOUR
                GROUP BY time_bucket
                ORDER BY time_bucket ASC
            """
            rows = self._clickhouse_client.execute(query)

            return [
                {
                    "timestamp": row[0],
                    "tokens_total": int(row[1] or 0),
                    "latency_ms": _sanitize_float(row[2]),
                    "throughput": _sanitize_float(row[3]),
                    "error_count": int(row[4] or 0),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting history from ClickHouse: {e}")
            return []

    async def _get_history_postgres(
        self, hours: int, granularity_minutes: int
    ) -> list[dict[str, Any]]:
        """Get history from PostgreSQL request_logs table."""
        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                query = text(
                    f"""
                    SELECT
                        date_trunc('minute', timestamp) as time_bucket,
                        COALESCE(SUM(tokens_generated), 0) as tokens_total,
                        COALESCE(AVG(latency_ms), 0) as latency_ms,
                        COUNT(*)::float / {granularity_minutes} as throughput,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                    FROM request_logs
                    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                    GROUP BY time_bucket
                    ORDER BY time_bucket ASC
                """
                )
                result = await session.execute(query)
                rows = result.fetchall()

                return [
                    {
                        "timestamp": row[0],
                        "tokens_total": int(row[1] or 0),
                        "latency_ms": _sanitize_float(row[2]),
                        "throughput": _sanitize_float(row[3]),
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
        status: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
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
        status: str | None,
        model: str | None,
    ) -> dict[str, Any]:
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
                    latency_ms, status, error_message,
                    prompt_text, response_text, prompt_tokens, total_tokens,
                    client_ip, user_agent, origin, referer
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
                    "prompt_text": row[7] if len(row) > 7 else None,
                    "response_text": row[8] if len(row) > 8 else None,
                    "prompt_tokens": row[9] if len(row) > 9 else None,
                    "total_tokens": row[10] if len(row) > 10 else None,
                    "client_ip": row[11] if len(row) > 11 else None,
                    "user_agent": row[12] if len(row) > 12 else None,
                    "origin": row[13] if len(row) > 13 else None,
                    "referer": row[14] if len(row) > 14 else None,
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
        status: str | None,
        model: str | None,
    ) -> dict[str, Any]:
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
                count_query = text(f"SELECT COUNT(*) FROM request_logs WHERE {where_clause}")
                result = await session.execute(count_query, params)
                total = result.scalar() or 0

                # Get logs
                query = text(
                    f"""
                    SELECT
                        request_id::text, timestamp, model, tokens_generated,
                        latency_ms, status, error_message
                    FROM request_logs
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT :limit OFFSET :offset
                """
                )
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

    # ========================================================================
    # Model Repository Methods (PostgreSQL only)
    # ========================================================================

    async def get_model_repository(
        self,
        category: str | None = None,
        favorites_only: bool = False,
        installed_only: bool = False,
    ) -> dict[str, Any]:
        """Get models from the repository."""
        if not self._postgres_session_factory:
            return {"models": [], "total": 0, "favorites_count": 0, "installed_count": 0}

        try:
            from sqlalchemy import text

            conditions = []
            params = {}

            if category:
                conditions.append("category = :category")
                params["category"] = category
            if favorites_only:
                conditions.append("is_favorite = TRUE")
            if installed_only:
                conditions.append("is_installed = TRUE")

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            async with self._postgres_session_factory() as session:
                # Get models
                query = text(
                    f"""
                    SELECT
                        id, model_name, display_name, description, category,
                        size_label, size_bytes, is_favorite, is_installed, is_default,
                        download_count, usage_count, total_tokens_generated,
                        last_used_at, installed_at, created_at, updated_at
                    FROM model_repository
                    WHERE {where_clause}
                    ORDER BY is_favorite DESC, usage_count DESC, model_name ASC
                """
                )
                result = await session.execute(query, params)
                rows = result.fetchall()

                models = [
                    {
                        "id": row[0],
                        "model_name": row[1],
                        "display_name": row[2],
                        "description": row[3],
                        "category": row[4],
                        "size_label": row[5],
                        "size_bytes": row[6] or 0,
                        "is_favorite": row[7],
                        "is_installed": row[8],
                        "is_default": row[9],
                        "download_count": row[10] or 0,
                        "usage_count": row[11] or 0,
                        "total_tokens_generated": row[12] or 0,
                        "last_used_at": row[13],
                        "installed_at": row[14],
                        "created_at": row[15],
                        "updated_at": row[16],
                    }
                    for row in rows
                ]

                # Get counts
                count_query = text(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN is_favorite THEN 1 ELSE 0 END) as favorites,
                        SUM(CASE WHEN is_installed THEN 1 ELSE 0 END) as installed
                    FROM model_repository
                """
                )
                count_result = await session.execute(count_query)
                counts = count_result.fetchone()

                return {
                    "models": models,
                    "total": counts[0] or 0,
                    "favorites_count": counts[1] or 0,
                    "installed_count": counts[2] or 0,
                }

        except Exception as e:
            logger.error(f"Error getting model repository: {e}")
            return {"models": [], "total": 0, "favorites_count": 0, "installed_count": 0}

    async def get_model_by_name(self, model_name: str) -> dict[str, Any] | None:
        """Get a single model from repository by name."""
        if not self._postgres_session_factory:
            return None

        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                query = text(
                    """
                    SELECT
                        id, model_name, display_name, description, category,
                        size_label, size_bytes, is_favorite, is_installed, is_default,
                        download_count, usage_count, total_tokens_generated,
                        last_used_at, installed_at, created_at, updated_at
                    FROM model_repository
                    WHERE model_name = :model_name
                """
                )
                result = await session.execute(query, {"model_name": model_name})
                row = result.fetchone()

                if not row:
                    return None

                return {
                    "id": row[0],
                    "model_name": row[1],
                    "display_name": row[2],
                    "description": row[3],
                    "category": row[4],
                    "size_label": row[5],
                    "size_bytes": row[6] or 0,
                    "is_favorite": row[7],
                    "is_installed": row[8],
                    "is_default": row[9],
                    "download_count": row[10] or 0,
                    "usage_count": row[11] or 0,
                    "total_tokens_generated": row[12] or 0,
                    "last_used_at": row[13],
                    "installed_at": row[14],
                    "created_at": row[15],
                    "updated_at": row[16],
                }

        except Exception as e:
            logger.error(f"Error getting model by name: {e}")
            return None

    async def create_model_entry(
        self,
        model_name: str,
        display_name: str | None = None,
        description: str | None = None,
        category: str = "general",
        size_label: str | None = None,
    ) -> dict[str, Any] | None:
        """Create a new model entry in the repository."""
        if not self._postgres_session_factory:
            return None

        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                query = text(
                    """
                    INSERT INTO model_repository (model_name, display_name, description, category, size_label)
                    VALUES (:model_name, :display_name, :description, :category, :size_label)
                    ON CONFLICT (model_name) DO UPDATE SET
                        display_name = COALESCE(EXCLUDED.display_name, model_repository.display_name),
                        description = COALESCE(EXCLUDED.description, model_repository.description),
                        category = COALESCE(EXCLUDED.category, model_repository.category),
                        size_label = COALESCE(EXCLUDED.size_label, model_repository.size_label),
                        updated_at = NOW()
                    RETURNING id, model_name, display_name, description, category, size_label,
                              is_favorite, is_installed, is_default, usage_count
                """
                )
                result = await session.execute(
                    query,
                    {
                        "model_name": model_name,
                        "display_name": display_name or model_name,
                        "description": description,
                        "category": category,
                        "size_label": size_label,
                    },
                )
                await session.commit()
                row = result.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "model_name": row[1],
                        "display_name": row[2],
                        "description": row[3],
                        "category": row[4],
                        "size_label": row[5],
                        "is_favorite": row[6],
                        "is_installed": row[7],
                        "is_default": row[8],
                        "usage_count": row[9],
                    }
                return None

        except Exception as e:
            logger.error(f"Error creating model entry: {e}")
            return None

    async def update_model_entry(
        self,
        model_name: str,
        display_name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        is_favorite: bool | None = None,
        is_default: bool | None = None,
        is_installed: bool | None = None,
        size_bytes: int | None = None,
    ) -> dict[str, Any] | None:
        """Update a model entry in the repository."""
        if not self._postgres_session_factory:
            return None

        try:
            from sqlalchemy import text

            updates = ["updated_at = NOW()"]
            params = {"model_name": model_name}

            if display_name is not None:
                updates.append("display_name = :display_name")
                params["display_name"] = display_name
            if description is not None:
                updates.append("description = :description")
                params["description"] = description
            if category is not None:
                updates.append("category = :category")
                params["category"] = category
            if is_favorite is not None:
                updates.append("is_favorite = :is_favorite")
                params["is_favorite"] = is_favorite
            if is_default is not None:
                updates.append("is_default = :is_default")
                params["is_default"] = is_default
                # If setting as default, unset other defaults
                if is_default:
                    async with self._postgres_session_factory() as session:
                        await session.execute(
                            text(
                                "UPDATE model_repository SET is_default = FALSE WHERE model_name != :model_name"
                            ),
                            {"model_name": model_name},
                        )
            if is_installed is not None:
                updates.append("is_installed = :is_installed")
                params["is_installed"] = is_installed
                if is_installed:
                    updates.append("installed_at = NOW()")
            if size_bytes is not None:
                updates.append("size_bytes = :size_bytes")
                params["size_bytes"] = size_bytes

            async with self._postgres_session_factory() as session:
                query = text(
                    f"""
                    UPDATE model_repository
                    SET {', '.join(updates)}
                    WHERE model_name = :model_name
                    RETURNING id, model_name, display_name, description, category,
                              size_label, is_favorite, is_installed, is_default, usage_count
                """
                )
                result = await session.execute(query, params)
                await session.commit()
                row = result.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "model_name": row[1],
                        "display_name": row[2],
                        "description": row[3],
                        "category": row[4],
                        "size_label": row[5],
                        "is_favorite": row[6],
                        "is_installed": row[7],
                        "is_default": row[8],
                        "usage_count": row[9],
                    }
                return None

        except Exception as e:
            logger.error(f"Error updating model entry: {e}")
            return None

    async def delete_model_entry(self, model_name: str) -> bool:
        """Delete a model entry from the repository."""
        if not self._postgres_session_factory:
            return False

        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                query = text("DELETE FROM model_repository WHERE model_name = :model_name")
                await session.execute(query, {"model_name": model_name})
                await session.commit()
                return True

        except Exception as e:
            logger.error(f"Error deleting model entry: {e}")
            return False

    async def sync_installed_models(self, installed_models: list[str]) -> None:
        """Sync the repository with currently installed models."""
        if not self._postgres_session_factory:
            return

        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                # Mark all as not installed first
                await session.execute(text("UPDATE model_repository SET is_installed = FALSE"))

                # Mark installed models
                for model_name in installed_models:
                    await session.execute(
                        text(
                            """
                            INSERT INTO model_repository (model_name, is_installed, installed_at)
                            VALUES (:model_name, TRUE, NOW())
                            ON CONFLICT (model_name) DO UPDATE SET
                                is_installed = TRUE,
                                installed_at = COALESCE(model_repository.installed_at, NOW()),
                                updated_at = NOW()
                        """
                        ),
                        {"model_name": model_name},
                    )

                await session.commit()

        except Exception as e:
            logger.error(f"Error syncing installed models: {e}")

    # ========================================================================
    # Data Management Methods
    # ========================================================================

    async def clear_metrics(self) -> bool:
        """Clear all metrics data from the database."""
        success = True

        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            try:
                self._clickhouse_client.execute("TRUNCATE TABLE IF EXISTS ollama_metrics")
                logger.info("Cleared ClickHouse metrics")
            except Exception as e:
                logger.error(f"Error clearing ClickHouse metrics: {e}")
                success = False

        if self.config.exporter_type in ("postgres", "both") and self._postgres_session_factory:
            try:
                from sqlalchemy import text

                async with self._postgres_session_factory() as session:
                    await session.execute(text("TRUNCATE TABLE ollama_metrics"))
                    await session.commit()
                logger.info("Cleared PostgreSQL metrics")
            except Exception as e:
                logger.error(f"Error clearing PostgreSQL metrics: {e}")
                success = False

        return success

    async def clear_logs(self) -> bool:
        """Clear all request logs from the database."""
        success = True

        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            try:
                self._clickhouse_client.execute("TRUNCATE TABLE IF EXISTS request_logs")
                logger.info("Cleared ClickHouse logs")
            except Exception as e:
                logger.error(f"Error clearing ClickHouse logs: {e}")
                success = False

        if self.config.exporter_type in ("postgres", "both") and self._postgres_session_factory:
            try:
                from sqlalchemy import text

                async with self._postgres_session_factory() as session:
                    await session.execute(text("TRUNCATE TABLE request_logs CASCADE"))
                    await session.commit()
                logger.info("Cleared PostgreSQL logs")
            except Exception as e:
                logger.error(f"Error clearing PostgreSQL logs: {e}")
                success = False

        return success

    async def clear_all_data(self) -> dict[str, bool]:
        """Clear all data from metrics, logs, and reset model stats."""
        results = {
            "metrics_cleared": await self.clear_metrics(),
            "logs_cleared": await self.clear_logs(),
            "model_stats_reset": await self._reset_model_stats(),
        }
        return results

    async def _reset_model_stats(self) -> bool:
        """Reset usage statistics in model repository."""
        if not self._postgres_session_factory:
            return True  # No postgres means nothing to reset

        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                await session.execute(
                    text(
                        """
                    UPDATE model_repository SET
                        usage_count = 0,
                        total_tokens_generated = 0,
                        last_used_at = NULL,
                        updated_at = NOW()
                """
                    )
                )
                await session.commit()
            logger.info("Reset model repository stats")
            return True
        except Exception as e:
            logger.error(f"Error resetting model stats: {e}")
            return False

    async def get_data_summary(self) -> dict[str, Any]:
        """Get summary of data in databases."""
        summary = {
            "metrics_count": 0,
            "logs_count": 0,
            "oldest_metric": None,
            "newest_metric": None,
            "databases": [],
        }

        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            try:
                count = self._clickhouse_client.execute("SELECT count() FROM ollama_metrics")[0][0]
                dates = self._clickhouse_client.execute(
                    "SELECT min(timestamp), max(timestamp) FROM ollama_metrics"
                )[0]
                summary["metrics_count"] += count
                summary["databases"].append("clickhouse")
                if dates[0]:
                    summary["oldest_metric"] = dates[0]
                    summary["newest_metric"] = dates[1]
            except Exception as e:
                logger.error(f"Error getting ClickHouse summary: {e}")

        if self.config.exporter_type in ("postgres", "both") and self._postgres_session_factory:
            try:
                from sqlalchemy import text

                async with self._postgres_session_factory() as session:
                    # Metrics count
                    result = await session.execute(text("SELECT COUNT(*) FROM ollama_metrics"))
                    summary["metrics_count"] += result.scalar() or 0

                    # Logs count
                    result = await session.execute(text("SELECT COUNT(*) FROM request_logs"))
                    summary["logs_count"] = result.scalar() or 0

                    # Date range
                    result = await session.execute(
                        text("SELECT MIN(timestamp), MAX(timestamp) FROM ollama_metrics")
                    )
                    dates = result.fetchone()
                    if dates and dates[0]:
                        if not summary["oldest_metric"] or dates[0] < summary["oldest_metric"]:
                            summary["oldest_metric"] = dates[0]
                        if not summary["newest_metric"] or dates[1] > summary["newest_metric"]:
                            summary["newest_metric"] = dates[1]

                    summary["databases"].append("postgres")
            except Exception as e:
                logger.error(f"Error getting PostgreSQL summary: {e}")

        return summary

    async def get_model_stats(self) -> list[dict[str, Any]]:
        """Get statistics per model."""
        if self.config.exporter_type in ("clickhouse", "both") and self._clickhouse_client:
            return await self._get_model_stats_clickhouse()
        elif self._postgres_session_factory:
            return await self._get_model_stats_postgres()
        else:
            return []

    async def _get_model_stats_clickhouse(self) -> list[dict[str, Any]]:
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
                    "avg_latency_ms": _sanitize_float(row[3]),
                    "error_count": row[4],
                    "last_used": row[5],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting model stats from ClickHouse: {e}")
            return []

    async def _get_model_stats_postgres(self) -> list[dict[str, Any]]:
        """Get model stats from PostgreSQL."""
        try:
            from sqlalchemy import text

            async with self._postgres_session_factory() as session:
                query = text(
                    """
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
                """
                )
                result = await session.execute(query)
                rows = result.fetchall()

                return [
                    {
                        "model_name": row[0],
                        "requests_count": row[1],
                        "tokens_generated": row[2],
                        "avg_latency_ms": _sanitize_float(row[3]),
                        "error_count": row[4],
                        "last_used": row[5],
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Error getting model stats from PostgreSQL: {e}")
            return []


# Global database manager instance
_db_manager: DatabaseManager | None = None


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

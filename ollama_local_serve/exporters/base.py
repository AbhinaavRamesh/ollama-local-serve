"""
Base exporter interface for Ollama metrics.

Provides abstract base class for implementing metrics exporters to various
backends like ClickHouse, PostgreSQL, or other time-series databases.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be exported."""

    REQUEST = "request"
    SYSTEM = "system"
    MODEL = "model"
    ERROR = "error"


@dataclass
class MetricRecord:
    """
    A single metric record for export.

    Attributes:
        timestamp: When the metric was recorded.
        service_name: Name of the service generating the metric.
        metric_type: Type of metric (request, system, model, error).
        metric_name: Name of the specific metric.
        metric_value: Numeric value of the metric.
        metadata: Additional context as key-value pairs.
    """

    timestamp: datetime
    service_name: str
    metric_type: MetricType
    metric_name: str
    metric_value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "service_name": self.service_name,
            "metric_type": self.metric_type.value,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metadata": self.metadata,
        }


@dataclass
class RequestLogRecord:
    """
    A request log record for export.

    Attributes:
        request_id: Unique identifier for the request.
        timestamp: When the request occurred.
        model: Model used for the request.
        tokens_generated: Number of tokens generated.
        latency_ms: Request latency in milliseconds.
        status: Request status (success/error).
        error_message: Error message if status is error.
    """

    request_id: str
    timestamp: datetime
    model: str
    tokens_generated: int
    latency_ms: int
    status: str
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "tokens_generated": self.tokens_generated,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "error_message": self.error_message,
        }


@dataclass
class ExporterConfig:
    """
    Base configuration for exporters.

    Attributes:
        service_name: Name of the service for identification.
        batch_size: Maximum number of records per batch.
        flush_interval_seconds: Interval between batch flushes.
        max_retries: Maximum retry attempts for failed exports.
        retry_delay_seconds: Delay between retry attempts.
        enabled: Whether the exporter is enabled.
    """

    service_name: str = "ollama-local-serve"
    batch_size: int = 100
    flush_interval_seconds: float = 5.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enabled: bool = True


class BaseExporter(ABC):
    """
    Abstract base class for metrics exporters.

    Provides common functionality for batching, retry logic, and lifecycle
    management. Subclasses must implement database-specific methods.

    Example:
        ```python
        class MyExporter(BaseExporter):
            async def _connect(self) -> None:
                # Establish database connection
                pass

            async def _disconnect(self) -> None:
                # Close database connection
                pass

            async def _write_metrics_batch(self, records: List[MetricRecord]) -> None:
                # Write metrics to database
                pass

            async def _write_logs_batch(self, records: List[RequestLogRecord]) -> None:
                # Write logs to database
                pass

            async def _ensure_tables(self) -> None:
                # Create tables if they don't exist
                pass
        ```
    """

    def __init__(self, config: Optional[ExporterConfig] = None) -> None:
        """
        Initialize the exporter.

        Args:
            config: Exporter configuration. Uses defaults if None.
        """
        self.config = config or ExporterConfig()
        self._metrics_buffer: List[MetricRecord] = []
        self._logs_buffer: List[RequestLogRecord] = []
        self._is_connected = False
        self._is_running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        logger.info(f"Exporter initialized with config: {self.config}")

    @abstractmethod
    async def _connect(self) -> None:
        """
        Establish connection to the database.

        Raises:
            ConnectionError: If connection fails.
        """
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    async def _write_metrics_batch(self, records: List[MetricRecord]) -> None:
        """
        Write a batch of metrics to the database.

        Args:
            records: List of metric records to write.

        Raises:
            Exception: If write fails.
        """
        pass

    @abstractmethod
    async def _write_logs_batch(self, records: List[RequestLogRecord]) -> None:
        """
        Write a batch of request logs to the database.

        Args:
            records: List of log records to write.

        Raises:
            Exception: If write fails.
        """
        pass

    @abstractmethod
    async def _ensure_tables(self) -> None:
        """
        Ensure required tables exist in the database.

        Creates tables if they don't exist.

        Raises:
            Exception: If table creation fails.
        """
        pass

    async def start(self) -> None:
        """
        Start the exporter.

        Establishes connection and starts background flush task.
        """
        if not self.config.enabled:
            logger.info("Exporter disabled, skipping start")
            return

        if self._is_running:
            logger.warning("Exporter already running")
            return

        try:
            await self._connect()
            self._is_connected = True

            await self._ensure_tables()

            # Start background flush task
            self._is_running = True
            self._flush_task = asyncio.create_task(self._flush_loop())

            logger.info("Exporter started successfully")

        except Exception as e:
            logger.error(f"Failed to start exporter: {e}")
            await self._cleanup()
            raise

    async def stop(self) -> None:
        """
        Stop the exporter.

        Flushes pending data and closes connection.
        """
        if not self._is_running:
            return

        self._is_running = False

        # Cancel flush task
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Flush remaining data
        await self._flush()

        await self._cleanup()
        logger.info("Exporter stopped")

    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._is_connected:
            try:
                await self._disconnect()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            self._is_connected = False

    async def _flush_loop(self) -> None:
        """Background task for periodic flushing."""
        while self._is_running:
            try:
                await asyncio.sleep(self.config.flush_interval_seconds)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def _flush(self) -> None:
        """Flush buffered data to database."""
        async with self._lock:
            # Flush metrics
            if self._metrics_buffer:
                metrics_to_flush = self._metrics_buffer.copy()
                self._metrics_buffer.clear()
                await self._write_with_retry(
                    self._write_metrics_batch, metrics_to_flush, "metrics"
                )

            # Flush logs
            if self._logs_buffer:
                logs_to_flush = self._logs_buffer.copy()
                self._logs_buffer.clear()
                await self._write_with_retry(
                    self._write_logs_batch, logs_to_flush, "logs"
                )

    async def _write_with_retry(
        self,
        write_func,
        records: List[Any],
        record_type: str,
    ) -> None:
        """
        Write records with retry logic.

        Args:
            write_func: Function to call for writing.
            records: Records to write.
            record_type: Type of records for logging.
        """
        for attempt in range(self.config.max_retries):
            try:
                await write_func(records)
                logger.debug(f"Flushed {len(records)} {record_type} records")
                return
            except Exception as e:
                logger.warning(
                    f"Failed to write {record_type} (attempt {attempt + 1}/"
                    f"{self.config.max_retries}): {e}"
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        logger.error(
            f"Failed to write {len(records)} {record_type} records after "
            f"{self.config.max_retries} attempts"
        )

    async def add_metric(self, record: MetricRecord) -> None:
        """
        Add a metric record to the buffer.

        Args:
            record: Metric record to add.
        """
        if not self._is_running:
            return

        async with self._lock:
            self._metrics_buffer.append(record)

            # Flush if buffer is full
            if len(self._metrics_buffer) >= self.config.batch_size:
                metrics_to_flush = self._metrics_buffer.copy()
                self._metrics_buffer.clear()

        if len(metrics_to_flush) >= self.config.batch_size:
            await self._write_with_retry(
                self._write_metrics_batch, metrics_to_flush, "metrics"
            )

    async def add_log(self, record: RequestLogRecord) -> None:
        """
        Add a request log record to the buffer.

        Args:
            record: Log record to add.
        """
        if not self._is_running:
            return

        async with self._lock:
            self._logs_buffer.append(record)

            # Flush if buffer is full
            if len(self._logs_buffer) >= self.config.batch_size:
                logs_to_flush = self._logs_buffer.copy()
                self._logs_buffer.clear()

        if len(logs_to_flush) >= self.config.batch_size:
            await self._write_with_retry(
                self._write_logs_batch, logs_to_flush, "logs"
            )

    @property
    def is_connected(self) -> bool:
        """Check if exporter is connected to database."""
        return self._is_connected

    @property
    def is_running(self) -> bool:
        """Check if exporter is running."""
        return self._is_running

    async def __aenter__(self) -> "BaseExporter":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

"""
OpenTelemetry metrics provider for Ollama Local Serve.

Provides comprehensive metrics collection for monitoring Ollama service performance,
including request counts, token generation, latency, and error tracking.
"""

import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

logger = logging.getLogger(__name__)


@dataclass
class InstrumentationConfig:
    """
    Configuration for metrics instrumentation.

    Attributes:
        service_name: Name of the service for metrics identification.
        enable_instrumentation: Whether to enable metrics collection.
        export_interval_ms: Interval in milliseconds for metric export.
        enable_console_export: Whether to export metrics to console (for debugging).
    """

    service_name: str = "ollama-local-serve"
    enable_instrumentation: bool = True
    export_interval_ms: int = 5000
    enable_console_export: bool = False


class MetricsProvider:
    """
    OpenTelemetry metrics provider for Ollama service instrumentation.

    Provides counters, histograms, and gauges for tracking service performance.
    All methods are async-ready and thread-safe.

    Example:
        ```python
        from ollama_local_serve.instrumentation import MetricsProvider, InstrumentationConfig

        config = InstrumentationConfig(service_name="my-ollama-service")
        provider = MetricsProvider(config)
        provider.initialize()

        # Record metrics
        provider.record_request(model="llama2", status="success")
        provider.record_tokens_generated(100, model="llama2")
        provider.record_latency(150.5, model="llama2")

        # Use context manager for automatic latency tracking
        async with provider.track_request(model="llama2") as tracker:
            # Your request code here
            tracker.set_tokens(150)
        ```
    """

    def __init__(self, config: InstrumentationConfig | None = None) -> None:
        """
        Initialize the metrics provider.

        Args:
            config: Instrumentation configuration. Uses defaults if None.
        """
        self.config = config or InstrumentationConfig()
        self._meter: metrics.Meter | None = None
        self._meter_provider: MeterProvider | None = None
        self._initialized = False

        # Metric instruments
        self._requests_total: metrics.Counter | None = None
        self._tokens_generated: metrics.Counter | None = None
        self._errors_total: metrics.Counter | None = None
        self._latency_histogram: metrics.Histogram | None = None

        # System metrics
        self._uptime_gauge: metrics.ObservableGauge | None = None
        self._start_time: float = time.time()

        # Callback storage for observable instruments
        self._observable_callbacks: dict[str, Callable] = {}

        logger.info(f"MetricsProvider created with config: {self.config}")

    def initialize(self, custom_exporter: Any | None = None) -> None:
        """
        Initialize the metrics provider and create all instruments.

        Args:
            custom_exporter: Optional custom metric exporter. If None, uses
                           console exporter when enable_console_export is True.

        Raises:
            RuntimeError: If instrumentation is disabled in config.
        """
        if not self.config.enable_instrumentation:
            logger.info("Instrumentation disabled, skipping initialization")
            return

        if self._initialized:
            logger.warning("MetricsProvider already initialized")
            return

        try:
            # Create resource with service name
            resource = Resource.create({SERVICE_NAME: self.config.service_name})

            # Setup metric readers
            readers = []
            if self.config.enable_console_export or custom_exporter is None:
                console_reader = PeriodicExportingMetricReader(
                    ConsoleMetricExporter(),
                    export_interval_millis=self.config.export_interval_ms,
                )
                readers.append(console_reader)

            if custom_exporter is not None:
                custom_reader = PeriodicExportingMetricReader(
                    custom_exporter,
                    export_interval_millis=self.config.export_interval_ms,
                )
                readers.append(custom_reader)

            # Create and set meter provider
            self._meter_provider = MeterProvider(
                resource=resource,
                metric_readers=readers if readers else None,
            )
            metrics.set_meter_provider(self._meter_provider)

            # Get meter
            self._meter = metrics.get_meter(
                name=self.config.service_name,
                version="0.1.0",
            )

            # Create metric instruments
            self._create_instruments()
            self._initialized = True
            logger.info("MetricsProvider initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MetricsProvider: {e}")
            raise

    def _create_instruments(self) -> None:
        """Create all metric instruments."""
        if self._meter is None:
            raise RuntimeError("Meter not initialized")

        # Request counter
        self._requests_total = self._meter.create_counter(
            name="ollama_requests_total",
            description="Total number of requests processed",
            unit="1",
        )

        # Token counter
        self._tokens_generated = self._meter.create_counter(
            name="ollama_tokens_generated_total",
            description="Total number of tokens generated",
            unit="1",
        )

        # Error counter
        self._errors_total = self._meter.create_counter(
            name="ollama_errors_total",
            description="Total number of errors encountered",
            unit="1",
        )

        # Latency histogram
        self._latency_histogram = self._meter.create_histogram(
            name="ollama_request_latency_ms",
            description="Request latency in milliseconds",
            unit="ms",
        )

        # Uptime gauge (observable)
        self._uptime_gauge = self._meter.create_observable_gauge(
            name="ollama_uptime_seconds",
            description="Service uptime in seconds",
            unit="s",
            callbacks=[self._get_uptime_callback()],
        )

        logger.debug("All metric instruments created")

    def _get_uptime_callback(self) -> Callable:
        """Create callback for uptime observable gauge."""

        def callback(options: metrics.CallbackOptions):
            uptime = time.time() - self._start_time
            yield metrics.Observation(uptime)

        return callback

    def record_request(
        self,
        model: str = "unknown",
        status: str = "success",
        attributes: dict[str, str] | None = None,
    ) -> None:
        """
        Record a request.

        Args:
            model: The model used for the request.
            status: Request status ('success' or 'error').
            attributes: Additional attributes to attach to the metric.
        """
        if not self._initialized or self._requests_total is None:
            return

        attrs = {"model": model, "status": status}
        if attributes:
            attrs.update(attributes)

        self._requests_total.add(1, attrs)
        logger.debug(f"Recorded request: model={model}, status={status}")

    def record_tokens_generated(
        self,
        count: int,
        model: str = "unknown",
        attributes: dict[str, str] | None = None,
    ) -> None:
        """
        Record tokens generated.

        Args:
            count: Number of tokens generated.
            model: The model that generated the tokens.
            attributes: Additional attributes to attach to the metric.
        """
        if not self._initialized or self._tokens_generated is None:
            return

        attrs = {"model": model}
        if attributes:
            attrs.update(attributes)

        self._tokens_generated.add(count, attrs)
        logger.debug(f"Recorded tokens: count={count}, model={model}")

    def record_error(
        self,
        error_type: str = "unknown",
        model: str = "unknown",
        attributes: dict[str, str] | None = None,
    ) -> None:
        """
        Record an error.

        Args:
            error_type: Type of error encountered.
            model: The model associated with the error.
            attributes: Additional attributes to attach to the metric.
        """
        if not self._initialized or self._errors_total is None:
            return

        attrs = {"error_type": error_type, "model": model}
        if attributes:
            attrs.update(attributes)

        self._errors_total.add(1, attrs)
        logger.debug(f"Recorded error: type={error_type}, model={model}")

    def record_latency(
        self,
        latency_ms: float,
        model: str = "unknown",
        operation: str = "request",
        attributes: dict[str, str] | None = None,
    ) -> None:
        """
        Record request latency.

        Args:
            latency_ms: Latency in milliseconds.
            model: The model used.
            operation: Type of operation (e.g., 'request', 'health_check').
            attributes: Additional attributes to attach to the metric.
        """
        if not self._initialized or self._latency_histogram is None:
            return

        attrs = {"model": model, "operation": operation}
        if attributes:
            attrs.update(attributes)

        self._latency_histogram.record(latency_ms, attrs)
        logger.debug(f"Recorded latency: {latency_ms}ms, model={model}")

    @asynccontextmanager
    async def track_request(
        self,
        model: str = "unknown",
        operation: str = "request",
    ):
        """
        Async context manager for tracking request metrics.

        Automatically records request count, latency, and handles errors.

        Args:
            model: The model being used.
            operation: Type of operation.

        Yields:
            RequestTracker: Object to set additional metrics like tokens.

        Example:
            async with provider.track_request(model="llama2") as tracker:
                result = await make_request()
                tracker.set_tokens(result.token_count)
        """
        tracker = RequestTracker()
        start_time = time.perf_counter()
        status = "success"

        try:
            yield tracker
        except Exception as e:
            status = "error"
            self.record_error(error_type=type(e).__name__, model=model)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.record_request(model=model, status=status)
            self.record_latency(elapsed_ms, model=model, operation=operation)

            if tracker.tokens is not None:
                self.record_tokens_generated(tracker.tokens, model=model)

    def shutdown(self) -> None:
        """Shutdown the metrics provider and flush any pending metrics."""
        if self._meter_provider is not None:
            try:
                self._meter_provider.shutdown()
                logger.info("MetricsProvider shutdown complete")
            except Exception as e:
                logger.error(f"Error during MetricsProvider shutdown: {e}")
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the metrics provider is initialized."""
        return self._initialized

    def get_meter(self) -> metrics.Meter | None:
        """Get the underlying OTEL meter for custom instrumentation."""
        return self._meter


@dataclass
class RequestTracker:
    """
    Helper class for tracking request-specific metrics.

    Used within the track_request context manager to set additional metrics.
    """

    tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_tokens(self, count: int) -> None:
        """Set the token count for this request."""
        self.tokens = count

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the request tracking."""
        self.metadata[key] = value

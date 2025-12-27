"""
OpenTelemetry tracing setup for Ollama Local Serve.

Provides distributed tracing with automatic span creation for service operations
like start, stop, health checks, and model inference.
"""

import functools
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from typing import Any, ParamSpec, TypeVar

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Span, Status, StatusCode

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class TracingConfig:
    """
    Configuration for distributed tracing.

    Attributes:
        service_name: Name of the service for trace identification.
        enable_tracing: Whether to enable tracing.
        enable_console_export: Whether to export traces to console (for debugging).
        sample_rate: Sampling rate for traces (0.0 to 1.0).
    """

    def __init__(
        self,
        service_name: str = "ollama-local-serve",
        enable_tracing: bool = True,
        enable_console_export: bool = False,
        sample_rate: float = 1.0,
    ) -> None:
        self.service_name = service_name
        self.enable_tracing = enable_tracing
        self.enable_console_export = enable_console_export
        self.sample_rate = sample_rate


class TracerManager:
    """
    OpenTelemetry tracer manager for Ollama service.

    Provides tracing capabilities with automatic span creation for operations.
    Supports both sync and async operations with proper context propagation.

    Example:
        ```python
        from ollama_local_serve.instrumentation import TracerManager, TracingConfig

        config = TracingConfig(service_name="my-ollama-service")
        tracer_mgr = TracerManager(config)
        tracer_mgr.initialize()

        # Use context manager for spans
        async with tracer_mgr.start_span("process_request") as span:
            span.set_attribute("model", "llama2")
            # Your code here

        # Or use decorator
        @tracer_mgr.trace_async("my_operation")
        async def my_function():
            pass
        ```
    """

    def __init__(self, config: TracingConfig | None = None) -> None:
        """
        Initialize the tracer manager.

        Args:
            config: Tracing configuration. Uses defaults if None.
        """
        self.config = config or TracingConfig()
        self._tracer: trace.Tracer | None = None
        self._tracer_provider: TracerProvider | None = None
        self._initialized = False

        logger.info(f"TracerManager created with service: {self.config.service_name}")

    def initialize(self, custom_exporter: Any | None = None) -> None:
        """
        Initialize the tracer provider and create the tracer.

        Args:
            custom_exporter: Optional custom span exporter. If None, uses
                           console exporter when enable_console_export is True.

        Raises:
            RuntimeError: If tracing is disabled in config.
        """
        if not self.config.enable_tracing:
            logger.info("Tracing disabled, skipping initialization")
            return

        if self._initialized:
            logger.warning("TracerManager already initialized")
            return

        try:
            # Create resource with service name
            resource = Resource.create({SERVICE_NAME: self.config.service_name})

            # Create tracer provider
            self._tracer_provider = TracerProvider(resource=resource)

            # Add span processors
            if self.config.enable_console_export:
                console_processor = BatchSpanProcessor(ConsoleSpanExporter())
                self._tracer_provider.add_span_processor(console_processor)

            if custom_exporter is not None:
                custom_processor = BatchSpanProcessor(custom_exporter)
                self._tracer_provider.add_span_processor(custom_processor)

            # Set as global tracer provider
            trace.set_tracer_provider(self._tracer_provider)

            # Get tracer
            self._tracer = trace.get_tracer(
                instrumenting_module_name=self.config.service_name,
                instrumenting_library_version="0.1.0",
            )

            self._initialized = True
            logger.info("TracerManager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize TracerManager: {e}")
            raise

    @asynccontextmanager
    async def start_span_async(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        parent_context: Context | None = None,
    ):
        """
        Start an async span for an operation.

        Args:
            name: Name of the span/operation.
            attributes: Optional attributes to attach to the span.
            parent_context: Optional parent context for trace propagation.

        Yields:
            Span: The active span.

        Example:
            async with tracer_mgr.start_span_async("process_request") as span:
                span.set_attribute("user_id", "123")
                await do_work()
        """
        if not self._initialized or self._tracer is None:
            yield _NoOpSpan()
            return

        with self._tracer.start_as_current_span(
            name,
            context=parent_context,
            attributes=attributes,
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        parent_context: Context | None = None,
    ):
        """
        Start a synchronous span for an operation.

        Args:
            name: Name of the span/operation.
            attributes: Optional attributes to attach to the span.
            parent_context: Optional parent context for trace propagation.

        Yields:
            Span: The active span.
        """
        if not self._initialized or self._tracer is None:
            yield _NoOpSpan()
            return

        with self._tracer.start_as_current_span(
            name,
            context=parent_context,
            attributes=attributes,
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def trace_async(
        self,
        name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Decorator for tracing async functions.

        Args:
            name: Optional span name. Defaults to function name.
            attributes: Optional attributes to attach to the span.

        Returns:
            Decorated function with automatic tracing.

        Example:
            @tracer_mgr.trace_async("fetch_models")
            async def get_models():
                return await api.list_models()
        """

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            span_name = name or func.__name__

            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                async with self.start_span_async(span_name, attributes):
                    return await func(*args, **kwargs)

            return wrapper

        return decorator

    def trace_sync(
        self,
        name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Decorator for tracing synchronous functions.

        Args:
            name: Optional span name. Defaults to function name.
            attributes: Optional attributes to attach to the span.

        Returns:
            Decorated function with automatic tracing.
        """

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            span_name = name or func.__name__

            @functools.wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                with self.start_span(span_name, attributes):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    def get_current_span(self) -> Span:
        """Get the current active span."""
        return trace.get_current_span()

    def get_current_context(self) -> Context:
        """Get the current trace context for propagation."""
        from opentelemetry.context import get_current

        return get_current()

    def inject_context(self, carrier: dict[str, str]) -> None:
        """
        Inject trace context into a carrier for distributed tracing.

        Args:
            carrier: Dictionary to inject context into (e.g., HTTP headers).
        """
        from opentelemetry.propagate import inject

        inject(carrier)

    def extract_context(self, carrier: dict[str, str]) -> Context:
        """
        Extract trace context from a carrier.

        Args:
            carrier: Dictionary containing trace context (e.g., HTTP headers).

        Returns:
            Extracted context.
        """
        from opentelemetry.propagate import extract

        return extract(carrier)

    def shutdown(self) -> None:
        """Shutdown the tracer provider and flush pending spans."""
        if self._tracer_provider is not None:
            try:
                self._tracer_provider.shutdown()
                logger.info("TracerManager shutdown complete")
            except Exception as e:
                logger.error(f"Error during TracerManager shutdown: {e}")
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the tracer is initialized."""
        return self._initialized

    def get_tracer(self) -> trace.Tracer | None:
        """Get the underlying OTEL tracer for custom instrumentation."""
        return self._tracer


class _NoOpSpan:
    """No-operation span for when tracing is disabled."""

    def set_attribute(self, key: str, value: Any) -> None:
        """No-op set attribute."""
        pass

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """No-op set attributes."""
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """No-op add event."""
        pass

    def set_status(self, status: Any) -> None:
        """No-op set status."""
        pass

    def record_exception(self, exception: Exception) -> None:
        """No-op record exception."""
        pass

    def is_recording(self) -> bool:
        """Always returns False."""
        return False

"""
OpenTelemetry instrumentation package for Ollama Local Serve.

This package provides comprehensive observability through metrics collection
and distributed tracing using the OpenTelemetry standard.

Components:
    - MetricsProvider: Collects and exports metrics (requests, tokens, latency, errors)
    - TracerManager: Provides distributed tracing with automatic span creation
    - InstrumentationConfig: Configuration for metrics collection
    - TracingConfig: Configuration for distributed tracing
    - RequestTracker: Helper for tracking request-specific metrics

Example:
    ```python
    from ollama_local_serve.instrumentation import (
        MetricsProvider,
        TracerManager,
        InstrumentationConfig,
        TracingConfig,
    )

    # Initialize metrics
    metrics_config = InstrumentationConfig(service_name="my-service")
    metrics = MetricsProvider(metrics_config)
    metrics.initialize()

    # Initialize tracing
    tracing_config = TracingConfig(service_name="my-service")
    tracer = TracerManager(tracing_config)
    tracer.initialize()

    # Record metrics
    metrics.record_request(model="llama2", status="success")
    metrics.record_tokens_generated(150, model="llama2")

    # Use tracing
    async with tracer.start_span_async("process") as span:
        span.set_attribute("model", "llama2")
        # Your code here
    ```
"""

from ollama_local_serve.instrumentation.metrics_provider import (
    MetricsProvider,
    InstrumentationConfig,
    RequestTracker,
)
from ollama_local_serve.instrumentation.tracer import (
    TracerManager,
    TracingConfig,
)

__all__ = [
    "MetricsProvider",
    "InstrumentationConfig",
    "RequestTracker",
    "TracerManager",
    "TracingConfig",
]

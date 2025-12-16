"""
Ollama service management with async support and metrics instrumentation.
"""

import asyncio
import logging
import subprocess
import signal
import os
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

import aiohttp

from ollama_local_serve.config import NetworkConfig
from ollama_local_serve.exceptions import (
    ServiceStartError,
    ServiceStopError,
    ConnectionError,
    HealthCheckError,
)

logger = logging.getLogger(__name__)

# Lazy imports for instrumentation (only loaded when enabled)
_instrumentation_available = False
try:
    from ollama_local_serve.instrumentation import (
        MetricsProvider,
        InstrumentationConfig,
        TracerManager,
        TracingConfig,
    )
    from ollama_local_serve.exporters import (
        ClickHouseExporter,
        ClickHouseConfig,
        PostgresExporter,
        PostgresConfig,
        MetricRecord,
        RequestLogRecord,
        MetricType,
        BaseExporter,
    )
    _instrumentation_available = True
except ImportError:
    logger.debug("Instrumentation modules not available, metrics disabled")


class OllamaService:
    """
    Service class for managing an Ollama server instance.

    This class provides methods to start, stop, and monitor an Ollama server
    with network accessibility, health checking capabilities, and optional
    metrics instrumentation.

    Example:
        ```python
        import asyncio
        from ollama_local_serve import OllamaService, NetworkConfig

        async def main():
            # Basic usage (no metrics)
            config = NetworkConfig(host="0.0.0.0", port=11434)
            service = OllamaService(config)

            await service.start()
            is_healthy = await service.health_check()
            print(f"Service is healthy: {is_healthy}")
            await service.stop()

        asyncio.run(main())
        ```

    Example with metrics:
        ```python
        import asyncio
        from ollama_local_serve import OllamaService, NetworkConfig

        async def main():
            config = NetworkConfig(
                host="0.0.0.0",
                port=11434,
                enable_instrumentation=True,
                exporter_type="clickhouse",
                clickhouse_host="localhost",
            )
            service = OllamaService(config)

            await service.start()
            # Metrics are now being collected automatically
            await service.stop()

        asyncio.run(main())
        ```
    """

    def __init__(
        self,
        config: Optional[NetworkConfig] = None,
        ollama_binary: str = "ollama",
    ) -> None:
        """
        Initialize the Ollama service.

        Args:
            config: Network configuration for the service. If None, uses default config.
            ollama_binary: Path to the ollama binary. Default is 'ollama' (expects it in PATH).
        """
        self.config = config or NetworkConfig()
        self.ollama_binary = ollama_binary
        self._process: Optional[subprocess.Popen] = None
        self._is_running = False
        self._start_time: Optional[float] = None

        # Instrumentation components (initialized on start if enabled)
        self._metrics_provider: Optional[Any] = None
        self._tracer_manager: Optional[Any] = None
        self._exporters: List[Any] = []
        self._instrumentation_enabled = (
            self.config.enable_instrumentation and _instrumentation_available
        )

        if self.config.enable_instrumentation and not _instrumentation_available:
            logger.warning(
                "Instrumentation requested but modules not available. "
                "Install opentelemetry packages to enable metrics."
            )

        logger.info(f"Initialized OllamaService with config: {self.config}")

    async def _initialize_instrumentation(self) -> None:
        """Initialize metrics and tracing if enabled."""
        if not self._instrumentation_enabled:
            return

        try:
            service_name = f"ollama-{self.config.host}:{self.config.port}"

            # Initialize metrics provider
            metrics_config = InstrumentationConfig(
                service_name=service_name,
                enable_instrumentation=True,
                export_interval_ms=self.config.metrics_export_interval * 1000,
                enable_console_export=False,
            )
            self._metrics_provider = MetricsProvider(metrics_config)
            self._metrics_provider.initialize()

            # Initialize tracer
            tracing_config = TracingConfig(
                service_name=service_name,
                enable_tracing=True,
                enable_console_export=False,
            )
            self._tracer_manager = TracerManager(tracing_config)
            self._tracer_manager.initialize()

            # Initialize exporters based on config
            await self._initialize_exporters()

            logger.info("Instrumentation initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize instrumentation: {e}")
            # Continue without instrumentation
            self._instrumentation_enabled = False

    async def _initialize_exporters(self) -> None:
        """Initialize metric exporters based on configuration."""
        exporter_type = self.config.exporter_type

        if exporter_type in ("clickhouse", "both"):
            try:
                ch_config = ClickHouseConfig(
                    service_name=f"ollama-{self.config.host}:{self.config.port}",
                    host=self.config.clickhouse_host,
                    port=self.config.clickhouse_port,
                    database=self.config.clickhouse_database,
                    flush_interval_seconds=float(self.config.metrics_export_interval),
                )
                exporter = ClickHouseExporter(ch_config)
                await exporter.start()
                self._exporters.append(exporter)
                logger.info("ClickHouse exporter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ClickHouse exporter: {e}")

        if exporter_type in ("postgres", "both"):
            try:
                pg_config = PostgresConfig(
                    service_name=f"ollama-{self.config.host}:{self.config.port}",
                    host=self.config.postgres_host,
                    port=self.config.postgres_port,
                    database=self.config.postgres_database,
                    user=self.config.postgres_user,
                    password=self.config.postgres_password,
                    flush_interval_seconds=float(self.config.metrics_export_interval),
                )
                exporter = PostgresExporter(pg_config)
                await exporter.start()
                self._exporters.append(exporter)
                logger.info("PostgreSQL exporter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL exporter: {e}")

    async def _shutdown_instrumentation(self) -> None:
        """Shutdown instrumentation components gracefully."""
        # Stop exporters
        for exporter in self._exporters:
            try:
                await exporter.stop()
            except Exception as e:
                logger.error(f"Error stopping exporter: {e}")
        self._exporters.clear()

        # Shutdown metrics provider
        if self._metrics_provider is not None:
            try:
                self._metrics_provider.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down metrics provider: {e}")
            self._metrics_provider = None

        # Shutdown tracer
        if self._tracer_manager is not None:
            try:
                self._tracer_manager.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down tracer: {e}")
            self._tracer_manager = None

    def _record_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_type: str = "request",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a metric to all exporters."""
        if not self._instrumentation_enabled or not self._exporters:
            return

        try:
            record = MetricRecord(
                timestamp=datetime.utcnow(),
                service_name=f"ollama-{self.config.host}:{self.config.port}",
                metric_type=MetricType(metric_type),
                metric_name=metric_name,
                metric_value=metric_value,
                metadata=metadata or {},
            )

            for exporter in self._exporters:
                asyncio.create_task(exporter.add_metric(record))

        except Exception as e:
            logger.debug(f"Failed to record metric: {e}")

    def _record_request_log(
        self,
        model: str,
        tokens_generated: int,
        latency_ms: int,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a request log to all exporters."""
        if not self._instrumentation_enabled or not self._exporters:
            return

        try:
            record = RequestLogRecord(
                request_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                model=model,
                tokens_generated=tokens_generated,
                latency_ms=latency_ms,
                status=status,
                error_message=error_message,
            )

            for exporter in self._exporters:
                asyncio.create_task(exporter.add_log(record))

        except Exception as e:
            logger.debug(f"Failed to record request log: {e}")

    async def start(self, startup_delay: float = 2.0) -> None:
        """
        Start the Ollama server instance.

        Args:
            startup_delay: Time in seconds to wait for server startup. Default is 2.0.

        Raises:
            ServiceStartError: If the service fails to start.
            ConnectionError: If unable to verify service is running after startup.
        """
        if self._is_running:
            logger.warning("Service is already running")
            return

        start_time = time.perf_counter()

        try:
            logger.info(
                f"Starting Ollama service on {self.config.host}:{self.config.port}"
            )

            # Initialize instrumentation before starting service
            await self._initialize_instrumentation()

            # Set environment variables for Ollama
            env = os.environ.copy()
            env["OLLAMA_HOST"] = f"{self.config.host}:{self.config.port}"

            # Start the Ollama serve process
            self._process = subprocess.Popen(
                [self.ollama_binary, "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            # Wait for startup
            await asyncio.sleep(startup_delay)

            # Check if process is still running
            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                raise ServiceStartError(
                    f"Ollama process terminated immediately. stderr: {stderr}"
                )

            # Verify service is accessible
            try:
                await self.health_check()
                self._is_running = True
                self._start_time = time.time()
                logger.info("Ollama service started successfully")

                # Record start metric
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if self._metrics_provider:
                    self._metrics_provider.record_request(
                        model="service", status="success"
                    )
                    self._metrics_provider.record_latency(
                        elapsed_ms, model="service", operation="start"
                    )
                self._record_metric(
                    "service_start_latency_ms", elapsed_ms, "system"
                )

            except HealthCheckError as e:
                # Service started but health check failed
                logger.warning(f"Service started but health check failed: {e}")
                self._is_running = True  # Mark as running anyway
                self._start_time = time.time()

        except FileNotFoundError:
            if self._metrics_provider:
                self._metrics_provider.record_error(
                    error_type="FileNotFoundError", model="service"
                )
            self._record_metric("service_errors_total", 1, "error")
            raise ServiceStartError(
                f"Ollama binary not found: {self.ollama_binary}. "
                "Please ensure Ollama is installed and in PATH."
            )
        except Exception as e:
            logger.error(f"Failed to start Ollama service: {e}")
            if self._metrics_provider:
                self._metrics_provider.record_error(
                    error_type=type(e).__name__, model="service"
                )
            self._record_metric("service_errors_total", 1, "error")
            # Clean up if start failed
            if self._process:
                try:
                    self._process.kill()
                except Exception:
                    pass
                self._process = None
            await self._shutdown_instrumentation()
            raise ServiceStartError(f"Failed to start Ollama service: {e}")

    async def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the Ollama server instance.

        Args:
            timeout: Time in seconds to wait for graceful shutdown. Default is 5.0.

        Raises:
            ServiceStopError: If the service fails to stop.
        """
        if not self._is_running or not self._process:
            logger.warning("Service is not running")
            return

        start_time = time.perf_counter()

        try:
            logger.info("Stopping Ollama service")

            # Record uptime before stopping
            if self._start_time:
                uptime_hours = (time.time() - self._start_time) / 3600
                self._record_metric("service_uptime_hours", uptime_hours, "system")

            # Try graceful shutdown first (SIGTERM)
            if os.name != "nt":
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
            else:
                self._process.terminate()

            # Wait for process to exit
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.warning("Graceful shutdown timed out, forcing termination")
                # Force kill if graceful shutdown failed
                if os.name != "nt":
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                else:
                    self._process.kill()
                self._process.wait()

            self._is_running = False
            self._process = None

            # Record stop metric
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if self._metrics_provider:
                self._metrics_provider.record_request(
                    model="service", status="success"
                )
                self._metrics_provider.record_latency(
                    elapsed_ms, model="service", operation="stop"
                )
            self._record_metric("service_stop_latency_ms", elapsed_ms, "system")

            logger.info("Ollama service stopped successfully")

        except Exception as e:
            logger.error(f"Failed to stop Ollama service: {e}")
            if self._metrics_provider:
                self._metrics_provider.record_error(
                    error_type=type(e).__name__, model="service"
                )
            self._record_metric("service_errors_total", 1, "error")
            raise ServiceStopError(f"Failed to stop Ollama service: {e}")
        finally:
            # Always shutdown instrumentation
            await self._shutdown_instrumentation()
            self._start_time = None

    async def health_check(self, retries: Optional[int] = None) -> bool:
        """
        Check if the Ollama service is healthy and responsive.

        Args:
            retries: Number of retry attempts. If None, uses config.max_retries.

        Returns:
            True if service is healthy, False otherwise.

        Raises:
            HealthCheckError: If health check fails after all retries.
            ConnectionError: If unable to connect to the service.
        """
        start_time = time.perf_counter()
        max_retries = retries if retries is not None else self.config.max_retries
        url = f"{self.config.get_connection_url(localhost_fallback=True)}/api/tags"

        for attempt in range(max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            logger.debug("Health check passed")

                            # Record success metric
                            elapsed_ms = (time.perf_counter() - start_time) * 1000
                            if self._metrics_provider:
                                self._metrics_provider.record_request(
                                    model="health_check", status="success"
                                )
                                self._metrics_provider.record_latency(
                                    elapsed_ms, model="health_check", operation="health_check"
                                )
                            self._record_metric(
                                "health_check_latency_ms", elapsed_ms, "system"
                            )

                            return True
                        else:
                            logger.warning(
                                f"Health check returned status {response.status}"
                            )
            except aiohttp.ClientError as e:
                logger.debug(f"Health check attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(1)  # Wait before retry
                else:
                    # Record failure metric
                    if self._metrics_provider:
                        self._metrics_provider.record_error(
                            error_type="ConnectionError", model="health_check"
                        )
                    self._record_metric("health_check_errors_total", 1, "error")
                    raise ConnectionError(
                        f"Failed to connect to Ollama service at {url}: {e}"
                    )
            except Exception as e:
                logger.error(f"Unexpected error during health check: {e}")
                if self._metrics_provider:
                    self._metrics_provider.record_error(
                        error_type=type(e).__name__, model="health_check"
                    )
                self._record_metric("health_check_errors_total", 1, "error")
                raise HealthCheckError(f"Health check failed: {e}")

        if self._metrics_provider:
            self._metrics_provider.record_error(
                error_type="MaxRetriesExceeded", model="health_check"
            )
        self._record_metric("health_check_errors_total", 1, "error")
        raise HealthCheckError(
            f"Health check failed after {max_retries + 1} attempts"
        )

    async def get_models(self) -> Dict[str, Any]:
        """
        Get list of available models from the Ollama service.

        Returns:
            Dictionary containing model information.

        Raises:
            ConnectionError: If unable to connect to the service.
        """
        start_time = time.perf_counter()
        url = f"{self.config.get_connection_url(localhost_fallback=True)}/api/tags"

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Record success metric
                        elapsed_ms = (time.perf_counter() - start_time) * 1000
                        if self._metrics_provider:
                            self._metrics_provider.record_request(
                                model="get_models", status="success"
                            )
                            self._metrics_provider.record_latency(
                                elapsed_ms, model="get_models", operation="get_models"
                            )
                        self._record_metric(
                            "get_models_latency_ms", elapsed_ms, "model"
                        )

                        # Record model count
                        model_count = len(result.get("models", []))
                        self._record_metric(
                            "available_models_count", float(model_count), "model"
                        )

                        return result
                    else:
                        if self._metrics_provider:
                            self._metrics_provider.record_error(
                                error_type="HTTPError", model="get_models"
                            )
                        self._record_metric("get_models_errors_total", 1, "error")
                        raise ConnectionError(
                            f"Failed to get models: HTTP {response.status}"
                        )
        except aiohttp.ClientError as e:
            if self._metrics_provider:
                self._metrics_provider.record_error(
                    error_type="ConnectionError", model="get_models"
                )
            self._record_metric("get_models_errors_total", 1, "error")
            raise ConnectionError(f"Failed to connect to Ollama service: {e}")

    async def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate a response from the Ollama model.

        Args:
            model: Name of the model to use.
            prompt: The prompt to send to the model.
            stream: Whether to stream the response.
            **kwargs: Additional parameters to pass to the API.

        Returns:
            Dictionary containing the response.

        Raises:
            ConnectionError: If unable to connect to the service.
        """
        start_time = time.perf_counter()
        url = f"{self.config.get_connection_url(localhost_fallback=True)}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            **kwargs,
        }

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout * 10)  # Longer timeout for generation
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        elapsed_ms = (time.perf_counter() - start_time) * 1000

                        # Extract token count from response
                        tokens = result.get("eval_count", 0)

                        # Record metrics
                        if self._metrics_provider:
                            self._metrics_provider.record_request(
                                model=model, status="success"
                            )
                            self._metrics_provider.record_tokens_generated(
                                tokens, model=model
                            )
                            self._metrics_provider.record_latency(
                                elapsed_ms, model=model, operation="generate"
                            )

                        # Record to exporters
                        self._record_request_log(
                            model=model,
                            tokens_generated=tokens,
                            latency_ms=int(elapsed_ms),
                            status="success",
                        )
                        self._record_metric(
                            "tokens_generated", float(tokens), "request",
                            {"model": model}
                        )

                        return result
                    else:
                        error_msg = f"Generation failed: HTTP {response.status}"
                        if self._metrics_provider:
                            self._metrics_provider.record_error(
                                error_type="HTTPError", model=model
                            )
                        self._record_request_log(
                            model=model,
                            tokens_generated=0,
                            latency_ms=int((time.perf_counter() - start_time) * 1000),
                            status="error",
                            error_message=error_msg,
                        )
                        raise ConnectionError(error_msg)

        except aiohttp.ClientError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if self._metrics_provider:
                self._metrics_provider.record_error(
                    error_type="ConnectionError", model=model
                )
            self._record_request_log(
                model=model,
                tokens_generated=0,
                latency_ms=int(elapsed_ms),
                status="error",
                error_message=str(e),
            )
            raise ConnectionError(f"Failed to connect to Ollama service: {e}")

    @property
    def is_running(self) -> bool:
        """Check if the service is currently running."""
        return self._is_running

    @property
    def base_url(self) -> str:
        """Get the base URL of the running service."""
        return self.config.get_connection_url(localhost_fallback=True)

    @property
    def uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def metrics_enabled(self) -> bool:
        """Check if metrics instrumentation is enabled."""
        return self._instrumentation_enabled

    @property
    def metrics_provider(self) -> Optional[Any]:
        """Get the metrics provider for custom instrumentation."""
        return self._metrics_provider

    async def __aenter__(self) -> "OllamaService":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

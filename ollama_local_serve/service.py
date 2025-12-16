"""
Ollama service management with async support.
"""

import asyncio
import logging
import subprocess
import signal
import os
from typing import Optional, Dict, Any
import aiohttp

from ollama_local_serve.config import NetworkConfig
from ollama_local_serve.exceptions import (
    ServiceStartError,
    ServiceStopError,
    ConnectionError,
    HealthCheckError,
)

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Service class for managing an Ollama server instance.

    This class provides methods to start, stop, and monitor an Ollama server
    with network accessibility and health checking capabilities.

    Example:
        ```python
        import asyncio
        from ollama_local_serve import OllamaService, NetworkConfig

        async def main():
            config = NetworkConfig(host="0.0.0.0", port=11434)
            service = OllamaService(config)

            await service.start()
            is_healthy = await service.health_check()
            print(f"Service is healthy: {is_healthy}")
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
        logger.info(f"Initialized OllamaService with config: {self.config}")

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

        try:
            logger.info(
                f"Starting Ollama service on {self.config.host}:{self.config.port}"
            )

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
                logger.info("Ollama service started successfully")
            except HealthCheckError as e:
                # Service started but health check failed
                logger.warning(f"Service started but health check failed: {e}")
                self._is_running = True  # Mark as running anyway

        except FileNotFoundError:
            raise ServiceStartError(
                f"Ollama binary not found: {self.ollama_binary}. "
                "Please ensure Ollama is installed and in PATH."
            )
        except Exception as e:
            logger.error(f"Failed to start Ollama service: {e}")
            # Clean up if start failed
            if self._process:
                try:
                    self._process.kill()
                except Exception:
                    pass
                self._process = None
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

        try:
            logger.info("Stopping Ollama service")

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
            logger.info("Ollama service stopped successfully")

        except Exception as e:
            logger.error(f"Failed to stop Ollama service: {e}")
            raise ServiceStopError(f"Failed to stop Ollama service: {e}")

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
        max_retries = retries if retries is not None else self.config.max_retries
        url = f"{self.config.get_connection_url(localhost_fallback=True)}/api/tags"

        for attempt in range(max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            logger.debug("Health check passed")
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
                    raise ConnectionError(
                        f"Failed to connect to Ollama service at {url}: {e}"
                    )
            except Exception as e:
                logger.error(f"Unexpected error during health check: {e}")
                raise HealthCheckError(f"Health check failed: {e}")

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
        url = f"{self.config.get_connection_url(localhost_fallback=True)}/api/tags"

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise ConnectionError(
                            f"Failed to get models: HTTP {response.status}"
                        )
        except aiohttp.ClientError as e:
            raise ConnectionError(f"Failed to connect to Ollama service: {e}")

    @property
    def is_running(self) -> bool:
        """Check if the service is currently running."""
        return self._is_running

    @property
    def base_url(self) -> str:
        """Get the base URL of the running service."""
        return self.config.get_connection_url(localhost_fallback=True)

    async def __aenter__(self) -> "OllamaService":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

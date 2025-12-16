"""
Network configuration for Ollama Local Serve.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NetworkConfig:
    """
    Network configuration for Ollama server.

    Attributes:
        host: The host address to bind to. Use '0.0.0.0' for LAN accessibility.
              Default is 'localhost' for local-only access.
        port: The port number to listen on. Default is 11434 (Ollama default).
        timeout: Connection timeout in seconds. Default is 30.
        max_retries: Maximum number of connection retry attempts. Default is 3.
    """

    host: str = "0.0.0.0"
    port: int = 11434
    timeout: int = 30
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {self.port}")
        if not isinstance(self.timeout, int) or self.timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout}")
        if not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise ValueError(f"Max retries must be non-negative, got {self.max_retries}")

    @property
    def base_url(self) -> str:
        """Get the base URL for the Ollama service."""
        return f"http://{self.host}:{self.port}"

    @property
    def api_url(self) -> str:
        """Get the API URL for the Ollama service."""
        return f"{self.base_url}/api"

    def get_connection_url(self, localhost_fallback: bool = False) -> str:
        """
        Get the connection URL for clients.

        Args:
            localhost_fallback: If True and host is '0.0.0.0', return localhost URL.

        Returns:
            The connection URL string.
        """
        if localhost_fallback and self.host == "0.0.0.0":
            return f"http://localhost:{self.port}"
        return self.base_url

"""
Custom exceptions for Ollama Local Serve.
"""


class OllamaServiceError(Exception):
    """Base exception for all Ollama service related errors."""

    pass


class ConnectionError(OllamaServiceError):
    """Raised when connection to Ollama service fails."""

    pass


class HealthCheckError(OllamaServiceError):
    """Raised when health check fails."""

    pass


class ServiceStartError(OllamaServiceError):
    """Raised when service fails to start."""

    pass


class ServiceStopError(OllamaServiceError):
    """Raised when service fails to stop."""

    pass

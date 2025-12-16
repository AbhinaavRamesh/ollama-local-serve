"""
Ollama Local Serve - Local LLM infrastructure for distributed AI applications.

This module provides a service class for running Ollama on a network-accessible server,
with LangChain integration and production-ready error handling.
"""

from ollama_local_serve.service import OllamaService
from ollama_local_serve.config import NetworkConfig
from ollama_local_serve.client import (
    create_langchain_client,
    create_langchain_chat_client,
)
from ollama_local_serve.exceptions import (
    OllamaServiceError,
    ConnectionError,
    HealthCheckError,
    ServiceStartError,
    ServiceStopError,
)

__version__ = "0.1.0"
__all__ = [
    "OllamaService",
    "NetworkConfig",
    "create_langchain_client",
    "create_langchain_chat_client",
    "OllamaServiceError",
    "ConnectionError",
    "HealthCheckError",
    "ServiceStartError",
    "ServiceStopError",
]

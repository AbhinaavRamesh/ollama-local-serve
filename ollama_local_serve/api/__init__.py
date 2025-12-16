"""
FastAPI monitoring API for Ollama Local Serve.

Provides REST endpoints for querying metrics, logs, and service health.
"""

from ollama_local_serve.api.server import app, create_app

__all__ = ["app", "create_app"]

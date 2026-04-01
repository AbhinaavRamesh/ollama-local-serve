"""
Pydantic models for WebSocket streaming API.

Defines the message protocol for bidirectional WebSocket communication
with the Ollama service.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class WSIncomingMessage(BaseModel):
    """Incoming WebSocket message from client."""

    type: Literal["chat", "ping"]
    model: str | None = None
    messages: list[dict[str, str]] | None = None
    prompt: str | None = None
    stream: bool = True
    options: dict[str, Any] | None = None
    request_id: str | None = None


class WSOutgoingMessage(BaseModel):
    """Outgoing WebSocket message to client."""

    type: Literal["token", "done", "error", "pong", "connected"]
    request_id: str | None = None
    content: str | None = None
    model: str | None = None
    done: bool = False
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    error: str | None = None
    timestamp: str | None = None


class WSConnectionInfo(BaseModel):
    """Information about a single WebSocket connection."""

    connection_id: str
    connected_at: datetime
    messages_sent: int
    messages_received: int
    last_activity: datetime


class WSStatsResponse(BaseModel):
    """Response model for WebSocket connection statistics."""

    active_connections: int
    total_connections_served: int
    total_messages_processed: int
    connections: list[WSConnectionInfo]

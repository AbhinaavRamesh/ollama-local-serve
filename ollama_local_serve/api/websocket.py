"""
WebSocket streaming engine for real-time chat with Ollama.

Provides a connection manager that handles bidirectional WebSocket
communication, streaming tokens from Ollama in real time.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

import httpx
from fastapi import WebSocket

from ollama_local_serve.config import AppConfig

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


@dataclass
class ConnectionState:
    """State for a single WebSocket connection."""

    connection_id: str
    websocket: WebSocket
    connected_at: float
    last_activity: float
    messages_sent: int = 0
    messages_received: int = 0


class ConnectionManager:
    """Manages WebSocket connections and message routing."""

    def __init__(
        self,
        max_connections: int = 100,
        heartbeat_interval: float = 30.0,
        message_max_size: int = 65536,
    ):
        self.max_connections = max_connections
        self.heartbeat_interval = heartbeat_interval
        self.message_max_size = message_max_size
        self._connections: dict[str, ConnectionState] = {}
        self._lock = asyncio.Lock()
        self._total_connections: int = 0
        self._total_messages: int = 0

    async def connect(self, websocket: WebSocket) -> ConnectionState | None:
        """Accept a WebSocket connection and register it.

        Returns the ConnectionState, or None if at capacity.
        """
        async with self._lock:
            if len(self._connections) >= self.max_connections:
                await websocket.accept()
                await websocket.close(code=1013, reason="Maximum connections reached")
                return None

            await websocket.accept()
            connection_id = str(uuid4())
            now = time.time()
            conn = ConnectionState(
                connection_id=connection_id,
                websocket=websocket,
                connected_at=now,
                last_activity=now,
            )
            self._connections[connection_id] = conn
            self._total_connections += 1

        await self.send_message(
            connection_id,
            {"type": "connected", "connection_id": connection_id},
        )
        logger.info("WebSocket connected: %s", connection_id)
        return conn

    async def disconnect(self, connection_id: str) -> None:
        """Remove a connection and close its WebSocket."""
        async with self._lock:
            conn = self._connections.pop(connection_id, None)

        if conn is not None:
            try:
                await conn.websocket.close()
            except Exception:
                pass
            logger.info("WebSocket disconnected: %s", connection_id)

    async def send_message(self, connection_id: str, message_dict: dict) -> None:
        """Send a JSON message to a connection."""
        conn = self._connections.get(connection_id)
        if conn is None:
            return
        try:
            await conn.websocket.send_text(json.dumps(message_dict))
            conn.messages_sent += 1
        except Exception:
            pass

    async def handle_message(self, conn: ConnectionState, data: dict) -> None:
        """Dispatch an incoming message by type."""
        self._total_messages += 1
        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send_message(
                conn.connection_id,
                {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
            )
        elif msg_type == "chat":
            await self._handle_chat(conn, data)
        else:
            await self.send_message(
                conn.connection_id,
                {"type": "error", "error": f"Unknown message type: {msg_type}"},
            )

    async def _handle_chat(self, conn: ConnectionState, data: dict) -> None:
        """Stream a chat or generate response from Ollama."""
        default_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        model = data.get("model") or default_model
        messages = data.get("messages")
        prompt = data.get("prompt")
        options = data.get("options")
        request_id = data.get("request_id") or str(uuid4())

        # Determine endpoint and build request body
        if messages:
            endpoint = f"{OLLAMA_HOST}/api/chat"
            body: dict = {"model": model, "messages": messages, "stream": True}
        elif prompt:
            endpoint = f"{OLLAMA_HOST}/api/generate"
            body = {"model": model, "prompt": prompt, "stream": True}
        else:
            await self.send_message(
                conn.connection_id,
                {
                    "type": "error",
                    "error": "Either 'messages' or 'prompt' is required",
                    "request_id": request_id,
                },
            )
            return

        if options:
            body["options"] = options

        start = time.perf_counter()
        prompt_tokens = None
        completion_tokens = None

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", endpoint, json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)

                        # Extract token content
                        if messages:
                            token = (
                                chunk.get("message", {}).get("content", "")
                                if not chunk.get("done")
                                else ""
                            )
                        else:
                            token = chunk.get("response", "")

                        if token:
                            await self.send_message(
                                conn.connection_id,
                                {
                                    "type": "token",
                                    "content": token,
                                    "request_id": request_id,
                                },
                            )

                        if chunk.get("done"):
                            prompt_tokens = chunk.get("prompt_eval_count")
                            completion_tokens = chunk.get("eval_count")
                            break

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            await self.send_message(
                conn.connection_id,
                {
                    "type": "done",
                    "request_id": request_id,
                    "model": model,
                    "done": True,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency_ms": elapsed_ms,
                },
            )
        except Exception as e:
            logger.error("Chat streaming error: %s", e)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            await self.send_message(
                conn.connection_id,
                {
                    "type": "error",
                    "error": str(e),
                    "request_id": request_id,
                    "latency_ms": elapsed_ms,
                },
            )

    async def _heartbeat_loop(self, connection_id: str) -> None:
        """Periodically send a ping to keep the connection alive."""
        while connection_id in self._connections:
            await asyncio.sleep(self.heartbeat_interval)
            if connection_id not in self._connections:
                break
            try:
                conn = self._connections[connection_id]
                await conn.websocket.send_text(
                    json.dumps(
                        {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                    )
                )
            except Exception:
                await self.disconnect(connection_id)
                break

    def get_stats(self) -> dict:
        """Return current connection statistics."""
        connections = []
        for conn in self._connections.values():
            connections.append(
                {
                    "connection_id": conn.connection_id,
                    "connected_at": datetime.utcfromtimestamp(conn.connected_at).isoformat(),
                    "messages_sent": conn.messages_sent,
                    "messages_received": conn.messages_received,
                    "last_activity": datetime.utcfromtimestamp(conn.last_activity).isoformat(),
                }
            )
        return {
            "active_connections": len(self._connections),
            "total_connections_served": self._total_connections,
            "total_messages_processed": self._total_messages,
            "connections": connections,
        }


# Module-level singleton
_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the singleton ConnectionManager."""
    global _manager
    if _manager is None:
        config = AppConfig().websocket
        _manager = ConnectionManager(
            max_connections=config.max_connections,
            heartbeat_interval=config.heartbeat_interval,
            message_max_size=config.message_max_size,
        )
    return _manager

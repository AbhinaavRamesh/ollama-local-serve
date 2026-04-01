"""
Conversation Memory & Session Management.

Manages in-memory conversation sessions with configurable context strategies
(sliding_window, full) and automatic TTL-based cleanup.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ollama_local_serve.config import AppConfig

logger = logging.getLogger(__name__)


# ============================================================================
# Internal dataclasses
# ============================================================================


@dataclass
class Message:
    """A single message in a conversation."""

    role: str
    content: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class Session:
    """A conversation session holding messages and metadata."""

    id: str
    model: str
    system_prompt: str | None = None
    context_strategy: str = "sliding_window"
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_active: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    ttl_seconds: int = 3600

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.last_active).total_seconds()
        return elapsed > self.ttl_seconds

    def touch(self) -> None:
        """Update last_active timestamp."""
        self.last_active = datetime.now(timezone.utc)


# ============================================================================
# ConversationManager
# ============================================================================


class ConversationManager:
    """
    Manages conversation sessions with context building and TTL cleanup.

    Stores sessions in memory. Provides sliding_window and full context
    strategies for building message history to send to Ollama.
    """

    def __init__(
        self,
        max_sessions: int = 100,
        default_ttl_seconds: int = 3600,
        max_messages_per_session: int = 200,
        default_context_strategy: str = "sliding_window",
        context_window_size: int = 20,
    ) -> None:
        self._sessions: dict[str, Session] = {}
        self._max_sessions = max_sessions
        self._default_ttl_seconds = default_ttl_seconds
        self._max_messages_per_session = max_messages_per_session
        self._default_context_strategy = default_context_strategy
        self._context_window_size = context_window_size
        self._cleanup_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    async def create_session(
        self,
        model: str,
        system_prompt: str | None = None,
        context_strategy: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Session:
        """Create a new conversation session."""
        if len(self._sessions) >= self._max_sessions:
            # Evict the oldest inactive session
            oldest = min(
                self._sessions.values(), key=lambda s: s.last_active
            )
            logger.info(f"Evicting oldest session {oldest.id} to make room")
            del self._sessions[oldest.id]

        session = Session(
            id=str(uuid.uuid4()),
            model=model,
            system_prompt=system_prompt,
            context_strategy=context_strategy or self._default_context_strategy,
            ttl_seconds=ttl_seconds or self._default_ttl_seconds,
        )
        self._sessions[session.id] = session
        logger.info(f"Created session {session.id} with model={model}")
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID, returning None if not found or expired."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired:
            logger.info(f"Session {session_id} has expired, removing")
            del self._sessions[session_id]
            return None
        return session

    async def list_sessions(self) -> list[Session]:
        """List all active (non-expired) sessions."""
        expired = [
            sid for sid, s in self._sessions.items() if s.is_expired
        ]
        for sid in expired:
            del self._sessions[sid]
        return list(self._sessions.values())

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID. Returns True if it existed."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        return False

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def add_message(
        self, session_id: str, role: str, content: str
    ) -> Message | None:
        """Add a message to a session. Returns the message or None if session not found."""
        session = await self.get_session(session_id)
        if session is None:
            return None

        message = Message(role=role, content=content)
        session.messages.append(message)
        session.touch()

        # Trim oldest messages if over limit (keep system-relevant ones)
        if len(session.messages) > self._max_messages_per_session:
            excess = len(session.messages) - self._max_messages_per_session
            session.messages = session.messages[excess:]

        return message

    async def get_messages(self, session_id: str) -> list[Message] | None:
        """Get all messages for a session. Returns None if session not found."""
        session = await self.get_session(session_id)
        if session is None:
            return None
        return list(session.messages)

    # ------------------------------------------------------------------
    # Context Building
    # ------------------------------------------------------------------

    def build_context(self, session: Session) -> list[dict[str, str]]:
        """
        Build the messages array to send to Ollama based on the session's
        context strategy.

        Args:
            session: The conversation session.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        messages: list[dict[str, str]] = []

        # Always include system prompt first if present
        if session.system_prompt:
            messages.append(
                {"role": "system", "content": session.system_prompt}
            )

        if session.context_strategy == "sliding_window":
            # Take the last N messages
            window = session.messages[-self._context_window_size :]
            for msg in window:
                messages.append({"role": msg.role, "content": msg.content})
        else:
            # "full" strategy: include all messages
            for msg in session.messages:
                messages.append({"role": msg.role, "content": msg.content})

        return messages

    # ------------------------------------------------------------------
    # TTL Cleanup
    # ------------------------------------------------------------------

    async def start_cleanup(self, interval: int = 60) -> None:
        """Start the background TTL cleanup loop."""
        if self._cleanup_task is not None:
            return

        async def _cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    expired = [
                        sid
                        for sid, s in self._sessions.items()
                        if s.is_expired
                    ]
                    for sid in expired:
                        del self._sessions[sid]
                    if expired:
                        logger.info(
                            f"TTL cleanup removed {len(expired)} expired sessions"
                        )
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in TTL cleanup loop: {e}")

        self._cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info("Conversation TTL cleanup loop started")

    async def stop_cleanup(self) -> None:
        """Stop the background TTL cleanup loop."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Conversation TTL cleanup loop stopped")


# ============================================================================
# Module-level singleton
# ============================================================================

_conversation_manager: ConversationManager | None = None


def get_conversation_manager() -> ConversationManager:
    """Get or create the global ConversationManager instance."""
    global _conversation_manager
    if _conversation_manager is None:
        config = AppConfig()
        conv_config = config.conversation
        _conversation_manager = ConversationManager(
            max_sessions=conv_config.max_sessions,
            default_ttl_seconds=conv_config.default_ttl_seconds,
            max_messages_per_session=conv_config.max_messages_per_session,
            default_context_strategy=conv_config.default_context_strategy,
            context_window_size=conv_config.context_window_size,
        )
    return _conversation_manager

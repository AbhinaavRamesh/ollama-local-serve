"""
Pydantic models for conversation session API request/response schemas.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ============================================================================
# Shared Models
# ============================================================================


class MessageModel(BaseModel):
    """A single message in a conversation."""

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="The role of the message sender"
    )
    content: str = Field(..., min_length=1, description="The message content")
    timestamp: datetime | None = Field(
        None, description="When the message was created"
    )


# ============================================================================
# Request Models
# ============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create a new conversation session."""

    model: str = Field(
        ..., min_length=1, description="Ollama model name to use for this session"
    )
    system_prompt: str | None = Field(
        None, description="Optional system prompt to set context"
    )
    context_strategy: Literal["sliding_window", "full"] = Field(
        default="sliding_window",
        description="Strategy for building context from history",
    )
    ttl_seconds: int | None = Field(
        None,
        ge=60,
        description="Session time-to-live in seconds (None uses server default)",
    )


class SessionChatRequest(BaseModel):
    """Request to send a message in a session and get a response."""

    content: str = Field(
        ..., min_length=1, description="The user message content"
    )
    stream: bool = Field(
        default=False, description="Whether to stream the response"
    )


# ============================================================================
# Response Models
# ============================================================================


class SessionResponse(BaseModel):
    """Response representing a conversation session."""

    session_id: str = Field(..., description="Unique session identifier")
    model: str = Field(..., description="Model used for this session")
    system_prompt: str | None = Field(
        None, description="System prompt for the session"
    )
    context_strategy: str = Field(
        ..., description="Context strategy (sliding_window or full)"
    )
    message_count: int = Field(
        ..., description="Number of messages in the session"
    )
    created_at: datetime = Field(..., description="When the session was created")
    last_active: datetime = Field(
        ..., description="When the session was last active"
    )
    ttl_seconds: int = Field(..., description="Session time-to-live in seconds")


class SessionListResponse(BaseModel):
    """Response containing a list of sessions."""

    sessions: list[SessionResponse] = Field(
        default_factory=list, description="List of active sessions"
    )
    total_count: int = Field(..., description="Total number of active sessions")


class SessionMessagesResponse(BaseModel):
    """Response containing messages from a session."""

    session_id: str = Field(..., description="Session identifier")
    messages: list[MessageModel] = Field(
        default_factory=list, description="Messages in the session"
    )
    total_count: int = Field(
        ..., description="Total number of messages in the session"
    )

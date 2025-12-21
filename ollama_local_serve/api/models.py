"""
Pydantic models for API request/response schemas.
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Health Check Models
# ============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Service health status"
    )
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    database_connected: bool = Field(..., description="Database connection status")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional health details"
    )


# ============================================================================
# Current Stats Models
# ============================================================================


class CurrentStatsResponse(BaseModel):
    """Current metrics snapshot."""

    tokens_total: int = Field(..., description="Total tokens generated all-time")
    tokens_per_sec: float = Field(
        ..., description="Average tokens per second (last hour)"
    )
    uptime_hours: float = Field(..., description="Service uptime in hours")
    error_count: int = Field(..., description="Total error count")
    request_count: int = Field(..., description="Total request count")
    avg_latency_ms: float = Field(..., description="Average latency in milliseconds")
    models_available: int = Field(..., description="Number of available models")
    timestamp: datetime = Field(..., description="Timestamp of the stats")


# ============================================================================
# History Models
# ============================================================================


class HistoryDataPoint(BaseModel):
    """Single data point in time-series history."""

    timestamp: datetime = Field(..., description="Time bucket timestamp")
    tokens_total: int = Field(..., description="Total tokens in this bucket")
    latency_ms: float = Field(..., description="Average latency in milliseconds")
    throughput: float = Field(..., description="Requests per minute")
    error_count: int = Field(0, description="Errors in this bucket")


class HistoryResponse(BaseModel):
    """Time-series history response."""

    time_range: str = Field(..., description="Time range (1h, 6h, 24h)")
    granularity: str = Field(..., description="Data granularity (1m, 5m, 1h)")
    data: List[HistoryDataPoint] = Field(..., description="Time-series data points")


# ============================================================================
# Request Logs Models
# ============================================================================


class RequestLogEntry(BaseModel):
    """Single request log entry."""

    id: Optional[str] = Field(None, description="Log entry ID")
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(..., description="Request timestamp")
    model: str = Field(..., description="Model used")
    prompt_text: Optional[str] = Field(None, description="Input prompt text")
    response_text: Optional[str] = Field(None, description="Output response text")
    prompt_tokens: Optional[int] = Field(None, description="Prompt token count")
    tokens: int = Field(..., description="Tokens generated")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    latency: int = Field(..., description="Latency in milliseconds")
    status: Literal["success", "error"] = Field(..., description="Request status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    origin: Optional[str] = Field(None, description="Request origin")
    referer: Optional[str] = Field(None, description="Request referer")


# ============================================================================
# Chat Models
# ============================================================================


class ChatRequest(BaseModel):
    """Chat request model."""

    prompt: str = Field(..., description="User prompt")
    model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2"),
        description="Model to use"
    )
    system: Optional[str] = Field(None, description="System prompt")
    temperature: Optional[float] = Field(0.7, description="Temperature for generation")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")


class ChatResponse(BaseModel):
    """Chat response model (non-streaming)."""

    request_id: str = Field(..., description="Unique request identifier")
    model: str = Field(..., description="Model used")
    response: str = Field(..., description="Generated response")
    prompt_tokens: int = Field(..., description="Prompt token count")
    completion_tokens: int = Field(..., description="Completion token count")
    total_tokens: int = Field(..., description="Total token count")
    latency_ms: int = Field(..., description="Latency in milliseconds")


class LogsResponse(BaseModel):
    """Paginated request logs response."""

    total: int = Field(..., description="Total number of logs")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Page size limit")
    logs: List[RequestLogEntry] = Field(..., description="Log entries")


# ============================================================================
# Model Stats Models
# ============================================================================


class ModelStats(BaseModel):
    """Statistics for a single model."""

    model_name: str = Field(..., description="Model name")
    requests_count: int = Field(..., description="Total requests for this model")
    tokens_generated: int = Field(..., description="Total tokens generated")
    avg_latency_ms: float = Field(..., description="Average latency in milliseconds")
    error_count: int = Field(0, description="Error count for this model")
    last_used: Optional[datetime] = Field(None, description="Last request timestamp")


class ModelsResponse(BaseModel):
    """Model statistics response."""

    models: List[ModelStats] = Field(..., description="List of model statistics")
    total_models: int = Field(..., description="Total number of models")


# ============================================================================
# Configuration Models
# ============================================================================


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration."""

    enable_instrumentation: Optional[bool] = Field(
        None, description="Enable/disable instrumentation"
    )
    metrics_export_interval: Optional[int] = Field(
        None, description="Metrics export interval in seconds"
    )
    exporter_type: Optional[Literal["clickhouse", "postgres", "both", "none"]] = Field(
        None, description="Exporter type to use"
    )


class ConfigResponse(BaseModel):
    """Current configuration response."""

    enable_instrumentation: bool = Field(
        ..., description="Whether instrumentation is enabled"
    )
    exporter_type: str = Field(..., description="Current exporter type")
    metrics_export_interval: int = Field(
        ..., description="Metrics export interval in seconds"
    )
    clickhouse_host: Optional[str] = Field(None, description="ClickHouse host")
    postgres_host: Optional[str] = Field(None, description="PostgreSQL host")


# ============================================================================
# Model Repository Models
# ============================================================================


class ModelRepositoryEntry(BaseModel):
    """Model repository entry."""

    id: Optional[int] = Field(None, description="Model ID")
    model_name: str = Field(..., description="Model name (e.g., llama3.2)")
    display_name: Optional[str] = Field(None, description="Display name")
    description: Optional[str] = Field(None, description="Model description")
    category: str = Field("general", description="Model category (general, coding, chat)")
    size_label: Optional[str] = Field(None, description="Size label (e.g., 7B)")
    size_bytes: int = Field(0, description="Size in bytes")
    is_favorite: bool = Field(False, description="Is favorite model")
    is_installed: bool = Field(False, description="Is installed locally")
    is_default: bool = Field(False, description="Is default model")
    download_count: int = Field(0, description="Number of times downloaded")
    usage_count: int = Field(0, description="Number of times used")
    total_tokens_generated: int = Field(0, description="Total tokens generated")
    last_used_at: Optional[datetime] = Field(None, description="Last used timestamp")
    installed_at: Optional[datetime] = Field(None, description="Installation timestamp")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class ModelRepositoryResponse(BaseModel):
    """Model repository list response."""

    models: List[ModelRepositoryEntry] = Field(..., description="List of models")
    total: int = Field(..., description="Total count")
    favorites_count: int = Field(0, description="Number of favorites")
    installed_count: int = Field(0, description="Number of installed models")


class ModelRepositoryUpdate(BaseModel):
    """Model repository update request."""

    display_name: Optional[str] = Field(None, description="Display name")
    description: Optional[str] = Field(None, description="Description")
    category: Optional[str] = Field(None, description="Category")
    is_favorite: Optional[bool] = Field(None, description="Is favorite")
    is_default: Optional[bool] = Field(None, description="Is default")


class ModelRepositoryCreate(BaseModel):
    """Model repository create request."""

    model_name: str = Field(..., description="Model name")
    display_name: Optional[str] = Field(None, description="Display name")
    description: Optional[str] = Field(None, description="Description")
    category: str = Field("general", description="Category")
    size_label: Optional[str] = Field(None, description="Size label")


# ============================================================================
# Error Models
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

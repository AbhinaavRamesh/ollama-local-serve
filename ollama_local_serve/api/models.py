"""
Pydantic models for API request/response schemas.
"""

import os
from datetime import datetime
from typing import Any, Literal

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
    details: dict[str, Any] | None = Field(None, description="Additional health details")


# ============================================================================
# Current Stats Models
# ============================================================================


class CurrentStatsResponse(BaseModel):
    """Current metrics snapshot."""

    tokens_total: int = Field(..., description="Total tokens generated all-time")
    tokens_per_sec: float = Field(..., description="Average tokens per second (last hour)")
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
    data: list[HistoryDataPoint] = Field(..., description="Time-series data points")


# ============================================================================
# Request Logs Models
# ============================================================================


class RequestLogEntry(BaseModel):
    """Single request log entry."""

    id: str | None = Field(None, description="Log entry ID")
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(..., description="Request timestamp")
    model: str = Field(..., description="Model used")
    prompt_text: str | None = Field(None, description="Input prompt text")
    response_text: str | None = Field(None, description="Output response text")
    prompt_tokens: int | None = Field(None, description="Prompt token count")
    tokens: int = Field(..., description="Tokens generated")
    total_tokens: int | None = Field(None, description="Total tokens used")
    latency: int = Field(..., description="Latency in milliseconds")
    status: Literal["success", "error"] = Field(..., description="Request status")
    error_message: str | None = Field(None, description="Error message if failed")
    client_ip: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client user agent")
    origin: str | None = Field(None, description="Request origin")
    referer: str | None = Field(None, description="Request referer")


# ============================================================================
# Chat Models
# ============================================================================


class ChatRequest(BaseModel):
    """Chat request model."""

    prompt: str = Field(..., description="User prompt")
    model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2"), description="Model to use"
    )
    system: str | None = Field(None, description="System prompt")
    temperature: float | None = Field(0.7, description="Temperature for generation")
    max_tokens: int | None = Field(None, description="Maximum tokens to generate")


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
    logs: list[RequestLogEntry] = Field(..., description="Log entries")


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
    last_used: datetime | None = Field(None, description="Last request timestamp")


class ModelsResponse(BaseModel):
    """Model statistics response."""

    models: list[ModelStats] = Field(..., description="List of model statistics")
    total_models: int = Field(..., description="Total number of models")


# ============================================================================
# Configuration Models
# ============================================================================


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration."""

    enable_instrumentation: bool | None = Field(
        None, description="Enable/disable instrumentation"
    )
    metrics_export_interval: int | None = Field(
        None, description="Metrics export interval in seconds"
    )
    exporter_type: Literal["clickhouse", "postgres", "both", "none"] | None = Field(
        None, description="Exporter type to use"
    )


class ConfigResponse(BaseModel):
    """Current configuration response."""

    enable_instrumentation: bool = Field(..., description="Whether instrumentation is enabled")
    exporter_type: str = Field(..., description="Current exporter type")
    metrics_export_interval: int = Field(..., description="Metrics export interval in seconds")
    clickhouse_host: str | None = Field(None, description="ClickHouse host")
    postgres_host: str | None = Field(None, description="PostgreSQL host")


# ============================================================================
# Model Repository Models
# ============================================================================


class ModelRepositoryEntry(BaseModel):
    """Model repository entry."""

    id: int | None = Field(None, description="Model ID")
    model_name: str = Field(..., description="Model name (e.g., llama3.2)")
    display_name: str | None = Field(None, description="Display name")
    description: str | None = Field(None, description="Model description")
    category: str = Field("general", description="Model category (general, coding, chat)")
    size_label: str | None = Field(None, description="Size label (e.g., 7B)")
    size_bytes: int = Field(0, description="Size in bytes")
    is_favorite: bool = Field(False, description="Is favorite model")
    is_installed: bool = Field(False, description="Is installed locally")
    is_default: bool = Field(False, description="Is default model")
    download_count: int = Field(0, description="Number of times downloaded")
    usage_count: int = Field(0, description="Number of times used")
    total_tokens_generated: int = Field(0, description="Total tokens generated")
    last_used_at: datetime | None = Field(None, description="Last used timestamp")
    installed_at: datetime | None = Field(None, description="Installation timestamp")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")


class ModelRepositoryResponse(BaseModel):
    """Model repository list response."""

    models: list[ModelRepositoryEntry] = Field(..., description="List of models")
    total: int = Field(..., description="Total count")
    favorites_count: int = Field(0, description="Number of favorites")
    installed_count: int = Field(0, description="Number of installed models")


class ModelRepositoryUpdate(BaseModel):
    """Model repository update request."""

    display_name: str | None = Field(None, description="Display name")
    description: str | None = Field(None, description="Description")
    category: str | None = Field(None, description="Category")
    is_favorite: bool | None = Field(None, description="Is favorite")
    is_default: bool | None = Field(None, description="Is default")


class ModelRepositoryCreate(BaseModel):
    """Model repository create request."""

    model_name: str = Field(..., description="Model name")
    display_name: str | None = Field(None, description="Display name")
    description: str | None = Field(None, description="Description")
    category: str = Field("general", description="Category")
    size_label: str | None = Field(None, description="Size label")


# ============================================================================
# Error Models
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional details")


# ============================================================================
# GPU Monitoring Models
# ============================================================================


class GPUInfoResponse(BaseModel):
    """Single GPU information."""

    index: int = Field(..., description="GPU index")
    name: str = Field(..., description="GPU name")
    driver_version: str = Field(..., description="Driver version")
    cuda_version: str = Field(..., description="CUDA version")
    memory_total_mb: int = Field(..., description="Total memory in MB")
    memory_used_mb: int = Field(..., description="Used memory in MB")
    memory_free_mb: int = Field(..., description="Free memory in MB")
    memory_utilization_percent: float = Field(..., description="Memory utilization %")
    utilization_gpu_percent: int = Field(..., description="GPU utilization %")
    utilization_memory_percent: int = Field(..., description="Memory utilization %")
    temperature_celsius: int = Field(..., description="Temperature in Celsius")
    power_draw_watts: float = Field(..., description="Power draw in watts")
    power_limit_watts: float = Field(..., description="Power limit in watts")
    vram_used_gb: float = Field(..., description="VRAM used in GB")
    vram_total_gb: float = Field(..., description="VRAM total in GB")


class GPUMetricsResponse(BaseModel):
    """GPU metrics response."""

    available: bool = Field(..., description="Whether GPU is available")
    gpu_count: int = Field(..., description="Number of GPUs")
    timestamp: str = Field(..., description="Timestamp of measurement")
    error: str | None = Field(None, description="Error message if any")
    total_vram_gb: float = Field(0, description="Total VRAM across GPUs in GB")
    used_vram_gb: float = Field(0, description="Used VRAM across GPUs in GB")
    avg_gpu_utilization_percent: float = Field(0, description="Avg GPU utilization")
    avg_memory_utilization_percent: float = Field(0, description="Avg memory utilization")
    avg_temperature_celsius: float = Field(0, description="Avg temperature")
    gpus: list[GPUInfoResponse] = Field(default_factory=list, description="Per-GPU details")


class SystemMetricsResponse(BaseModel):
    """System CPU and RAM metrics response."""

    available: bool = Field(..., description="Whether system metrics are available")
    cpu_percent: float = Field(0, description="CPU usage percentage")
    cpu_count: int = Field(0, description="Number of physical CPU cores")
    cpu_count_logical: int = Field(0, description="Number of logical CPU cores")
    memory_total_gb: float = Field(0, description="Total system memory in GB")
    memory_used_gb: float = Field(0, description="Used system memory in GB")
    memory_available_gb: float = Field(0, description="Available system memory in GB")
    memory_percent: float = Field(0, description="Memory usage percentage")
    timestamp: str = Field(..., description="Timestamp of measurement")
    error: str | None = Field(None, description="Error message if any")


class SystemMetricsHistoryPoint(BaseModel):
    """Single point in system metrics history."""

    timestamp: str = Field(..., description="Timestamp of snapshot")
    cpu_percent: float = Field(0, description="CPU usage percentage")
    memory_percent: float = Field(0, description="Memory usage percentage")
    memory_used_gb: float = Field(0, description="Memory used in GB")
    memory_total_gb: float = Field(0, description="Total memory in GB")
    gpu_available: bool = Field(False, description="Whether GPU is available")
    gpu_utilization_percent: float = Field(0, description="GPU utilization percentage")
    vram_used_gb: float = Field(0, description="VRAM used in GB")
    vram_total_gb: float = Field(0, description="Total VRAM in GB")
    gpu_temperature_celsius: float = Field(0, description="GPU temperature")
    queue_depth: int = Field(0, description="Request queue depth")


class SystemMetricsHistoryResponse(BaseModel):
    """System metrics history response."""

    time_range: str = Field(..., description="Time range (e.g., '1h', '6h', '24h')")
    data_points: int = Field(..., description="Number of data points")
    data: list[SystemMetricsHistoryPoint] = Field(
        default_factory=list, description="Historical metrics data"
    )


# ============================================================================
# Enhanced Stats Models (with percentiles)
# ============================================================================


class ModelPerformanceStats(BaseModel):
    """Performance statistics for a single model."""

    model_name: str = Field(..., description="Model name")
    request_count: int = Field(..., description="Total requests")
    error_count: int = Field(..., description="Total errors")
    total_tokens: int = Field(..., description="Total tokens generated")
    avg_latency_ms: float = Field(..., description="Average latency")
    p50_latency_ms: float = Field(..., description="P50 latency")
    p95_latency_ms: float = Field(..., description="P95 latency")
    p99_latency_ms: float = Field(..., description="P99 latency")
    tokens_per_second: float = Field(..., description="Tokens per second")


class EnhancedStatsResponse(BaseModel):
    """Enhanced stats with percentiles and queue metrics."""

    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    queue_depth: int = Field(..., description="Current pending requests")
    total_requests: int = Field(..., description="Total requests processed")
    total_errors: int = Field(..., description="Total errors")
    total_tokens: int = Field(..., description="Total tokens generated")
    tokens_per_second: float = Field(..., description="Current tokens/sec rate")
    error_rate_percent: float = Field(..., description="Error rate percentage")
    latency_p50_ms: float = Field(..., description="P50 latency")
    latency_p95_ms: float = Field(..., description="P95 latency")
    latency_p99_ms: float = Field(..., description="P99 latency")
    active_models: list[str] = Field(..., description="Recently active models")
    model_count: int = Field(..., description="Number of unique models")
    models: dict[str, ModelPerformanceStats] = Field(
        default_factory=dict, description="Per-model statistics"
    )


# ============================================================================
# Infrastructure Health Models
# ============================================================================


class ServiceHealthStatus(BaseModel):
    """Health status of a single service."""

    name: str = Field(..., description="Service name")
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Health status")
    latency_ms: float | None = Field(None, description="Health check latency")
    message: str | None = Field(None, description="Status message")
    last_check: datetime = Field(..., description="Last check timestamp")


class InfrastructureHealthResponse(BaseModel):
    """Infrastructure health response."""

    overall_status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall system status"
    )
    timestamp: datetime = Field(..., description="Check timestamp")

    # Service health
    services: list[ServiceHealthStatus] = Field(..., description="Service health statuses")

    # Resource metrics
    gpu_available: bool = Field(..., description="GPU availability")
    gpu_utilization_percent: float = Field(0, description="GPU utilization")
    gpu_temperature_celsius: float = Field(0, description="GPU temperature")
    vram_used_gb: float = Field(0, description="VRAM used in GB")
    vram_total_gb: float = Field(0, description="Total VRAM in GB")

    # Request metrics
    queue_depth: int = Field(0, description="Pending requests")
    error_count_24h: int = Field(0, description="Errors in last 24 hours")
    error_rate_24h_percent: float = Field(0, description="Error rate in last 24 hours")

    # Model info
    active_models: list[str] = Field(default_factory=list, description="Active models")
    loaded_models_count: int = Field(0, description="Number of loaded models")


# ============================================================================
# Kubernetes Probe Models
# ============================================================================


class ReadinessResponse(BaseModel):
    """Kubernetes readiness probe response."""

    ready: bool = Field(..., description="Whether service is ready")
    checks: dict[str, bool] = Field(..., description="Individual check results")
    message: str | None = Field(None, description="Status message")


class LivenessResponse(BaseModel):
    """Kubernetes liveness probe response."""

    alive: bool = Field(..., description="Whether service is alive")
    uptime_seconds: float = Field(..., description="Service uptime")
    message: str | None = Field(None, description="Status message")

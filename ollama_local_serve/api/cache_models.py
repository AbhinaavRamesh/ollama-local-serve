"""
Pydantic models for the response cache layer.

Provides request/response models for cache statistics,
configuration updates, and cache entry inspection.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""

    enabled: bool
    max_size: int
    current_size: int
    ttl_seconds: int
    hit_count: int
    miss_count: int
    hit_rate_percent: float
    eviction_count: int
    excluded_models: list[str]


class CacheConfigUpdateRequest(BaseModel):
    """Request model for updating cache configuration."""

    enabled: bool | None = None
    max_size: int | None = Field(default=None, ge=1)
    ttl_seconds: int | None = Field(default=None, gt=0)
    excluded_models: list[str] | None = None


class CacheEntryResponse(BaseModel):
    """Response model for a single cache entry."""

    cache_key: str
    model: str
    created_at: datetime
    expires_at: datetime
    hit_count: int

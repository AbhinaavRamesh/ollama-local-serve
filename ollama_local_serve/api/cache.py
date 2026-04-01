"""
Response cache layer for Ollama Local Serve.

Provides an LRU response cache with configurable TTL and max size.
Uses only stdlib: collections.OrderedDict, hashlib, threading, json, time.
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from ollama_local_serve.config import AppConfig


@dataclass
class CacheEntry:
    """A single cached response entry."""

    key: str
    model: str
    response: dict
    created_at: float
    expires_at: float
    hit_count: int = field(default=0)


class ResponseCache:
    """
    LRU response cache with TTL expiration.

    Uses collections.OrderedDict for O(1) LRU operations:
    - move_to_end(key) on cache hit
    - popitem(last=False) for LRU eviction

    Thread-safe via threading.Lock (synchronous operations on OrderedDict).
    """

    def __init__(
        self,
        enabled: bool = True,
        max_size: int = 256,
        ttl_seconds: int = 300,
        excluded_models: list[str] | None = None,
    ) -> None:
        self._enabled = enabled
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._excluded_models = excluded_models or []
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0

    @property
    def enabled(self) -> bool:
        """Whether the cache is enabled."""
        return self._enabled

    @staticmethod
    def _compute_key(model: str, prompt: str, params: dict) -> str:
        """
        Compute a deterministic cache key.

        Uses SHA-256 hash of the JSON-serialized combination of
        model, prompt, and additional parameters.
        """
        key_data = json.dumps(
            {"model": model, "prompt": prompt, **params},
            sort_keys=True,
        )
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, model: str, prompt: str, params: dict) -> dict | None:
        """
        Look up a cached response.

        Returns the cached response dict on hit, or None on miss.
        Expired entries are removed. Hits move the entry to the end (most recent).
        """
        if not self._enabled:
            return None

        key = self._compute_key(model, prompt, params)
        now = time.time()

        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if now < entry.expires_at:
                    # Cache hit
                    entry.hit_count += 1
                    self._hit_count += 1
                    self._cache.move_to_end(key)
                    return entry.response
                else:
                    # Expired — remove
                    del self._cache[key]

            self._miss_count += 1
            return None

    def put(self, model: str, prompt: str, params: dict, response: dict) -> None:
        """
        Store a response in the cache.

        Skips caching if the model is in the excluded list.
        Evicts the least-recently-used entry if at max capacity.
        """
        if not self._enabled:
            return

        if model in self._excluded_models:
            return

        key = self._compute_key(model, prompt, params)
        now = time.time()

        with self._lock:
            # If key already exists, remove it first so we re-insert at end
            if key in self._cache:
                del self._cache[key]

            # Evict LRU if at capacity
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                self._eviction_count += 1

            self._cache[key] = CacheEntry(
                key=key,
                model=model,
                response=response,
                created_at=now,
                expires_at=now + self._ttl_seconds,
            )

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            The number of entries that were cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> dict:
        """Return cache statistics and configuration."""
        with self._lock:
            total = self._hit_count + self._miss_count
            hit_rate = (self._hit_count / total * 100.0) if total > 0 else 0.0
            return {
                "enabled": self._enabled,
                "max_size": self._max_size,
                "current_size": len(self._cache),
                "ttl_seconds": self._ttl_seconds,
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "hit_rate_percent": round(hit_rate, 2),
                "eviction_count": self._eviction_count,
                "excluded_models": list(self._excluded_models),
            }

    def update_config(
        self,
        enabled: bool | None = None,
        max_size: int | None = None,
        ttl_seconds: int | None = None,
        excluded_models: list[str] | None = None,
    ) -> None:
        """
        Update cache configuration at runtime.

        If max_size is reduced, excess LRU entries are evicted immediately.
        """
        with self._lock:
            if enabled is not None:
                self._enabled = enabled
            if ttl_seconds is not None:
                self._ttl_seconds = ttl_seconds
            if excluded_models is not None:
                self._excluded_models = excluded_models
            if max_size is not None:
                self._max_size = max_size
                # Evict excess entries if max_size was reduced
                while len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)
                    self._eviction_count += 1


# Module-level singleton
_response_cache: ResponseCache | None = None
_cache_lock = threading.Lock()


def get_response_cache() -> ResponseCache:
    """
    Get the module-level ResponseCache singleton.

    Initializes from AppConfig().cache on first call.
    """
    global _response_cache
    if _response_cache is None:
        with _cache_lock:
            if _response_cache is None:
                config = AppConfig().cache
                _response_cache = ResponseCache(
                    enabled=config.enabled,
                    max_size=config.max_size,
                    ttl_seconds=config.ttl_seconds,
                    excluded_models=config.excluded_models_list,
                )
    return _response_cache

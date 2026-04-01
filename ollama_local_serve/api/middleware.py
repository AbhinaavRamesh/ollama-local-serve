"""
Authentication and rate limiting middleware for the Ollama Local Serve API.

Provides:
- API key authentication via X-API-Key header or Authorization: Bearer <key>
- In-memory sliding window rate limiting per client IP
"""

import asyncio
import logging
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Paths that bypass authentication
AUTH_EXEMPT_PATHS: set[str] = {
    "/health",
    "/api/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates API key authentication.

    Checks for a valid API key in either:
    - X-API-Key header
    - Authorization: Bearer <key> header

    If no API key is configured (api_key is None or empty), all requests
    are allowed through without authentication.

    The /health endpoint is always accessible without authentication.
    """

    def __init__(self, app, api_key: str | None = None) -> None:
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        """Process the request, validating API key if configured."""
        # Skip auth if no API key is configured
        if not self.api_key:
            return await call_next(request)

        # Skip auth for exempt paths
        if request.url.path in AUTH_EXEMPT_PATHS:
            return await call_next(request)

        # Extract API key from headers
        provided_key = self._extract_api_key(request)

        if not provided_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing API key. Provide via X-API-Key header or Authorization: Bearer <key>.",
                    "status_code": 401,
                },
            )

        if provided_key != self.api_key:
            logger.warning(
                "Invalid API key attempt from %s",
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid API key.",
                    "status_code": 401,
                },
            )

        return await call_next(request)

    @staticmethod
    def _extract_api_key(request: Request) -> str | None:
        """
        Extract the API key from request headers.

        Checks X-API-Key header first, then Authorization: Bearer <key>.

        Args:
            request: The incoming HTTP request.

        Returns:
            The API key string, or None if not found.
        """
        # Check X-API-Key header
        api_key = request.headers.get("x-api-key")
        if api_key:
            return api_key

        # Check Authorization: Bearer <key>
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()

        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter per client IP.

    Tracks request timestamps per client IP and enforces a maximum number
    of requests within a sliding time window. Returns 429 Too Many Requests
    with a Retry-After header when the limit is exceeded.

    If rate limiting is not configured (max_requests or window_seconds is 0),
    all requests pass through without limiting.

    Expired entries are periodically cleaned up to prevent memory leaks.
    """

    def __init__(
        self,
        app,
        max_requests: int = 0,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._enabled = max_requests > 0 and window_seconds > 0

    async def dispatch(self, request: Request, call_next):
        """Process the request, enforcing rate limits if configured."""
        # Skip if rate limiting is disabled
        if not self._enabled:
            return await call_next(request)

        # Ensure cleanup task is running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        client_ip = self._get_client_ip(request)
        now = time.monotonic()

        async with self._lock:
            # Remove expired timestamps for this client
            window_start = now - self.window_seconds
            self._requests[client_ip] = [
                ts for ts in self._requests[client_ip] if ts > window_start
            ]

            # Check if rate limit is exceeded
            if len(self._requests[client_ip]) >= self.max_requests:
                # Calculate retry-after from the oldest request in the window
                oldest = self._requests[client_ip][0]
                retry_after = int(oldest - window_start) + 1
                retry_after = max(retry_after, 1)

                logger.warning(
                    "Rate limit exceeded for client %s: %d requests in %ds window",
                    client_ip,
                    len(self._requests[client_ip]),
                    self.window_seconds,
                )

                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please retry later.",
                        "status_code": 429,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            # Record this request
            self._requests[client_ip].append(now)

        return await call_next(request)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Get the client IP address from the request.

        Checks X-Forwarded-For header first for proxied requests,
        then falls back to the direct client address.

        Args:
            request: The incoming HTTP request.

        Returns:
            The client IP address string.
        """
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    async def _periodic_cleanup(self) -> None:
        """Periodically remove expired rate limit entries to prevent memory leaks."""
        while True:
            try:
                await asyncio.sleep(self.window_seconds * 2)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error during rate limit cleanup")

    async def _cleanup_expired(self) -> None:
        """Remove all expired entries from the rate limit tracker."""
        now = time.monotonic()
        window_start = now - self.window_seconds

        async with self._lock:
            expired_keys = [
                ip
                for ip, timestamps in self._requests.items()
                if not timestamps or timestamps[-1] <= window_start
            ]
            for key in expired_keys:
                del self._requests[key]

            if expired_keys:
                logger.debug("Cleaned up %d expired rate limit entries", len(expired_keys))

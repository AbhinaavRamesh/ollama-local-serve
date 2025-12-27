"""
Prometheus Metrics Collector for Ollama Local Serve.

Provides:
- Request queue tracking
- Latency percentile calculations (P50, P95, P99)
- Token throughput by model
- Prometheus/OpenMetrics format export
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LatencyRecord:
    """Single latency measurement."""

    timestamp: float
    latency_ms: float
    model: str
    tokens: int
    status: str


@dataclass
class ModelMetrics:
    """Metrics for a single model."""

    request_count: int = 0
    error_count: int = 0
    total_tokens: int = 0
    latencies: list[float] = field(default_factory=list)
    last_request_time: float | None = None

    def add_request(self, latency_ms: float, tokens: int, is_error: bool = False):
        """Record a request."""
        self.request_count += 1
        if is_error:
            self.error_count += 1
        self.total_tokens += tokens
        self.latencies.append(latency_ms)
        self.last_request_time = time.time()

        # Keep only last 1000 latencies for percentile calculation
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]

    def get_percentiles(self) -> dict[str, float]:
        """Calculate latency percentiles."""
        if not self.latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        def percentile(p: float) -> float:
            idx = int(n * p / 100)
            return sorted_latencies[min(idx, n - 1)]

        return {
            "p50": round(percentile(50), 2),
            "p95": round(percentile(95), 2),
            "p99": round(percentile(99), 2),
        }

    def get_avg_latency(self) -> float:
        """Get average latency."""
        if not self.latencies:
            return 0.0
        return round(sum(self.latencies) / len(self.latencies), 2)


class RequestQueue:
    """
    Track pending requests for queue depth monitoring.

    Thread-safe request queue tracker.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize request queue.

        Args:
            max_history: Maximum number of completed requests to track
        """
        self._pending: dict[str, float] = {}  # request_id -> start_time
        self._completed: deque = deque(maxlen=max_history)
        self._lock = Lock()
        self._total_requests = 0
        self._total_errors = 0

    def start_request(self, request_id: str) -> None:
        """Mark a request as started."""
        with self._lock:
            self._pending[request_id] = time.time()
            self._total_requests += 1

    def complete_request(
        self, request_id: str, latency_ms: float, model: str, tokens: int, is_error: bool = False
    ) -> None:
        """Mark a request as completed."""
        with self._lock:
            start_time = self._pending.pop(request_id, None)
            if is_error:
                self._total_errors += 1

            self._completed.append(
                LatencyRecord(
                    timestamp=time.time(),
                    latency_ms=latency_ms,
                    model=model,
                    tokens=tokens,
                    status="error" if is_error else "success",
                )
            )

    @property
    def queue_depth(self) -> int:
        """Get current queue depth (pending requests)."""
        with self._lock:
            return len(self._pending)

    @property
    def total_requests(self) -> int:
        """Get total request count."""
        with self._lock:
            return self._total_requests

    @property
    def total_errors(self) -> int:
        """Get total error count."""
        with self._lock:
            return self._total_errors

    def get_recent_latencies(self, window_seconds: int = 60) -> list[LatencyRecord]:
        """Get latency records from the last N seconds."""
        cutoff = time.time() - window_seconds
        with self._lock:
            return [r for r in self._completed if r.timestamp > cutoff]


class MetricsCollector:
    """
    Central metrics collector for Prometheus export.

    Collects and aggregates:
    - Request metrics (count, errors, latency)
    - Token metrics (total, per-model, throughput)
    - Queue metrics (depth, wait time)
    - Model metrics (per-model breakdown)
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._start_time = time.time()
        self._model_metrics: dict[str, ModelMetrics] = {}
        self._request_queue = RequestQueue()
        self._lock = Lock()

        # Sliding window for throughput calculation
        self._token_window: deque = deque(maxlen=3600)  # 1 hour of per-second buckets
        self._current_second_tokens = 0
        self._last_second = int(time.time())

    def record_request(
        self,
        request_id: str,
        model: str,
        latency_ms: float,
        tokens: int,
        is_error: bool = False,
    ) -> None:
        """
        Record a completed request.

        Args:
            request_id: Unique request identifier
            model: Model name used
            latency_ms: Request latency in milliseconds
            tokens: Number of tokens generated
            is_error: Whether the request resulted in an error
        """
        with self._lock:
            # Update model metrics
            if model not in self._model_metrics:
                self._model_metrics[model] = ModelMetrics()
            self._model_metrics[model].add_request(latency_ms, tokens, is_error)

            # Update token window for throughput
            current_second = int(time.time())
            if current_second != self._last_second:
                # Flush previous second
                self._token_window.append((self._last_second, self._current_second_tokens))
                self._current_second_tokens = tokens
                self._last_second = current_second
            else:
                self._current_second_tokens += tokens

        # Update request queue
        self._request_queue.complete_request(request_id, latency_ms, model, tokens, is_error)

    def start_request(self, request_id: str) -> None:
        """Mark a request as started (for queue tracking)."""
        self._request_queue.start_request(request_id)

    def get_queue_depth(self) -> int:
        """Get current request queue depth."""
        return self._request_queue.queue_depth

    def get_tokens_per_second(self, window_seconds: int = 60) -> float:
        """
        Calculate tokens per second over a time window.

        Args:
            window_seconds: Time window in seconds

        Returns:
            Tokens per second rate
        """
        with self._lock:
            cutoff = time.time() - window_seconds
            total_tokens = sum(tokens for ts, tokens in self._token_window if ts > cutoff)
            # Add current second's tokens
            if time.time() - self._last_second < window_seconds:
                total_tokens += self._current_second_tokens

            return round(total_tokens / window_seconds, 2)

    def get_model_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get per-model statistics.

        Returns:
            Dictionary of model name -> stats
        """
        with self._lock:
            result = {}
            for model, metrics in self._model_metrics.items():
                percentiles = metrics.get_percentiles()
                result[model] = {
                    "request_count": metrics.request_count,
                    "error_count": metrics.error_count,
                    "total_tokens": metrics.total_tokens,
                    "avg_latency_ms": metrics.get_avg_latency(),
                    "p50_latency_ms": percentiles["p50"],
                    "p95_latency_ms": percentiles["p95"],
                    "p99_latency_ms": percentiles["p99"],
                    "tokens_per_second": self._calculate_model_tps(model),
                }
            return result

    def _calculate_model_tps(self, model: str) -> float:
        """Calculate tokens per second for a specific model."""
        recent = self._request_queue.get_recent_latencies(60)
        model_records = [r for r in recent if r.model == model]
        if not model_records:
            return 0.0
        total_tokens = sum(r.tokens for r in model_records)
        return round(total_tokens / 60, 2)

    def get_global_percentiles(self) -> dict[str, float]:
        """Get global latency percentiles across all models."""
        with self._lock:
            all_latencies = []
            for metrics in self._model_metrics.values():
                all_latencies.extend(metrics.latencies)

            if not all_latencies:
                return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

            sorted_latencies = sorted(all_latencies)
            n = len(sorted_latencies)

            def percentile(p: float) -> float:
                idx = int(n * p / 100)
                return sorted_latencies[min(idx, n - 1)]

            return {
                "p50": round(percentile(50), 2),
                "p95": round(percentile(95), 2),
                "p99": round(percentile(99), 2),
            }

    def get_uptime_seconds(self) -> float:
        """Get collector uptime in seconds."""
        return time.time() - self._start_time

    def get_active_models(self) -> list[str]:
        """Get list of models with recent activity."""
        with self._lock:
            cutoff = time.time() - 3600  # Active in last hour
            return [
                model
                for model, metrics in self._model_metrics.items()
                if metrics.last_request_time and metrics.last_request_time > cutoff
            ]

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of all metrics.

        Returns:
            Dictionary with aggregated metrics
        """
        model_stats = self.get_model_stats()
        global_percentiles = self.get_global_percentiles()

        total_requests = sum(s["request_count"] for s in model_stats.values())
        total_errors = sum(s["error_count"] for s in model_stats.values())
        total_tokens = sum(s["total_tokens"] for s in model_stats.values())

        return {
            "uptime_seconds": round(self.get_uptime_seconds(), 2),
            "queue_depth": self.get_queue_depth(),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "total_tokens": total_tokens,
            "tokens_per_second": self.get_tokens_per_second(),
            "error_rate_percent": round(
                (total_errors / total_requests * 100) if total_requests > 0 else 0, 2
            ),
            "latency_p50_ms": global_percentiles["p50"],
            "latency_p95_ms": global_percentiles["p95"],
            "latency_p99_ms": global_percentiles["p99"],
            "active_models": self.get_active_models(),
            "model_count": len(self._model_metrics),
            "models": model_stats,
        }

    def to_prometheus(self) -> str:
        """
        Export metrics in Prometheus/OpenMetrics format.

        Returns:
            String in Prometheus exposition format
        """
        lines = []
        summary = self.get_summary()

        # Uptime
        lines.append("# HELP ollama_uptime_seconds Service uptime in seconds")
        lines.append("# TYPE ollama_uptime_seconds gauge")
        lines.append(f"ollama_uptime_seconds {summary['uptime_seconds']}")

        # Queue depth
        lines.append("# HELP ollama_queue_depth Current number of pending requests")
        lines.append("# TYPE ollama_queue_depth gauge")
        lines.append(f"ollama_queue_depth {summary['queue_depth']}")

        # Total requests
        lines.append("# HELP ollama_requests_total Total number of requests")
        lines.append("# TYPE ollama_requests_total counter")
        lines.append(f"ollama_requests_total {summary['total_requests']}")

        # Total errors
        lines.append("# HELP ollama_errors_total Total number of errors")
        lines.append("# TYPE ollama_errors_total counter")
        lines.append(f"ollama_errors_total {summary['total_errors']}")

        # Total tokens
        lines.append("# HELP ollama_tokens_total Total tokens generated")
        lines.append("# TYPE ollama_tokens_total counter")
        lines.append(f"ollama_tokens_total {summary['total_tokens']}")

        # Tokens per second
        lines.append("# HELP ollama_tokens_per_second Current tokens per second rate")
        lines.append("# TYPE ollama_tokens_per_second gauge")
        lines.append(f"ollama_tokens_per_second {summary['tokens_per_second']}")

        # Global latency percentiles
        lines.append("# HELP ollama_request_latency_ms Request latency in milliseconds")
        lines.append("# TYPE ollama_request_latency_ms summary")
        lines.append(f'ollama_request_latency_ms{{quantile="0.5"}} {summary["latency_p50_ms"]}')
        lines.append(f'ollama_request_latency_ms{{quantile="0.95"}} {summary["latency_p95_ms"]}')
        lines.append(f'ollama_request_latency_ms{{quantile="0.99"}} {summary["latency_p99_ms"]}')

        # Per-model metrics
        for model, stats in summary.get("models", {}).items():
            safe_model = model.replace('"', '\\"')
            labels = f'model="{safe_model}"'

            lines.append("# HELP ollama_model_requests_total Requests per model")
            lines.append("# TYPE ollama_model_requests_total counter")
            lines.append(f"ollama_model_requests_total{{{labels}}} {stats['request_count']}")

            lines.append("# HELP ollama_model_tokens_total Tokens per model")
            lines.append("# TYPE ollama_model_tokens_total counter")
            lines.append(f"ollama_model_tokens_total{{{labels}}} {stats['total_tokens']}")

            lines.append("# HELP ollama_model_errors_total Errors per model")
            lines.append("# TYPE ollama_model_errors_total counter")
            lines.append(f"ollama_model_errors_total{{{labels}}} {stats['error_count']}")

            lines.append("# HELP ollama_model_tokens_per_second Tokens/sec per model")
            lines.append("# TYPE ollama_model_tokens_per_second gauge")
            lines.append(f"ollama_model_tokens_per_second{{{labels}}} {stats['tokens_per_second']}")

            # Per-model latency percentiles
            lines.append("# HELP ollama_model_latency_ms Latency per model")
            lines.append("# TYPE ollama_model_latency_ms summary")
            lines.append(
                f'ollama_model_latency_ms{{{labels},quantile="0.5"}} {stats["p50_latency_ms"]}'
            )
            lines.append(
                f'ollama_model_latency_ms{{{labels},quantile="0.95"}} {stats["p95_latency_ms"]}'
            )
            lines.append(
                f'ollama_model_latency_ms{{{labels},quantile="0.99"}} {stats["p99_latency_ms"]}'
            )

        return "\n".join(lines)


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

"""
Model Benchmarking & Comparison Engine.

Runs benchmarks against multiple Ollama models, collecting timing metrics
(TTFT, total generation time, tokens/sec) and providing comparison rankings.
"""

import asyncio
import json
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import aiohttp

from ollama_local_serve.api.benchmark_models import (
    BenchmarkResponse,
    BenchmarkStatusResponse,
    ComparisonRanking,
    ModelBenchmarkSummary,
    PromptSummary,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Internal dataclasses for collecting raw iteration data
# ============================================================================


@dataclass
class IterationMetrics:
    """Raw metrics from a single benchmark iteration."""

    prompt: str
    iteration: int
    time_to_first_token_ms: float = 0.0
    total_generation_time_ms: float = 0.0
    tokens_per_second: float = 0.0
    total_tokens: int = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class BenchmarkResult:
    """Complete result set for a benchmark run."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    config: dict = field(default_factory=dict)
    model_results: dict[str, list[IterationMetrics]] = field(default_factory=dict)


# ============================================================================
# Percentile helper
# ============================================================================


def _percentile(sorted_values: list[float], p: float) -> float:
    """Calculate the p-th percentile from a sorted list of values."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


# ============================================================================
# BenchmarkRunner
# ============================================================================


class BenchmarkRunner:
    """
    Runs benchmarks against multiple Ollama models.

    Accepts a list of model names and test prompts, measures timing metrics,
    and produces comparison rankings.
    """

    def __init__(self, ollama_base_url: str = "http://localhost:11434") -> None:
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self._lock = asyncio.Lock()
        self._is_running = False
        self._progress: str | None = None
        self._started_at: datetime | None = None
        self._latest_result: BenchmarkResponse | None = None

    # ------------------------------------------------------------------
    # Public status helpers
    # ------------------------------------------------------------------

    def get_status(self) -> BenchmarkStatusResponse:
        """Return the current benchmark status."""
        return BenchmarkStatusResponse(
            is_running=self._is_running,
            progress=self._progress,
            started_at=self._started_at,
        )

    def get_latest_result(self) -> BenchmarkResponse | None:
        """Return the most recent benchmark result, or None."""
        return self._latest_result

    # ------------------------------------------------------------------
    # Run benchmark
    # ------------------------------------------------------------------

    async def run(
        self,
        models: list[str],
        prompts: list[str],
        iterations: int = 3,
        max_tokens: int = 100,
    ) -> BenchmarkResponse:
        """
        Execute a full benchmark run.

        Args:
            models: Model names to benchmark.
            prompts: Prompts to test each model with.
            iterations: Number of iterations per prompt.
            max_tokens: Max tokens to generate per request.

        Returns:
            BenchmarkResponse with all metrics and rankings.

        Raises:
            RuntimeError: If a benchmark is already in progress.
        """
        async with self._lock:
            if self._is_running:
                raise RuntimeError("A benchmark is already running")
            self._is_running = True
            self._started_at = datetime.now(timezone.utc)
            self._progress = "Starting benchmark"

        result = BenchmarkResult(
            started_at=self._started_at,  # type: ignore[arg-type]
            config={
                "models": models,
                "prompts": prompts,
                "iterations": iterations,
                "max_tokens": max_tokens,
            },
        )

        try:
            for model_idx, model in enumerate(models, 1):
                self._progress = (
                    f"Benchmarking model {model_idx}/{len(models)}: {model}"
                )
                logger.info(self._progress)

                model_metrics: list[IterationMetrics] = []

                for prompt_idx, prompt in enumerate(prompts, 1):
                    for iteration in range(1, iterations + 1):
                        self._progress = (
                            f"Model {model_idx}/{len(models)} ({model}) - "
                            f"Prompt {prompt_idx}/{len(prompts)} - "
                            f"Iteration {iteration}/{iterations}"
                        )
                        metrics = await self._run_single(
                            model=model,
                            prompt=prompt,
                            iteration=iteration,
                            max_tokens=max_tokens,
                        )
                        model_metrics.append(metrics)

                result.model_results[model] = model_metrics

            result.completed_at = datetime.now(timezone.utc)

            response = self._build_response(result)
            self._latest_result = response
            return response

        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            raise
        finally:
            async with self._lock:
                self._is_running = False
                self._progress = None
                self._started_at = None

    # ------------------------------------------------------------------
    # Single iteration against Ollama /api/generate (streaming)
    # ------------------------------------------------------------------

    async def _run_single(
        self,
        model: str,
        prompt: str,
        iteration: int,
        max_tokens: int,
    ) -> IterationMetrics:
        """Run a single prompt iteration against Ollama and measure timing."""
        url = f"{self._ollama_base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_predict": max_tokens},
        }

        metrics = IterationMetrics(prompt=prompt, iteration=iteration)

        try:
            timeout = aiohttp.ClientTimeout(total=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start_time = time.perf_counter()
                first_token_time: float | None = None
                total_tokens = 0

                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        metrics.error = f"HTTP {resp.status}: {body}"
                        return metrics

                    async for line in resp.content:
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # Record time of first token with actual content
                        if first_token_time is None and chunk.get("response"):
                            first_token_time = time.perf_counter()

                        # Ollama sends eval_count in the final chunk (done=true)
                        if chunk.get("done"):
                            total_tokens = chunk.get("eval_count", total_tokens)
                            break
                        elif chunk.get("response"):
                            total_tokens += 1

                end_time = time.perf_counter()

                total_ms = (end_time - start_time) * 1000.0
                ttft_ms = (
                    (first_token_time - start_time) * 1000.0
                    if first_token_time is not None
                    else total_ms
                )
                tps = (total_tokens / (total_ms / 1000.0)) if total_ms > 0 else 0.0

                metrics.time_to_first_token_ms = round(ttft_ms, 2)
                metrics.total_generation_time_ms = round(total_ms, 2)
                metrics.tokens_per_second = round(tps, 2)
                metrics.total_tokens = total_tokens

        except asyncio.TimeoutError:
            metrics.error = "Request timed out (300s)"
        except aiohttp.ClientError as e:
            metrics.error = f"Connection error: {e}"
        except Exception as e:
            metrics.error = f"Unexpected error: {e}"

        return metrics

    # ------------------------------------------------------------------
    # Build the response with summaries and rankings
    # ------------------------------------------------------------------

    def _build_response(self, result: BenchmarkResult) -> BenchmarkResponse:
        """Build a BenchmarkResponse from raw BenchmarkResult data."""
        model_summaries: list[ModelBenchmarkSummary] = []

        for model, iterations in result.model_results.items():
            summary = self._summarize_model(model, iterations)
            model_summaries.append(summary)

        rankings = self._compute_rankings(model_summaries)

        duration = 0.0
        if result.completed_at and result.started_at:
            duration = (result.completed_at - result.started_at).total_seconds()

        return BenchmarkResponse(
            status="completed",
            started_at=result.started_at,
            completed_at=result.completed_at or datetime.now(timezone.utc),
            duration_seconds=round(duration, 2),
            config=result.config,
            results=model_summaries,
            rankings=rankings,
        )

    def _summarize_model(
        self, model: str, iterations: list[IterationMetrics]
    ) -> ModelBenchmarkSummary:
        """Compute aggregated summary metrics for one model."""
        successful = [m for m in iterations if m.success]
        failed = [m for m in iterations if not m.success]

        if not successful:
            return ModelBenchmarkSummary(
                model_name=model,
                total_iterations=len(iterations),
                successful_iterations=0,
                failed_iterations=len(failed),
                min_latency_ms=0.0,
                max_latency_ms=0.0,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                min_ttft_ms=0.0,
                max_ttft_ms=0.0,
                avg_ttft_ms=0.0,
                p50_ttft_ms=0.0,
                p95_ttft_ms=0.0,
                avg_tokens_per_second=0.0,
                total_tokens_generated=0,
                prompt_summaries=[],
            )

        latencies = sorted([m.total_generation_time_ms for m in successful])
        ttfts = sorted([m.time_to_first_token_ms for m in successful])
        tps_values = [m.tokens_per_second for m in successful]
        total_tokens = sum(m.total_tokens for m in successful)

        # Per-prompt breakdown
        prompts_seen: dict[str, list[IterationMetrics]] = {}
        for m in successful:
            prompts_seen.setdefault(m.prompt, []).append(m)

        prompt_summaries = []
        for prompt_text, pms in prompts_seen.items():
            prompt_summaries.append(
                PromptSummary(
                    prompt=prompt_text,
                    iterations_completed=len(pms),
                    avg_time_to_first_token_ms=round(
                        sum(p.time_to_first_token_ms for p in pms) / len(pms), 2
                    ),
                    avg_total_generation_time_ms=round(
                        sum(p.total_generation_time_ms for p in pms) / len(pms), 2
                    ),
                    avg_tokens_per_second=round(
                        sum(p.tokens_per_second for p in pms) / len(pms), 2
                    ),
                    avg_total_tokens=round(
                        sum(p.total_tokens for p in pms) / len(pms), 2
                    ),
                )
            )

        return ModelBenchmarkSummary(
            model_name=model,
            total_iterations=len(iterations),
            successful_iterations=len(successful),
            failed_iterations=len(failed),
            min_latency_ms=round(latencies[0], 2),
            max_latency_ms=round(latencies[-1], 2),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2),
            p50_latency_ms=round(_percentile(latencies, 50), 2),
            p95_latency_ms=round(_percentile(latencies, 95), 2),
            min_ttft_ms=round(ttfts[0], 2),
            max_ttft_ms=round(ttfts[-1], 2),
            avg_ttft_ms=round(sum(ttfts) / len(ttfts), 2),
            p50_ttft_ms=round(_percentile(ttfts, 50), 2),
            p95_ttft_ms=round(_percentile(ttfts, 95), 2),
            avg_tokens_per_second=round(sum(tps_values) / len(tps_values), 2),
            total_tokens_generated=total_tokens,
            prompt_summaries=prompt_summaries,
        )

    def _compute_rankings(
        self, summaries: list[ModelBenchmarkSummary]
    ) -> list[ComparisonRanking]:
        """Rank models by speed (lowest latency) and throughput (highest tokens/sec)."""
        rankings: list[ComparisonRanking] = []

        # Filter to models with successful iterations
        valid = [s for s in summaries if s.successful_iterations > 0]

        if not valid:
            return rankings

        # Rank by speed (lowest average latency is best)
        by_speed = sorted(valid, key=lambda s: s.avg_latency_ms)
        rankings.append(
            ComparisonRanking(
                criterion="speed",
                rankings=[
                    {
                        "rank": i + 1,
                        "model": s.model_name,
                        "avg_latency_ms": s.avg_latency_ms,
                    }
                    for i, s in enumerate(by_speed)
                ],
            )
        )

        # Rank by throughput (highest tokens/sec is best)
        by_throughput = sorted(
            valid, key=lambda s: s.avg_tokens_per_second, reverse=True
        )
        rankings.append(
            ComparisonRanking(
                criterion="throughput",
                rankings=[
                    {
                        "rank": i + 1,
                        "model": s.model_name,
                        "avg_tokens_per_second": s.avg_tokens_per_second,
                    }
                    for i, s in enumerate(by_throughput)
                ],
            )
        )

        # Rank by time-to-first-token (lowest TTFT is best)
        by_ttft = sorted(valid, key=lambda s: s.avg_ttft_ms)
        rankings.append(
            ComparisonRanking(
                criterion="time_to_first_token",
                rankings=[
                    {
                        "rank": i + 1,
                        "model": s.model_name,
                        "avg_ttft_ms": s.avg_ttft_ms,
                    }
                    for i, s in enumerate(by_ttft)
                ],
            )
        )

        return rankings


# ============================================================================
# Module-level singleton
# ============================================================================

_benchmark_runner: BenchmarkRunner | None = None


def get_benchmark_runner(
    ollama_base_url: str = "http://localhost:11434",
) -> BenchmarkRunner:
    """Get or create the global BenchmarkRunner instance."""
    global _benchmark_runner
    if _benchmark_runner is None:
        _benchmark_runner = BenchmarkRunner(ollama_base_url=ollama_base_url)
    return _benchmark_runner

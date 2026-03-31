"""
Pydantic models for benchmark API request/response schemas.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================================
# Default Benchmark Prompts
# ============================================================================

DEFAULT_BENCHMARK_PROMPTS: list[str] = [
    "What is the capital of France? Answer in one sentence.",
    "Write a Python function that checks if a string is a palindrome.",
    "Write a short poem about the ocean at sunset.",
    "If a train travels 120 miles in 2 hours, and then 180 miles in 3 hours, what is the average speed for the entire trip? Show your reasoning.",
    "Explain the difference between a stack and a queue in computer science.",
]


# ============================================================================
# Request Models
# ============================================================================


class BenchmarkRequest(BaseModel):
    """Request to start a benchmark run."""

    models: list[str] = Field(
        ...,
        min_length=1,
        description="List of model names to benchmark",
    )
    prompts: list[str] = Field(
        default_factory=lambda: list(DEFAULT_BENCHMARK_PROMPTS),
        min_length=1,
        description="List of test prompts to run against each model",
    )
    iterations: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Number of iterations per prompt for averaging",
    )
    max_tokens: int = Field(
        default=100,
        ge=1,
        le=4096,
        description="Maximum tokens to generate per request",
    )


# ============================================================================
# Response Models
# ============================================================================


class IterationResult(BaseModel):
    """Result of a single benchmark iteration."""

    prompt: str = Field(..., description="The prompt used")
    iteration: int = Field(..., description="Iteration number")
    time_to_first_token_ms: float = Field(..., description="Time to first token in ms")
    total_generation_time_ms: float = Field(..., description="Total generation time in ms")
    tokens_per_second: float = Field(..., description="Tokens per second")
    total_tokens: int = Field(..., description="Total tokens generated")
    error: str | None = Field(None, description="Error message if the iteration failed")


class PromptSummary(BaseModel):
    """Aggregated metrics for a single prompt across iterations."""

    prompt: str = Field(..., description="The prompt text")
    iterations_completed: int = Field(..., description="Number of successful iterations")
    avg_time_to_first_token_ms: float = Field(..., description="Average TTFT in ms")
    avg_total_generation_time_ms: float = Field(..., description="Average total time in ms")
    avg_tokens_per_second: float = Field(..., description="Average tokens/sec")
    avg_total_tokens: float = Field(..., description="Average tokens generated")


class ModelBenchmarkSummary(BaseModel):
    """Summary of benchmark results for a single model."""

    model_name: str = Field(..., description="Model name")
    total_iterations: int = Field(..., description="Total iterations run")
    successful_iterations: int = Field(..., description="Number of successful iterations")
    failed_iterations: int = Field(..., description="Number of failed iterations")

    # Latency metrics (total generation time)
    min_latency_ms: float = Field(..., description="Minimum generation latency in ms")
    max_latency_ms: float = Field(..., description="Maximum generation latency in ms")
    avg_latency_ms: float = Field(..., description="Average generation latency in ms")
    p50_latency_ms: float = Field(..., description="P50 generation latency in ms")
    p95_latency_ms: float = Field(..., description="P95 generation latency in ms")

    # TTFT metrics
    min_ttft_ms: float = Field(..., description="Minimum time to first token in ms")
    max_ttft_ms: float = Field(..., description="Maximum time to first token in ms")
    avg_ttft_ms: float = Field(..., description="Average time to first token in ms")
    p50_ttft_ms: float = Field(..., description="P50 time to first token in ms")
    p95_ttft_ms: float = Field(..., description="P95 time to first token in ms")

    # Throughput metrics
    avg_tokens_per_second: float = Field(..., description="Average tokens per second")
    total_tokens_generated: int = Field(
        ..., description="Total tokens generated across all iterations"
    )

    # Per-prompt breakdown
    prompt_summaries: list[PromptSummary] = Field(
        default_factory=list, description="Per-prompt metric summaries"
    )


class ComparisonRanking(BaseModel):
    """Ranking of models by a specific criterion."""

    criterion: str = Field(
        ..., description="Ranking criterion (e.g., 'speed', 'throughput')"
    )
    rankings: list[dict[str, float | str]] = Field(
        ..., description="Ordered list of models with their scores"
    )


class BenchmarkResponse(BaseModel):
    """Complete benchmark results."""

    status: str = Field(..., description="Benchmark status (completed, failed)")
    started_at: datetime = Field(..., description="When the benchmark started")
    completed_at: datetime = Field(..., description="When the benchmark completed")
    duration_seconds: float = Field(..., description="Total benchmark duration in seconds")
    config: dict = Field(..., description="Benchmark configuration used")
    results: list[ModelBenchmarkSummary] = Field(
        ..., description="Per-model benchmark results"
    )
    rankings: list[ComparisonRanking] = Field(
        default_factory=list, description="Model comparison rankings"
    )


class BenchmarkStatusResponse(BaseModel):
    """Status of the current benchmark."""

    is_running: bool = Field(..., description="Whether a benchmark is currently running")
    progress: str | None = Field(None, description="Current progress description")
    started_at: datetime | None = Field(
        None, description="When the current benchmark started"
    )

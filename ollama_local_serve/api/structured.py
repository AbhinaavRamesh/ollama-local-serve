"""
Structured output validation and tool calling support for Ollama Local Serve.

Provides JSON Schema validation for structured outputs and tool call extraction
from Ollama responses, with in-memory tracking of success/failure rates.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

try:
    import jsonschema

    _jsonschema_available = True
except ImportError:
    _jsonschema_available = False
    logger.debug("jsonschema not installed, schema validation will be skipped")


@dataclass
class ValidationResult:
    """Result of JSON Schema validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ToolCall:
    """Parsed tool call from Ollama response."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredOutputRecord:
    """Record of a structured output request."""

    timestamp: float
    model: str
    request_type: str  # "structured" or "tool_call"
    schema_valid: bool | None = None
    tool_name: str | None = None
    tool_call_success: bool | None = None
    latency_ms: float = 0


def validate_against_schema(response: dict[str, Any], schema: dict[str, Any]) -> ValidationResult:
    """
    Validate a response dictionary against a JSON Schema.

    Args:
        response: The response data to validate.
        schema: The JSON Schema to validate against.

    Returns:
        ValidationResult with valid flag and any error messages.
    """
    if not _jsonschema_available:
        return ValidationResult(valid=True, errors=["jsonschema not installed, validation skipped"])

    try:
        jsonschema.validate(instance=response, schema=schema)
        return ValidationResult(valid=True)
    except jsonschema.ValidationError as e:
        return ValidationResult(valid=False, errors=[e.message])
    except jsonschema.SchemaError as e:
        return ValidationResult(valid=False, errors=[f"Invalid schema: {e.message}"])


def extract_tool_calls(response: dict[str, Any]) -> list[ToolCall]:
    """
    Extract tool calls from an Ollama chat response.

    Ollama returns tool calls in the message.tool_calls field.

    Args:
        response: The Ollama response dictionary.

    Returns:
        List of parsed ToolCall objects.
    """
    tool_calls = []
    message = response.get("message", {})
    raw_tool_calls = message.get("tool_calls", [])

    for tc in raw_tool_calls:
        function = tc.get("function", {})
        tool_calls.append(
            ToolCall(
                name=function.get("name", "unknown"),
                arguments=function.get("arguments", {}),
            )
        )

    return tool_calls


class StructuredOutputTracker:
    """
    In-memory tracker for structured output and tool calling statistics.

    Tracks schema validation pass/fail rates, tool call frequencies,
    and popular schemas/tools over a sliding window.
    """

    def __init__(self, max_records: int = 1000):
        self._records: deque[StructuredOutputRecord] = deque(maxlen=max_records)
        self._lock = Lock()

    def record_structured_output(
        self,
        model: str,
        schema_valid: bool,
        latency_ms: float,
    ) -> None:
        """Record a structured output request result."""
        with self._lock:
            self._records.append(
                StructuredOutputRecord(
                    timestamp=time.time(),
                    model=model,
                    request_type="structured",
                    schema_valid=schema_valid,
                    latency_ms=latency_ms,
                )
            )

    def record_tool_call(
        self,
        model: str,
        tool_name: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record a tool call request result."""
        with self._lock:
            self._records.append(
                StructuredOutputRecord(
                    timestamp=time.time(),
                    model=model,
                    request_type="tool_call",
                    tool_name=tool_name,
                    tool_call_success=success,
                    latency_ms=latency_ms,
                )
            )

    def get_stats(self) -> dict[str, Any]:
        """
        Get aggregated statistics for structured outputs and tool calls.

        Returns:
            Dictionary with structured output and tool call statistics.
        """
        with self._lock:
            records = list(self._records)

        structured = [r for r in records if r.request_type == "structured"]
        tool_calls = [r for r in records if r.request_type == "tool_call"]

        # Structured output stats
        structured_total = len(structured)
        structured_valid = sum(1 for r in structured if r.schema_valid)
        structured_invalid = structured_total - structured_valid

        # Tool call stats
        tool_call_total = len(tool_calls)
        tool_call_success = sum(1 for r in tool_calls if r.tool_call_success)
        tool_call_failure = tool_call_total - tool_call_success

        # Per-tool breakdown
        tool_counts: dict[str, dict[str, int]] = {}
        for r in tool_calls:
            name = r.tool_name or "unknown"
            if name not in tool_counts:
                tool_counts[name] = {"total": 0, "success": 0, "failure": 0}
            tool_counts[name]["total"] += 1
            if r.tool_call_success:
                tool_counts[name]["success"] += 1
            else:
                tool_counts[name]["failure"] += 1

        # Per-model breakdown
        model_counts: dict[str, dict[str, int]] = {}
        for r in records:
            if r.model not in model_counts:
                model_counts[r.model] = {"structured": 0, "tool_calls": 0}
            if r.request_type == "structured":
                model_counts[r.model]["structured"] += 1
            else:
                model_counts[r.model]["tool_calls"] += 1

        # Average latencies
        structured_avg_latency = (
            round(sum(r.latency_ms for r in structured) / structured_total, 2)
            if structured_total > 0
            else 0
        )
        tool_call_avg_latency = (
            round(sum(r.latency_ms for r in tool_calls) / tool_call_total, 2)
            if tool_call_total > 0
            else 0
        )

        return {
            "structured_outputs": {
                "total": structured_total,
                "valid": structured_valid,
                "invalid": structured_invalid,
                "validation_rate": (
                    round(structured_valid / structured_total * 100, 1)
                    if structured_total > 0
                    else 0
                ),
                "avg_latency_ms": structured_avg_latency,
            },
            "tool_calls": {
                "total": tool_call_total,
                "success": tool_call_success,
                "failure": tool_call_failure,
                "success_rate": (
                    round(tool_call_success / tool_call_total * 100, 1)
                    if tool_call_total > 0
                    else 0
                ),
                "avg_latency_ms": tool_call_avg_latency,
                "by_tool": tool_counts,
            },
            "by_model": model_counts,
            "total_requests": len(records),
        }


# Global tracker instance
_structured_tracker: StructuredOutputTracker | None = None


def get_structured_tracker() -> StructuredOutputTracker:
    """Get the global structured output tracker instance."""
    global _structured_tracker
    if _structured_tracker is None:
        _structured_tracker = StructuredOutputTracker()
    return _structured_tracker

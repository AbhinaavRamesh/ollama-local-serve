"""
MCP (Model Context Protocol) server for Ollama Local Serve.

Exposes the platform's capabilities as MCP tools so AI agents can
programmatically manage models, query metrics, and run inference.

Usage:
    python -m ollama_local_serve.mcp_server

Configuration via environment variables:
    OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
    API_HOST: Monitoring API URL (default: http://localhost:8000)
"""

import json
import logging
import os

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
API_HOST = os.getenv("API_HOST", "http://localhost:8000")

# Create MCP server
mcp = FastMCP(
    "ollama-local-serve",
    description="Manage and monitor local Ollama LLM infrastructure",
)


# ============================================================================
# Helper
# ============================================================================


async def _api_get(path: str, timeout: float = 30.0) -> dict:
    """Make a GET request to the monitoring API."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{API_HOST}{path}")
        response.raise_for_status()
        return response.json()


async def _api_post(path: str, data: dict, timeout: float | None = None) -> dict:
    """Make a POST request to the monitoring API."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{API_HOST}{path}", json=data)
        response.raise_for_status()
        return response.json()


async def _ollama_get(path: str, timeout: float = 30.0) -> dict:
    """Make a GET request directly to Ollama."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{OLLAMA_HOST}{path}")
        response.raise_for_status()
        return response.json()


async def _ollama_post(path: str, data: dict, timeout: float | None = None) -> dict:
    """Make a POST request directly to Ollama."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{OLLAMA_HOST}{path}", json=data)
        response.raise_for_status()
        return response.json()


# ============================================================================
# MCP Tools
# ============================================================================


@mcp.tool()
async def list_models() -> str:
    """List all available Ollama models with their sizes and modification dates."""
    try:
        data = await _ollama_get("/api/tags")
        models = data.get("models", [])
        if not models:
            return "No models installed."

        lines = []
        for m in models:
            name = m.get("name", "unknown")
            size_gb = m.get("size", 0) / (1024**3)
            modified = m.get("modified_at", "unknown")
            lines.append(f"- {name} ({size_gb:.1f} GB, modified: {modified})")

        return f"**{len(models)} models available:**\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listing models: {e}"


@mcp.tool()
async def pull_model(name: str) -> str:
    """
    Download a model from the Ollama registry.

    Args:
        name: Model name to pull (e.g., "llama3.2", "deepseek-coder-v2")
    """
    try:
        result = await _ollama_post(
            "/api/pull",
            {"name": name, "stream": False},
            timeout=600.0,
        )
        return f"Successfully pulled model: {name}\n{json.dumps(result, indent=2)}"
    except Exception as e:
        return f"Error pulling model {name}: {e}"


@mcp.tool()
async def delete_model(name: str) -> str:
    """
    Delete a model from Ollama.

    Args:
        name: Model name to delete
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{OLLAMA_HOST}/api/delete",
                json={"name": name},
            )
            response.raise_for_status()
        return f"Successfully deleted model: {name}"
    except Exception as e:
        return f"Error deleting model {name}: {e}"


@mcp.tool()
async def chat(
    model: str,
    message: str,
    system: str | None = None,
) -> str:
    """
    Send a chat message to an Ollama model and get a response.

    Args:
        model: Model name to use (e.g., "llama3.2"). Use "auto" for smart routing.
        message: The user message to send
        system: Optional system prompt
    """
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})

        # Use monitoring API for logging/routing, fall back to direct Ollama
        try:
            result = await _api_post(
                "/api/chat",
                {"model": model, "messages": messages, "stream": False},
                timeout=300.0,
            )
        except Exception:
            result = await _ollama_post(
                "/api/chat",
                {"model": model, "messages": messages, "stream": False},
                timeout=300.0,
            )

        # Extract response
        content = result.get("message", {}).get("content", "")
        prompt_tokens = result.get("prompt_eval_count", 0)
        completion_tokens = result.get("eval_count", 0)

        return (
            f"{content}\n\n"
            f"---\n"
            f"Model: {model} | Tokens: {prompt_tokens}+{completion_tokens}"
        )
    except Exception as e:
        return f"Error chatting with {model}: {e}"


@mcp.tool()
async def generate(
    model: str,
    prompt: str,
    system: str | None = None,
    temperature: float | None = None,
) -> str:
    """
    Generate a text completion from an Ollama model.

    Args:
        model: Model name to use
        prompt: The prompt text
        system: Optional system prompt
        temperature: Sampling temperature (0.0-2.0)
    """
    try:
        request_data: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            request_data["system"] = system
        if temperature is not None:
            request_data["options"] = {"temperature": temperature}

        result = await _ollama_post("/api/generate", request_data, timeout=300.0)

        response_text = result.get("response", "")
        eval_count = result.get("eval_count", 0)
        eval_duration = result.get("eval_duration", 0)
        tokens_per_sec = (
            round(eval_count / (eval_duration / 1e9), 1) if eval_duration > 0 else 0
        )

        return (
            f"{response_text}\n\n"
            f"---\n"
            f"Model: {model} | Tokens: {eval_count} | Speed: {tokens_per_sec} tok/s"
        )
    except Exception as e:
        return f"Error generating with {model}: {e}"


@mcp.tool()
async def chat_structured(
    model: str,
    message: str,
    schema: dict,
    system: str | None = None,
) -> str:
    """
    Chat with structured JSON output enforced by a JSON Schema.

    Args:
        model: Model name to use
        message: The user message
        schema: JSON Schema that the response must conform to
        system: Optional system prompt
    """
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})

        result = await _api_post(
            "/api/chat/structured",
            {"model": model, "messages": messages, "format": schema},
            timeout=300.0,
        )

        response = result.get("response", {})
        valid = result.get("schema_valid", False)
        errors = result.get("validation_errors", [])

        output = f"**Response:**\n```json\n{json.dumps(response, indent=2)}\n```\n"
        output += f"\nSchema valid: {'Yes' if valid else 'No'}"
        if errors:
            output += f"\nValidation errors: {', '.join(errors)}"

        return output
    except Exception as e:
        return f"Error with structured chat: {e}"


@mcp.tool()
async def get_health() -> str:
    """Get the health status of the Ollama monitoring service."""
    try:
        data = await _api_get("/api/health")
        status = data.get("status", "unknown")
        uptime = data.get("uptime_seconds", 0)
        db_connected = data.get("database_connected", False)

        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)

        return (
            f"**Service Status:** {status}\n"
            f"**Uptime:** {hours}h {minutes}m\n"
            f"**Database:** {'Connected' if db_connected else 'Disconnected'}"
        )
    except Exception as e:
        return f"Error checking health: {e}"


@mcp.tool()
async def get_metrics() -> str:
    """Get current performance metrics including tokens, latency, and error rates."""
    try:
        data = await _api_get("/api/stats/enhanced")
        return (
            f"**Performance Metrics:**\n"
            f"- Total requests: {data.get('total_requests', 0)}\n"
            f"- Total tokens: {data.get('total_tokens', 0)}\n"
            f"- Tokens/sec: {data.get('tokens_per_second', 0)}\n"
            f"- Error rate: {data.get('error_rate_percent', 0)}%\n"
            f"- Latency P50: {data.get('latency_p50_ms', 0)}ms\n"
            f"- Latency P95: {data.get('latency_p95_ms', 0)}ms\n"
            f"- Queue depth: {data.get('queue_depth', 0)}\n"
            f"- Active models: {', '.join(data.get('active_models', []))}"
        )
    except Exception as e:
        return f"Error getting metrics: {e}"


@mcp.tool()
async def get_gpu_status() -> str:
    """Get GPU utilization, VRAM usage, and temperature."""
    try:
        data = await _api_get("/api/gpu")
        if not data.get("available", False):
            return "No GPU available."

        return (
            f"**GPU Status:**\n"
            f"- GPU count: {data.get('gpu_count', 0)}\n"
            f"- VRAM: {data.get('used_vram_gb', 0):.1f} / {data.get('total_vram_gb', 0):.1f} GB\n"
            f"- GPU utilization: {data.get('avg_gpu_utilization_percent', 0):.0f}%\n"
            f"- Memory utilization: {data.get('avg_memory_utilization_percent', 0):.0f}%\n"
            f"- Temperature: {data.get('avg_temperature_celsius', 0):.0f}°C"
        )
    except Exception as e:
        return f"Error getting GPU status: {e}"


@mcp.tool()
async def get_request_logs(limit: int = 10) -> str:
    """
    Get recent request logs showing prompts, models, and performance.

    Args:
        limit: Number of recent logs to return (default 10, max 50)
    """
    try:
        limit = min(limit, 50)
        data = await _api_get(f"/api/logs?limit={limit}")
        logs = data.get("logs", [])

        if not logs:
            return "No request logs found."

        lines = [f"**Recent {len(logs)} requests:**\n"]
        for log in logs:
            model = log.get("model", "unknown")
            status = log.get("status", "unknown")
            latency = log.get("latency", 0)
            tokens = log.get("tokens", 0)
            prompt = (log.get("prompt_text") or "")[:80]
            icon = "OK" if status == "success" else "ERR"
            lines.append(
                f"[{icon}] {model} | {latency}ms | {tokens} tokens | {prompt}..."
            )

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting logs: {e}"


@mcp.tool()
async def get_router_status() -> str:
    """Get the smart model router configuration and routing statistics."""
    try:
        config = await _api_get("/api/router/config")
        stats = await _api_get("/api/router/stats")

        if not config.get("enabled", False):
            return "Smart model router is not enabled."

        rules_text = ""
        for rule in config.get("rules", []):
            models = ", ".join(rule.get("models", []))
            keywords = ", ".join(rule.get("keywords", [])[:5])
            rules_text += f"\n  - {rule['task_type']}: [{models}] (keywords: {keywords}...)"

        stats_text = ""
        if stats.get("total_decisions", 0) > 0:
            stats_text = (
                f"\n\n**Routing Stats:**\n"
                f"- Total decisions: {stats['total_decisions']}\n"
                f"- Fallback rate: {stats.get('fallback_rate', 0)}%\n"
                f"- By model: {json.dumps(stats.get('by_model', {}))}\n"
                f"- By task type: {json.dumps(stats.get('by_task_type', {}))}"
            )

        return (
            f"**Router Config:**\n"
            f"- Strategy: {config.get('strategy', 'priority')}\n"
            f"- Default model: {config.get('default_model', 'N/A')}\n"
            f"- Rules:{rules_text}"
            f"{stats_text}"
        )
    except Exception as e:
        return f"Error getting router status: {e}"


# ============================================================================
# MCP Resources
# ============================================================================


@mcp.resource("ollama://models")
async def models_resource() -> str:
    """Currently available Ollama models."""
    return await list_models()


@mcp.resource("ollama://health")
async def health_resource() -> str:
    """Current service health status."""
    return await get_health()


# ============================================================================
# Entry Point
# ============================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

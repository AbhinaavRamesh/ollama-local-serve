"""
FastAPI monitoring server for Ollama Local Serve.

Provides REST API endpoints for querying metrics, logs, and service health.
"""

import logging
import os
import uuid
import time
import json
import httpx
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Literal, AsyncGenerator

from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from ollama_local_serve.api.models import (
    HealthResponse,
    CurrentStatsResponse,
    HistoryResponse,
    HistoryDataPoint,
    LogsResponse,
    RequestLogEntry,
    ModelsResponse,
    ModelStats,
    ConfigResponse,
    ConfigUpdateRequest,
    ErrorResponse,
    ChatRequest,
    ChatResponse,
)
from ollama_local_serve.api.dependencies import (
    DatabaseManager,
    DatabaseConfig,
    get_database_manager,
    init_database,
    close_database,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifespan
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Ollama monitoring API server")
    try:
        await init_database()
        logger.info("Database connections established")
    except Exception as e:
        logger.warning(f"Failed to connect to database on startup: {e}")
        # Continue anyway - endpoints will handle missing connection

    yield

    # Shutdown
    logger.info("Shutting down Ollama monitoring API server")
    await close_database()


# ============================================================================
# FastAPI Application
# ============================================================================


def create_app(
    title: str = "Ollama Monitoring API",
    version: str = "0.1.0",
    cors_origins: Optional[list] = None,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        title: API title
        version: API version
        cors_origins: List of allowed CORS origins

    Returns:
        Configured FastAPI application
    """
    application = FastAPI(
        title=title,
        description="REST API for monitoring Ollama service metrics and logs",
        version=version,
        lifespan=lifespan,
        responses={
            500: {"model": ErrorResponse, "description": "Internal Server Error"},
        },
    )

    # Configure CORS
    origins = cors_origins or [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*",  # Allow all for development
    ]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    _register_routes(application)

    return application


def _register_routes(app: FastAPI) -> None:
    """Register all API routes."""

    # ========================================================================
    # Health Check
    # ========================================================================

    @app.get(
        "/api/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Service health check",
        description="Check the health status of the monitoring service and database connections.",
    )
    async def health_check():
        """Check service health."""
        try:
            db = get_database_manager()
            is_connected = db.is_connected

            if is_connected:
                status = "healthy"
            else:
                status = "degraded"

            return HealthResponse(
                status=status,
                uptime_seconds=db.uptime_seconds if db else 0,
                database_connected=is_connected,
                details={
                    "exporter_type": db.config.exporter_type if db else "none",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthResponse(
                status="unhealthy",
                uptime_seconds=0,
                database_connected=False,
                details={"error": str(e)},
            )

    # ========================================================================
    # Current Stats
    # ========================================================================

    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

    @app.get(
        "/api/stats/current",
        response_model=CurrentStatsResponse,
        tags=["Statistics"],
        summary="Get current metrics",
        description="Returns the latest metrics snapshot including tokens, latency, and errors.",
    )
    async def get_current_stats():
        """Get current metrics snapshot."""
        try:
            db = get_database_manager()
            stats = await db.get_current_stats()

            # Get actual models count from Ollama
            models_count = 0
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{OLLAMA_HOST}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        models_count = len(data.get("models", []))
            except Exception as e:
                logger.warning(f"Could not fetch models count: {e}")

            return CurrentStatsResponse(
                tokens_total=stats["tokens_total"],
                tokens_per_sec=stats["tokens_per_sec"],
                uptime_hours=stats["uptime_hours"],
                error_count=stats["error_count"],
                request_count=stats["request_count"],
                avg_latency_ms=stats["avg_latency_ms"],
                models_available=models_count,
                timestamp=stats["timestamp"],
            )

        except Exception as e:
            logger.error(f"Error getting current stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # History
    # ========================================================================

    @app.get(
        "/api/stats/history",
        response_model=HistoryResponse,
        tags=["Statistics"],
        summary="Get metrics history",
        description="Returns time-series data for charting over specified time range.",
    )
    async def get_stats_history(
        time_range: Literal["1h", "6h", "24h"] = Query(
            "1h", description="Time range to query"
        ),
        granularity: Literal["1m", "5m", "1h"] = Query(
            "1m", description="Data granularity"
        ),
    ):
        """Get time-series history data."""
        try:
            db = get_database_manager()
            data = await db.get_history(time_range=time_range, granularity=granularity)

            data_points = [
                HistoryDataPoint(
                    timestamp=point["timestamp"],
                    tokens_total=point["tokens_total"],
                    latency_ms=point["latency_ms"],
                    throughput=point["throughput"],
                    error_count=point["error_count"],
                )
                for point in data
            ]

            return HistoryResponse(
                time_range=time_range,
                granularity=granularity,
                data=data_points,
            )

        except Exception as e:
            logger.error(f"Error getting history: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # Request Logs
    # ========================================================================

    @app.get(
        "/api/stats/logs",
        response_model=LogsResponse,
        tags=["Logs"],
        summary="Get request logs",
        description="Returns paginated request logs with optional filtering.",
    )
    async def get_request_logs(
        limit: int = Query(100, ge=1, le=1000, description="Maximum logs to return"),
        offset: int = Query(0, ge=0, description="Offset for pagination"),
        status: Optional[Literal["success", "error"]] = Query(
            None, description="Filter by status"
        ),
        model: Optional[str] = Query(None, description="Filter by model name"),
    ):
        """Get paginated request logs."""
        try:
            db = get_database_manager()
            result = await db.get_logs(
                limit=limit, offset=offset, status=status, model=model
            )

            logs = [
                RequestLogEntry(
                    request_id=log["request_id"],
                    timestamp=log["timestamp"],
                    model=log["model"],
                    tokens=log["tokens"],
                    latency=log["latency"],
                    status=log["status"],
                    error_message=log.get("error_message"),
                    prompt_text=log.get("prompt_text"),
                    response_text=log.get("response_text"),
                    prompt_tokens=log.get("prompt_tokens"),
                    total_tokens=log.get("total_tokens"),
                    client_ip=log.get("client_ip"),
                    user_agent=log.get("user_agent"),
                    origin=log.get("origin"),
                    referer=log.get("referer"),
                )
                for log in result["logs"]
            ]

            return LogsResponse(
                total=result["total"],
                offset=offset,
                limit=limit,
                logs=logs,
            )

        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # Model Statistics
    # ========================================================================

    @app.get(
        "/api/models",
        response_model=ModelsResponse,
        tags=["Models"],
        summary="Get model statistics",
        description="Returns statistics for each model including request counts and latency.",
    )
    async def get_models():
        """Get model statistics."""
        try:
            db = get_database_manager()
            stats = await db.get_model_stats()

            models = [
                ModelStats(
                    model_name=stat["model_name"],
                    requests_count=stat["requests_count"],
                    tokens_generated=stat["tokens_generated"],
                    avg_latency_ms=stat["avg_latency_ms"],
                    error_count=stat["error_count"],
                    last_used=stat.get("last_used"),
                )
                for stat in stats
            ]

            return ModelsResponse(
                models=models,
                total_models=len(models),
            )

        except Exception as e:
            logger.error(f"Error getting model stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # Configuration (Optional)
    # ========================================================================

    @app.get(
        "/api/config",
        response_model=ConfigResponse,
        tags=["Configuration"],
        summary="Get current configuration",
        description="Returns the current monitoring configuration.",
    )
    async def get_config():
        """Get current configuration."""
        try:
            db = get_database_manager()
            config = db.config

            return ConfigResponse(
                enable_instrumentation=True,  # If API is running, instrumentation is on
                exporter_type=config.exporter_type,
                metrics_export_interval=5,  # Default
                clickhouse_host=config.clickhouse_host
                if config.exporter_type in ("clickhouse", "both")
                else None,
                postgres_host=config.postgres_host
                if config.exporter_type in ("postgres", "both")
                else None,
            )

        except Exception as e:
            logger.error(f"Error getting config: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(
        "/api/config",
        response_model=ConfigResponse,
        tags=["Configuration"],
        summary="Update configuration",
        description="Update runtime configuration (limited options available).",
    )
    async def update_config(config_update: ConfigUpdateRequest):
        """Update configuration (limited)."""
        # Note: Most config changes require restart
        # This endpoint is mainly for future extensibility
        try:
            db = get_database_manager()
            current_config = db.config

            return ConfigResponse(
                enable_instrumentation=config_update.enable_instrumentation
                if config_update.enable_instrumentation is not None
                else True,
                exporter_type=config_update.exporter_type
                if config_update.exporter_type is not None
                else current_config.exporter_type,
                metrics_export_interval=config_update.metrics_export_interval
                if config_update.metrics_export_interval is not None
                else 5,
                clickhouse_host=current_config.clickhouse_host,
                postgres_host=current_config.postgres_host,
            )

        except Exception as e:
            logger.error(f"Error updating config: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # Chat Endpoint
    # ========================================================================

    async def log_chat_request(
        request_id: str,
        model: str,
        prompt: str,
        response: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        status: str,
        error_message: Optional[str] = None,
        client_ip: str = "",
        user_agent: str = "",
        origin: str = "",
        referer: str = "",
    ):
        """Log a chat request to the database."""
        try:
            db = get_database_manager()
            if db.config.exporter_type in ("clickhouse", "both") and db._clickhouse_client:
                db._clickhouse_client.execute(
                    """
                    INSERT INTO request_logs
                    (request_id, timestamp, model, prompt_text, response_text,
                     prompt_tokens, tokens_generated, total_tokens, latency_ms, status, error_message,
                     client_ip, user_agent, origin, referer)
                    VALUES
                    """,
                    [(
                        request_id,
                        datetime.utcnow(),
                        model,
                        prompt[:10000],  # Limit prompt size
                        response[:50000],  # Limit response size
                        prompt_tokens,
                        completion_tokens,
                        prompt_tokens + completion_tokens,
                        latency_ms,
                        status,
                        error_message,
                        client_ip[:255],
                        user_agent[:500],
                        origin[:500],
                        referer[:500],
                    )],
                )
        except Exception as e:
            logger.error(f"Failed to log chat request: {e}")

    @app.post(
        "/api/chat",
        tags=["Chat"],
        summary="Chat with Ollama (streaming)",
        description="Send a prompt to Ollama and receive a streaming response.",
    )
    async def chat_stream(chat_request: ChatRequest, request: Request):
        """Stream chat response from Ollama."""
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Extract client info
        client_ip = request.client.host if request.client else ""
        # Check for forwarded IP (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        user_agent = request.headers.get("User-Agent", "")
        origin = request.headers.get("Origin", "")
        referer = request.headers.get("Referer", "")

        async def generate() -> AsyncGenerator[str, None]:
            full_response = ""
            prompt_tokens = 0
            completion_tokens = 0
            error_occurred = False
            error_message = None

            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    ollama_request = {
                        "model": chat_request.model,
                        "prompt": chat_request.prompt,
                        "stream": True,
                    }
                    if chat_request.system:
                        ollama_request["system"] = chat_request.system
                    if chat_request.temperature is not None:
                        ollama_request["options"] = {"temperature": chat_request.temperature}

                    async with client.stream(
                        "POST",
                        f"{OLLAMA_HOST}/api/generate",
                        json=ollama_request,
                    ) as response:
                        response.raise_for_status()

                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    data = json.loads(line)

                                    # Extract token from response
                                    if "response" in data:
                                        token = data["response"]
                                        full_response += token
                                        # Send token as SSE event
                                        yield f"data: {json.dumps({'token': token, 'request_id': request_id})}\n\n"

                                    # Check if done
                                    if data.get("done"):
                                        prompt_tokens = data.get("prompt_eval_count", 0)
                                        completion_tokens = data.get("eval_count", 0)

                                        # Send final stats
                                        latency_ms = int((time.time() - start_time) * 1000)
                                        yield f"data: {json.dumps({'done': True, 'request_id': request_id, 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'latency_ms': latency_ms})}\n\n"

                                except json.JSONDecodeError:
                                    continue

            except httpx.HTTPStatusError as e:
                error_occurred = True
                error_message = str(e)
                yield f"data: {json.dumps({'error': error_message, 'request_id': request_id})}\n\n"
            except Exception as e:
                error_occurred = True
                error_message = str(e)
                yield f"data: {json.dumps({'error': error_message, 'request_id': request_id})}\n\n"
            finally:
                # Log the request
                latency_ms = int((time.time() - start_time) * 1000)
                await log_chat_request(
                    request_id=request_id,
                    model=chat_request.model,
                    prompt=chat_request.prompt,
                    response=full_response,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    status="error" if error_occurred else "success",
                    error_message=error_message,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    origin=origin,
                    referer=referer,
                )

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id,
            },
        )

    @app.get(
        "/api/ollama/models",
        tags=["Chat"],
        summary="List available Ollama models",
        description="Get list of models available in Ollama.",
    )
    async def list_ollama_models():
        """Get available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{OLLAMA_HOST}/api/tags")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(
        "/api/ollama/pull",
        tags=["Chat"],
        summary="Pull a model from Ollama registry",
        description="Download a model from the Ollama model library.",
    )
    async def pull_ollama_model(request: Request):
        """Pull a model with streaming progress."""
        body = await request.json()
        model_name = body.get("name", "")

        if not model_name:
            raise HTTPException(status_code=400, detail="Model name is required")

        async def generate():
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        f"{OLLAMA_HOST}/api/pull",
                        json={"name": model_name, "stream": True},
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line:
                                yield f"data: {line}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    @app.delete(
        "/api/ollama/models/{model_name:path}",
        tags=["Chat"],
        summary="Delete a model",
        description="Remove a model from Ollama.",
    )
    async def delete_ollama_model(model_name: str):
        """Delete a model."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{OLLAMA_HOST}/api/delete",
                    json={"name": model_name}
                )
                response.raise_for_status()
                return {"status": "deleted", "model": model_name}
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(
        "/api/ollama/library",
        tags=["Chat"],
        summary="Search Ollama model library",
        description="Search for models in the Ollama library.",
    )
    async def search_ollama_library(q: str = Query("", description="Search query")):
        """Search the Ollama library (returns popular models)."""
        # Ollama doesn't have a public search API, so we return a curated list
        popular_models = [
            {"name": "llama3.2", "description": "Meta's Llama 3.2 - latest and most capable", "size": "1B-90B"},
            {"name": "llama3.1", "description": "Meta's Llama 3.1 - powerful open model", "size": "8B-405B"},
            {"name": "gemma3:1b", "description": "Google's Gemma 3 - compact 1B model", "size": "1B"},
            {"name": "gemma3:4b", "description": "Google's Gemma 3 - balanced 4B model", "size": "4B"},
            {"name": "gemma2", "description": "Google's Gemma 2 model", "size": "2B-27B"},
            {"name": "nemotron-mini", "description": "NVIDIA Nemotron Mini - efficient small model", "size": "4B"},
            {"name": "mistral", "description": "Mistral AI's 7B model - fast and efficient", "size": "7B"},
            {"name": "mixtral", "description": "Mistral's mixture of experts model", "size": "8x7B"},
            {"name": "phi3", "description": "Microsoft's small but capable model", "size": "3.8B"},
            {"name": "phi3:mini", "description": "Microsoft Phi-3 Mini", "size": "3.8B"},
            {"name": "qwen2.5", "description": "Alibaba's Qwen 2.5 model", "size": "0.5B-72B"},
            {"name": "qwen2.5:1.5b", "description": "Alibaba's Qwen 2.5 - tiny variant", "size": "1.5B"},
            {"name": "codellama", "description": "Meta's code-specialized Llama", "size": "7B-34B"},
            {"name": "deepseek-coder", "description": "DeepSeek's coding model", "size": "1.3B-33B"},
            {"name": "deepseek-coder-v2", "description": "DeepSeek Coder V2 - improved coding", "size": "16B-236B"},
            {"name": "starcoder2", "description": "BigCode's StarCoder 2", "size": "3B-15B"},
            {"name": "tinyllama", "description": "Tiny but fast for testing", "size": "1.1B"},
            {"name": "neural-chat", "description": "Intel's neural chat model", "size": "7B"},
            {"name": "starling-lm", "description": "Berkeley's Starling model", "size": "7B"},
            {"name": "dolphin-mixtral", "description": "Uncensored Mixtral variant", "size": "8x7B"},
            {"name": "wizard-vicuna", "description": "Wizard + Vicuna combined", "size": "13B"},
        ]

        if q:
            q_lower = q.lower()
            filtered = [m for m in popular_models if q_lower in m["name"].lower() or q_lower in m["description"].lower()]
            return {"models": filtered}
        return {"models": popular_models}

    # ========================================================================
    # Model Repository Endpoints
    # ========================================================================

    @app.get(
        "/api/models/repository",
        tags=["Models"],
        summary="Get model repository",
        description="Get all models from the repository with preferences and stats.",
    )
    async def get_model_repository(
        category: Optional[str] = Query(None, description="Filter by category"),
        favorites_only: bool = Query(False, description="Only show favorites"),
        installed_only: bool = Query(False, description="Only show installed"),
    ):
        """Get models from the repository."""
        db = get_database_manager()
        result = await db.get_model_repository(
            category=category,
            favorites_only=favorites_only,
            installed_only=installed_only,
        )
        return result

    @app.get(
        "/api/models/repository/{model_name:path}",
        tags=["Models"],
        summary="Get model details",
        description="Get details for a specific model.",
    )
    async def get_model_details(model_name: str):
        """Get a specific model from the repository."""
        db = get_database_manager()
        model = await db.get_model_by_name(model_name)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return model

    @app.post(
        "/api/models/repository",
        tags=["Models"],
        summary="Add model to repository",
        description="Add a new model to the repository.",
    )
    async def create_model_in_repository(request: Request):
        """Create a new model entry."""
        body = await request.json()
        db = get_database_manager()
        result = await db.create_model_entry(
            model_name=body.get("model_name"),
            display_name=body.get("display_name"),
            description=body.get("description"),
            category=body.get("category", "general"),
            size_label=body.get("size_label"),
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create model entry")
        return result

    @app.put(
        "/api/models/repository/{model_name:path}",
        tags=["Models"],
        summary="Update model preferences",
        description="Update model preferences like favorite, default, etc.",
    )
    async def update_model_in_repository(model_name: str, request: Request):
        """Update a model entry."""
        body = await request.json()
        db = get_database_manager()
        result = await db.update_model_entry(
            model_name=model_name,
            display_name=body.get("display_name"),
            description=body.get("description"),
            category=body.get("category"),
            is_favorite=body.get("is_favorite"),
            is_default=body.get("is_default"),
            is_installed=body.get("is_installed"),
            size_bytes=body.get("size_bytes"),
        )
        if not result:
            raise HTTPException(status_code=404, detail="Model not found")
        return result

    @app.delete(
        "/api/models/repository/{model_name:path}",
        tags=["Models"],
        summary="Remove model from repository",
        description="Remove a model from the repository.",
    )
    async def delete_model_from_repository(model_name: str):
        """Delete a model entry from the repository."""
        db = get_database_manager()
        success = await db.delete_model_entry(model_name)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete model")
        return {"status": "deleted", "model": model_name}

    @app.post(
        "/api/models/repository/sync",
        tags=["Models"],
        summary="Sync installed models",
        description="Sync repository with currently installed Ollama models.",
    )
    async def sync_model_repository():
        """Sync repository with installed models."""
        try:
            # Get installed models from Ollama
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{OLLAMA_HOST}/api/tags")
                response.raise_for_status()
                data = response.json()
                installed_models = [m["name"] for m in data.get("models", [])]

            # Sync with repository
            db = get_database_manager()
            await db.sync_installed_models(installed_models)

            return {
                "status": "synced",
                "installed_count": len(installed_models),
                "models": installed_models,
            }
        except Exception as e:
            logger.error(f"Failed to sync models: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(
        "/api/models/repository/{model_name:path}/favorite",
        tags=["Models"],
        summary="Toggle favorite",
        description="Toggle favorite status for a model.",
    )
    async def toggle_model_favorite(model_name: str):
        """Toggle favorite status."""
        db = get_database_manager()
        model = await db.get_model_by_name(model_name)

        if not model:
            # Create entry if doesn't exist
            await db.create_model_entry(model_name=model_name)
            model = await db.get_model_by_name(model_name)

        new_favorite = not model.get("is_favorite", False)
        result = await db.update_model_entry(model_name, is_favorite=new_favorite)
        return result

    # ========================================================================
    # Data Management Endpoints
    # ========================================================================

    @app.get(
        "/api/data/summary",
        tags=["Data Management"],
        summary="Get data summary",
        description="Get summary of data stored in databases.",
    )
    async def get_data_summary():
        """Get summary of data in databases."""
        db = get_database_manager()
        return await db.get_data_summary()

    @app.delete(
        "/api/data/metrics",
        tags=["Data Management"],
        summary="Clear all metrics",
        description="Clear all metrics data from the database.",
    )
    async def clear_metrics():
        """Clear all metrics data."""
        db = get_database_manager()
        success = await db.clear_metrics()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear metrics")
        return {"status": "cleared", "type": "metrics"}

    @app.delete(
        "/api/data/logs",
        tags=["Data Management"],
        summary="Clear all request logs",
        description="Clear all request logs from the database.",
    )
    async def clear_logs():
        """Clear all request logs."""
        db = get_database_manager()
        success = await db.clear_logs()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear logs")
        return {"status": "cleared", "type": "logs"}

    @app.delete(
        "/api/data/all",
        tags=["Data Management"],
        summary="Clear all data",
        description="Clear all metrics, logs, and reset model statistics.",
    )
    async def clear_all_data():
        """Clear all data from databases."""
        db = get_database_manager()
        results = await db.clear_all_data()
        return {
            "status": "cleared",
            "results": results,
        }

    # ========================================================================
    # Error Handlers
    # ========================================================================

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "message": exc.detail,
                "details": None,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": type(exc).__name__,
                "message": str(exc),
                "details": None,
            },
        )


# Create default app instance
app = create_app()


# ============================================================================
# CLI Entry Point
# ============================================================================


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """
    Run the API server using uvicorn.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
        log_level: Logging level
    """
    import uvicorn

    uvicorn.run(
        "ollama_local_serve.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    # Allow running directly: python -m ollama_local_serve.api.server
    import argparse

    parser = argparse.ArgumentParser(description="Ollama Monitoring API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Logging level")

    args = parser.parse_args()

    run_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )

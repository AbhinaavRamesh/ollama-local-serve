"""
FastAPI monitoring server for Ollama Local Serve.

Provides REST API endpoints for querying metrics, logs, and service health.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Literal

from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

            return CurrentStatsResponse(
                tokens_total=stats["tokens_total"],
                tokens_per_sec=stats["tokens_per_sec"],
                uptime_hours=stats["uptime_hours"],
                error_count=stats["error_count"],
                request_count=stats["request_count"],
                avg_latency_ms=stats["avg_latency_ms"],
                models_available=stats["models_available"],
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

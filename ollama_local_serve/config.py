"""
Configuration management for Ollama Local Serve using Pydantic.

This module provides configuration classes for network settings,
instrumentation, database connections, and API server configuration.
All settings can be loaded from environment variables.
"""

from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NetworkConfig(BaseSettings):
    """
    Network configuration for Ollama server.

    All settings can be loaded from environment variables with the OLLAMA_ prefix.

    Attributes:
        host: The host address to bind to. Use '0.0.0.0' for LAN accessibility.
        port: The port number to listen on. Default is 11434 (Ollama default).
        timeout: Connection timeout in seconds.
        max_retries: Maximum number of connection retry attempts.

    Example:
        ```python
        # Load from environment variables
        config = NetworkConfig()

        # Or provide explicit values
        config = NetworkConfig(host="0.0.0.0", port=11434)
        ```
    """

    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="Host address to bind to")
    port: int = Field(default=11434, ge=1, le=65535, description="Port number")
    timeout: int = Field(default=30, gt=0, description="Connection timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")

    @computed_field
    @property
    def base_url(self) -> str:
        """Get the base URL for the Ollama service."""
        return f"http://{self.host}:{self.port}"

    @computed_field
    @property
    def api_url(self) -> str:
        """Get the API URL for the Ollama service."""
        return f"{self.base_url}/api"

    def get_connection_url(self, localhost_fallback: bool = False) -> str:
        """
        Get the connection URL for clients.

        Args:
            localhost_fallback: If True and host is '0.0.0.0', return localhost URL.

        Returns:
            The connection URL string.
        """
        if localhost_fallback and self.host == "0.0.0.0":
            return f"http://localhost:{self.port}"
        return self.base_url


class InstrumentationConfig(BaseSettings):
    """
    Configuration for metrics instrumentation and exporters.

    Attributes:
        enable_instrumentation: Whether to enable metrics collection.
        exporter_type: Type of metrics exporter to use.
        metrics_export_interval: Interval in seconds for batch metric export.
        service_name: Service name for OTEL metrics.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enable_instrumentation: bool = Field(
        default=False,
        alias="ENABLE_INSTRUMENTATION",
        description="Enable metrics collection",
    )
    exporter_type: Literal["clickhouse", "postgres", "both", "none"] = Field(
        default="none",
        alias="EXPORTER_TYPE",
        description="Type of metrics exporter",
    )
    metrics_export_interval: int = Field(
        default=5,
        gt=0,
        alias="METRICS_EXPORT_INTERVAL",
        description="Export interval in seconds",
    )
    service_name: str = Field(
        default="ollama-local-serve",
        alias="SERVICE_NAME",
        description="Service name for metrics",
    )


class ClickHouseConfig(BaseSettings):
    """
    ClickHouse database configuration.

    Attributes:
        host: ClickHouse server host.
        port: ClickHouse native protocol port.
        http_port: ClickHouse HTTP interface port.
        database: Database name.
        user: Database user.
        password: Database password.
        secure: Whether to use secure connection.
        connect_timeout: Connection timeout in seconds.
    """

    model_config = SettingsConfigDict(
        env_prefix="CLICKHOUSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="ClickHouse server host")
    port: int = Field(default=9000, description="Native protocol port")
    http_port: int = Field(default=8123, description="HTTP interface port")
    database: str = Field(default="ollama_metrics", description="Database name")
    user: str = Field(default="default", description="Database user")
    password: str = Field(default="", description="Database password")
    secure: bool = Field(default=False, description="Use secure connection")
    connect_timeout: int = Field(default=10, gt=0, description="Connection timeout")

    @computed_field
    @property
    def connection_url(self) -> str:
        """Get the ClickHouse connection URL."""
        protocol = "https" if self.secure else "http"
        auth = f"{self.user}:{self.password}@" if self.password else f"{self.user}@"
        return f"{protocol}://{auth}{self.host}:{self.http_port}/{self.database}"


class PostgresConfig(BaseSettings):
    """
    PostgreSQL database configuration.

    Attributes:
        host: PostgreSQL server host.
        port: PostgreSQL port.
        database: Database name.
        user: Database user.
        password: Database password.
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections.
        use_timescale: Whether to use TimescaleDB features.
        ssl_mode: SSL mode for connection.
    """

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="PostgreSQL server host")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(default="ollama_metrics", description="Database name")
    user: str = Field(default="ollama", description="Database user")
    password: str = Field(default="ollama", description="Database password")
    pool_size: int = Field(default=5, ge=1, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Max overflow connections")
    use_timescale: bool = Field(
        default=True,
        alias="USE_TIMESCALE",
        description="Use TimescaleDB features",
    )
    ssl_mode: str = Field(default="prefer", description="SSL mode")

    @computed_field
    @property
    def connection_url(self) -> str:
        """Get the async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    @computed_field
    @property
    def sync_connection_url(self) -> str:
        """Get the sync PostgreSQL connection URL."""
        return (
            f"postgresql://{self.user}:{self.password}@" f"{self.host}:{self.port}/{self.database}"
        )


class APIConfig(BaseSettings):
    """
    FastAPI server configuration.

    Attributes:
        host: API server host.
        port: API server port.
        workers: Number of worker processes.
        log_level: Logging level.
        cors_origins: Allowed CORS origins.
        debug: Enable debug mode.
        reload: Enable hot reload.
        api_key: Optional API key for authentication.
    """

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, ge=1, le=65535, description="API server port")
    workers: int = Field(default=4, ge=1, description="Number of workers")
    log_level: str = Field(default="info", description="Logging level")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated CORS origins",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Enable hot reload")
    api_key: str | None = Field(default=None, description="API key for auth")

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


class LoggingConfig(BaseSettings):
    """
    Logging configuration.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: Log format (json or text).
    """

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    level: str = Field(default="INFO", description="Log level")
    format: Literal["json", "text"] = Field(default="json", description="Log format")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return upper_v


class AppConfig(BaseSettings):
    """
    Unified application configuration.

    Combines all configuration sections into a single class for convenience.
    All settings are loaded from environment variables and .env file.

    Example:
        ```python
        from ollama_local_serve.config import AppConfig

        # Load all configuration
        config = AppConfig()

        # Access nested configs
        print(config.network.base_url)
        print(config.clickhouse.connection_url)
        print(config.api.cors_origins_list)
        ```
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nested configurations are created as computed fields
    @computed_field
    @property
    def network(self) -> NetworkConfig:
        """Get network configuration."""
        return NetworkConfig()

    @computed_field
    @property
    def instrumentation(self) -> InstrumentationConfig:
        """Get instrumentation configuration."""
        return InstrumentationConfig()

    @computed_field
    @property
    def clickhouse(self) -> ClickHouseConfig:
        """Get ClickHouse configuration."""
        return ClickHouseConfig()

    @computed_field
    @property
    def postgres(self) -> PostgresConfig:
        """Get PostgreSQL configuration."""
        return PostgresConfig()

    @computed_field
    @property
    def api(self) -> APIConfig:
        """Get API configuration."""
        return APIConfig()

    @computed_field
    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        return LoggingConfig()


# Convenience function to get configuration
def get_config() -> AppConfig:
    """
    Get the application configuration.

    Returns:
        AppConfig instance with all settings loaded.
    """
    return AppConfig()

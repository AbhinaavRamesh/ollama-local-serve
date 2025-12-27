# Configuration Guide

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Ollama Configuration
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=120

# Instrumentation
ENABLE_INSTRUMENTATION=true
EXPORTER_TYPE=clickhouse  # clickhouse, postgres, both, none

# ClickHouse
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=ollama_metrics

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DATABASE=ollama_metrics
POSTGRES_USER=ollama
POSTGRES_PASSWORD=your_secure_password
```

## Pydantic Configuration

All configuration classes support environment variable loading:

```python
from ollama_local_serve.config import (
    NetworkConfig,
    InstrumentationConfig,
    ClickHouseConfig,
    PostgresConfig,
    APIConfig,
    AppConfig,
)

# Load from environment variables
config = AppConfig()

# Access nested configs
print(config.network.base_url)
print(config.clickhouse.connection_url)
print(config.api.cors_origins_list)
```

### NetworkConfig

Configuration for network settings (Pydantic BaseSettings).

**Attributes:**
- `host: str` - Host address (default: "0.0.0.0")
- `port: int` - Port number (default: 11434)
- `timeout: int` - Connection timeout in seconds (default: 30)
- `max_retries: int` - Maximum retry attempts (default: 3)

**Computed Properties:**
- `base_url: str` - Get the base URL
- `api_url: str` - Get the API URL

**Usage:**

```python
from ollama_local_serve.config import NetworkConfig

# Default configuration
config = NetworkConfig()

# Custom configuration
config = NetworkConfig(
    host="192.168.1.100",  # Listen on specific interface
    port=11434,             # Ollama port
    timeout=60,             # 60 second timeout
    max_retries=5           # Retry up to 5 times
)

# From environment variables
import os
os.environ['OLLAMA_HOST'] = '0.0.0.0'
os.environ['OLLAMA_PORT'] = '11434'
config = NetworkConfig()  # Loads from environment
```

### InstrumentationConfig

Enable metrics collection and reporting.

**Attributes:**
- `enable_instrumentation: bool` - Enable/disable metrics (default: False)
- `exporter_type: str` - Export destination: "clickhouse", "postgres", "both", "none" (default: "none")
- `metrics_export_interval: int` - Export interval in seconds (default: 60)

**Usage:**

```python
from ollama_local_serve.config import InstrumentationConfig

config = InstrumentationConfig(
    enable_instrumentation=True,
    exporter_type="clickhouse",
    metrics_export_interval=30  # Export metrics every 30 seconds
)
```

### ClickHouseConfig

Time-series database for metrics storage.

**Attributes:**
- `host: str` - ClickHouse host (default: "clickhouse")
- `port: int` - ClickHouse port (default: 9000)
- `database: str` - Database name (default: "ollama_metrics")
- `user: str` - Username (default: "default")
- `password: str` - Password (default: "")
- `secure: bool` - Use HTTPS (default: False)

**Usage:**

```python
from ollama_local_serve.config import ClickHouseConfig

config = ClickHouseConfig(
    host="clickhouse.example.com",
    port=9000,
    database="ollama_metrics",
    user="ollama",
    password="secure_password",
    secure=True
)

# Connection URL
print(config.connection_url)
```

### PostgresConfig

Relational database for queries and model metadata.

**Attributes:**
- `host: str` - PostgreSQL host (default: "postgres")
- `port: int` - PostgreSQL port (default: 5432)
- `database: str` - Database name (default: "ollama_metrics")
- `user: str` - Username (default: "ollama")
- `password: str` - Password (default: "ollama")
- `sslmode: str` - SSL mode: "disable", "require", "prefer" (default: "disable")

**Usage:**

```python
from ollama_local_serve.config import PostgresConfig

config = PostgresConfig(
    host="postgres.example.com",
    port=5432,
    database="ollama_metrics",
    user="ollama_user",
    password="secure_password",
    sslmode="require"
)

# Connection URL
print(config.connection_url)
```

### APIConfig

FastAPI server configuration.

**Attributes:**
- `host: str` - API server host (default: "0.0.0.0")
- `port: int` - API server port (default: 8000)
- `cors_origins: str` - CORS origins (default: "*")
- `debug: bool` - Enable debug mode (default: False)
- `reload: bool` - Auto-reload on code changes (default: False)

**Usage:**

```python
from ollama_local_serve.config import APIConfig

config = APIConfig(
    host="0.0.0.0",
    port=8000,
    cors_origins="http://localhost:3000,https://example.com",
    debug=False,
    reload=True
)

@property
def cors_origins_list(self):
    """Get CORS origins as list"""
    return config.cors_origins_list
```

### AppConfig

Top-level configuration combining all sub-configs.

**Usage:**

```python
from ollama_local_serve.config import AppConfig

# Load all config from environment variables
config = AppConfig()

# Access nested configs
print(config.network.base_url)
print(config.clickhouse.connection_url)
print(config.postgres.connection_url)
print(config.api.cors_origins_list)
print(config.instrumentation.enable_instrumentation)
```

## Environment File Examples

### Development Setup (.env)

```bash
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=30
OLLAMA_MAX_RETRIES=3

# Instrumentation
ENABLE_INSTRUMENTATION=true
EXPORTER_TYPE=both  # Use both ClickHouse and PostgreSQL

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=ollama_metrics
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=ollama_metrics
POSTGRES_USER=ollama
POSTGRES_PASSWORD=ollama

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=*
API_DEBUG=true
API_RELOAD=true
```

### Production Setup (.env)

```bash
# Ollama Configuration
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=60
OLLAMA_MAX_RETRIES=5

# Instrumentation
ENABLE_INSTRUMENTATION=true
EXPORTER_TYPE=clickhouse  # Use ClickHouse only for performance

# ClickHouse (production instance)
CLICKHOUSE_HOST=clickhouse.prod.internal
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=ollama_metrics_prod
CLICKHOUSE_USER=ollama_prod
CLICKHOUSE_PASSWORD=secure_password_here
CLICKHOUSE_SECURE=true

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://dashboard.example.com,https://api.example.com
API_DEBUG=false
API_RELOAD=false
```

### Docker Compose Setup (.env)

```bash
# Service names resolve via Docker DNS
OLLAMA_HOST=http://ollama:11434
CLICKHOUSE_HOST=clickhouse
POSTGRES_HOST=postgres

# Enable both databases
ENABLE_INSTRUMENTATION=true
EXPORTER_TYPE=both

# Database credentials match docker-compose.yml
POSTGRES_USER=ollama
POSTGRES_PASSWORD=postgres_password

# API accessible to other containers
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=*
```

## Configuration Priority

Configuration is loaded in this order (highest priority first):

1. **Command line arguments** (if applicable)
2. **Environment variables** (.env file or system env)
3. **Direct config object** (passed to OllamaService)
4. **Default values** (hardcoded in config classes)

Example:
```python
# This will override environment variables
config = NetworkConfig(host="192.168.1.100")  # Takes precedence

# This uses environment variables (if set)
config = NetworkConfig()
```

## Validating Configuration

```python
from ollama_local_serve.config import AppConfig

# Load and validate all config
config = AppConfig()

# Check key settings
print(f"Ollama URL: {config.network.base_url}")
print(f"Instrumentation enabled: {config.instrumentation.enable_instrumentation}")
print(f"Exporter: {config.instrumentation.exporter_type}")
print(f"ClickHouse: {config.clickhouse.connection_url}")
print(f"PostgreSQL: {config.postgres.connection_url}")

# Validate connections (optional - do in your code)
import asyncio

async def validate():
    # Test Ollama connection
    from ollama_local_serve import OllamaService
    async with OllamaService(config.network) as service:
        is_healthy = await service.health_check()
        print(f"Ollama healthy: {is_healthy}")

asyncio.run(validate())
```

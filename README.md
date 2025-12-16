# Ollama Local Serve

Local LLM infrastructure with a professional monitoring dashboard for distributed AI applications. Serve Ollama-powered models across your network with seamless LangChain integration, OpenTelemetry instrumentation, and real-time metrics visualization.

## Features

- **Service Management**: Easy start/stop control of Ollama server instances
- **Network Accessible**: Configure host/port for LAN accessibility
- **LangChain Integration**: Seamless integration with LangChain for remote LLM clients
- **OpenTelemetry Instrumentation**: Built-in metrics collection with OTEL support
- **Real-time Monitoring Dashboard**: Professional React dashboard with live metrics
- **Multiple Database Backends**: Export metrics to ClickHouse or PostgreSQL/TimescaleDB
- **Health Checks**: Built-in health check endpoints to monitor service status
- **Docker Ready**: Complete Docker Compose stack for production deployment
- **Async/Await**: Production-ready async patterns throughout
- **Type Hints**: Full type annotations with Pydantic configuration

## Quick Start

### Installation

```bash
# Basic installation
pip install ollama-local-serve

# With LangChain integration
pip install ollama-local-serve[langchain]

# With full monitoring stack
pip install ollama-local-serve[monitoring]

# All features
pip install ollama-local-serve[all]
```

### Prerequisites

- Python 3.12 or higher
- Ollama installed on your system ([Download Ollama](https://ollama.ai))

### Basic Usage

```python
import asyncio
from ollama_local_serve import OllamaService, NetworkConfig

async def main():
    # Create configuration for LAN accessibility
    config = NetworkConfig(
        host="0.0.0.0",  # Accessible from any network interface
        port=11434,      # Default Ollama port
        timeout=30,
        max_retries=3
    )

    # Create and start the service
    service = OllamaService(config)
    await service.start()

    # Check service health
    is_healthy = await service.health_check()
    print(f"Service is healthy: {is_healthy}")

    # Stop the service
    await service.stop()

asyncio.run(main())
```

### Using Context Manager

```python
import asyncio
from ollama_local_serve import OllamaService, NetworkConfig

async def main():
    config = NetworkConfig(host="0.0.0.0", port=11434)

    # Automatic cleanup with context manager
    async with OllamaService(config) as service:
        print(f"Service running at {service.base_url}")
        await service.health_check()
        # Service automatically stops when exiting context

asyncio.run(main())
```

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Clone the repository
git clone https://github.com/AbhinaavRamesh/ollama-local-serve.git
cd ollama-local-serve

# Initialize environment
make init

# Start all services
make up

# View the dashboard
open http://localhost:3000
```

### Available Services

| Service | Port | Description |
|---------|------|-------------|
| Ollama | 11434 | LLM inference service |
| ClickHouse | 8123, 9000 | Time-series database |
| PostgreSQL | 5432 | TimescaleDB for relational storage |
| API Server | 8000 | FastAPI monitoring API |
| Dashboard | 3000 | React monitoring dashboard |

### Make Commands

```bash
make help          # Show all available commands
make init          # Initialize environment
make up            # Start all services
make down          # Stop all services
make logs          # View logs
make health        # Check service health
make dev           # Start development environment
make clean         # Remove all containers and volumes
```

## Configuration

### Environment Variables

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

### Pydantic Configuration

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

## Monitoring & Instrumentation

### Enable Instrumentation

```python
from ollama_local_serve import OllamaService, NetworkConfig

config = NetworkConfig(
    host="0.0.0.0",
    port=11434,
    enable_instrumentation=True,
    exporter_type="clickhouse",  # or "postgres", "both"
    metrics_export_interval=5,
)

async with OllamaService(config) as service:
    # Metrics are automatically collected
    response = await service.generate("llama2", "Hello, world!")
```

### Available Metrics

- `ollama_requests_total` - Total number of requests
- `ollama_tokens_generated_total` - Total tokens generated
- `ollama_errors_total` - Total errors
- `ollama_request_latency_ms` - Request latency histogram

### API Endpoints

The monitoring API provides:

```
GET /api/health          - Health check
GET /api/stats/current   - Current statistics
GET /api/stats/history   - Historical metrics
GET /api/stats/logs      - Request logs
GET /api/models          - Available models
```

## LangChain Integration

```python
from ollama_local_serve import create_langchain_client, NetworkConfig

# Connect to a local or remote Ollama service
llm = create_langchain_client(
    base_url="http://192.168.1.100:11434",
    model="llama2",
    temperature=0.7
)

response = llm.invoke("What is the meaning of life?")
print(response)
```

## Project Structure

```
ollama-local-serve/
├── ollama_local_serve/          # Python package
│   ├── __init__.py
│   ├── config.py                # Pydantic configuration
│   ├── service.py               # OllamaService class
│   ├── client.py                # LangChain client
│   ├── exceptions.py            # Custom exceptions
│   ├── api/                     # FastAPI server
│   │   ├── server.py
│   │   ├── models.py
│   │   └── dependencies.py
│   ├── instrumentation/         # OTEL instrumentation
│   │   ├── metrics_provider.py
│   │   └── tracer.py
│   └── exporters/               # Database exporters
│       ├── base.py
│       ├── clickhouse_exporter.py
│       └── postgres_exporter.py
├── frontend/                    # React dashboard
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── utils/
│   ├── package.json
│   └── Dockerfile
├── schemas/                     # Database schemas
│   ├── clickhouse_init.sql
│   └── postgres_init.sql
├── docker-compose.yml           # Production stack
├── docker-compose.dev.yml       # Development overrides
├── Dockerfile                   # API Dockerfile
├── Makefile                     # Convenience commands
├── pyproject.toml               # Python project config
└── requirements-api.txt         # API dependencies
```

## Installation Options

```bash
# Core only
pip install ollama-local-serve

# With specific features
pip install ollama-local-serve[langchain]      # LangChain integration
pip install ollama-local-serve[api]            # FastAPI server
pip install ollama-local-serve[instrumentation] # OpenTelemetry
pip install ollama-local-serve[clickhouse]     # ClickHouse exporter
pip install ollama-local-serve[postgres]       # PostgreSQL exporter
pip install ollama-local-serve[monitoring]     # Full monitoring stack
pip install ollama-local-serve[all]            # Everything

# Development
pip install -e ".[dev]"
```

## Error Handling

```python
from ollama_local_serve import (
    OllamaServiceError,       # Base exception
    ConnectionError,          # Connection failures
    HealthCheckError,         # Health check failures
    ServiceStartError,        # Service start failures
    ServiceStopError,         # Service stop failures
)

try:
    await service.health_check()
except ConnectionError as e:
    print(f"Connection failed: {e}")
except HealthCheckError as e:
    print(f"Health check failed: {e}")
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/AbhinaavRamesh/ollama-local-serve.git
cd ollama-local-serve

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend && npm install
```

### Code Quality

```bash
# Format code
black ollama_local_serve/

# Lint code
ruff check ollama_local_serve/

# Type checking
mypy ollama_local_serve/

# Run tests
pytest
```

### Development Mode

```bash
# Start development stack with hot reloading
make dev

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## API Reference

### OllamaService

Main service class for managing Ollama server instances.

**Methods:**
- `async start(startup_delay: float = 2.0)` - Start the Ollama server
- `async stop(timeout: float = 5.0)` - Stop the Ollama server
- `async health_check(retries: Optional[int] = None)` - Check service health
- `async get_models()` - Get list of available models
- `async generate(model: str, prompt: str)` - Generate text

**Properties:**
- `is_running: bool` - Check if service is running
- `base_url: str` - Get the base URL of the service
- `uptime_seconds: float` - Get service uptime
- `metrics_enabled: bool` - Check if metrics are enabled

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

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

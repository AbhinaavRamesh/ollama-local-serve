# Ollama Local Serve

[![PyPI version](https://badge.fury.io/py/ollama-local-serve.svg)](https://pypi.org/project/ollama-local-serve/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Local LLM infrastructure with a professional monitoring dashboard for distributed AI applications. Serve Ollama-powered models across your network with seamless LangChain integration, OpenTelemetry instrumentation, and real-time metrics visualization.

## Features

- **Service Management**: Easy start/stop control of Ollama server instances
- **Network Accessible**: Configure host/port for LAN accessibility
- **LangChain Integration**: Seamless integration with LangChain for remote LLM clients
- **OpenTelemetry Instrumentation**: Built-in metrics collection with OTEL support
- **Real-time Monitoring Dashboard**: Professional React dashboard with live metrics
- **In-App Chat Interface**: Floating chat bubble with streaming responses and markdown support
- **Model Management**: Pull, delete, and manage models directly from the dashboard
- **Model Repository**: Track favorites, usage stats, and preferences per model
- **Multiple Database Backends**: Export metrics to ClickHouse or PostgreSQL/TimescaleDB
- **Enhanced Request Logging**: Capture prompt/response text, client info, and token counts
- **Data Management**: Clear metrics/logs and view data summaries via API
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

# With LangGraph integration (includes LangChain)
pip install ollama-local-serve[langgraph]

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

> **Note:** The API Server is named `ollama-monitor` in docker-compose files and commands. This naming reflects the service's primary purpose as a monitoring API for Ollama. When you see references to `ollama-monitor` in docker commands or compose files, this refers to the API Server listed above.

### Make Commands

#### Core Commands
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

#### Dependency Installation
```bash
make install                  # Install all dependencies (Python + Frontend)
make install-python           # Install Python dependencies
make install-python-venv      # Install Python deps in virtual environment
make install-frontend         # Install frontend (Node.js) dependencies
make install-db-clients       # Install database CLI clients (ClickHouse + PostgreSQL)
make install-clickhouse-client # Install ClickHouse client only
make install-postgres-client  # Install PostgreSQL client only
make check-deps               # Check if required dependencies are installed
```

#### Selective Service Startup (Toggle Databases)
```bash
make up-minimal      # Start only Ollama + API (no databases, no frontend)
make up-clickhouse   # Start full stack with ClickHouse (includes frontend)
make up-postgres     # Start full stack with PostgreSQL (includes frontend)

# Or use environment variables to toggle services (with up-selective target):
make up-selective ENABLE_CLICKHOUSE=false    # Disable ClickHouse
make up-selective ENABLE_POSTGRES=false      # Disable PostgreSQL
make up-selective ENABLE_FRONTEND=false      # Disable frontend dashboard
```

#### Local Development (without Docker)
```bash
make run-api        # Run API server locally (port 8000)
make run-frontend   # Run frontend dev server locally (port 5173)
make run-local      # Run both API and frontend in parallel
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
# Health & Stats
GET  /api/health           - Health check
GET  /api/stats/current    - Current statistics
GET  /api/stats/history    - Historical metrics
GET  /api/stats/logs       - Request logs (with prompt/response text)
GET  /api/models           - Model statistics

# Chat
POST /api/chat             - Stream chat with Ollama (SSE)

# Ollama Proxy
GET  /api/ollama/models    - List installed Ollama models
POST /api/ollama/pull      - Pull a model (streaming progress)
DELETE /api/ollama/models/{name} - Delete a model
GET  /api/ollama/library   - Search model library

# Model Repository (PostgreSQL)
GET  /api/models/repository         - Get all models with preferences
GET  /api/models/repository/{name}  - Get model details
POST /api/models/repository         - Add model to repository
PUT  /api/models/repository/{name}  - Update model (favorite, default)
POST /api/models/repository/sync    - Sync with installed models

# Data Management
GET    /api/data/summary   - Get data summary
DELETE /api/data/metrics   - Clear all metrics
DELETE /api/data/logs      - Clear all request logs
DELETE /api/data/all       - Clear all data
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

### LangGraph ReAct Agent

For advanced use cases, you can use LangGraph's prebuilt ReAct agent with Ollama:

```python
from ollama_local_serve import OllamaService, NetworkConfig, create_langchain_chat_client
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

# Define tools for the agent
@tool
def cube(x: float) -> float:
    """Calculate the cube of a number."""
    return x ** 3

# Start Ollama service and create agent
config = NetworkConfig()
async with OllamaService(config) as service:
    llm = create_langchain_chat_client(config=config, model="llama3.2")
    agent = create_react_agent(llm, [cube])
    
    response = await agent.ainvoke({"messages": [("user", "What is 5 cubed?")]})
    print(response["messages"][-1].content)
```

See `langgraph_react_agent_example.py` for a complete working example with multiple tools.


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
│   │   │   ├── chat/            # Chat bubble with streaming
│   │   │   ├── charts/          # Visualization components
│   │   │   └── ...              # Other UI components
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── context/             # App and Theme context
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
pip install ollama-local-serve[langgraph]      # LangGraph integration (includes LangChain)
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

# Check what dependencies you have installed
make check-deps

# Option 1: Install all dependencies at once
make install

# Option 2: Use virtual environment for Python
make install-python-venv   # Creates .venv and installs deps
source .venv/bin/activate  # Activate the virtual environment
make install-frontend      # Install frontend deps

# Option 3: Manual setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"
cd frontend && npm install

# Optional: Install database clients for local debugging
make install-db-clients
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
# Option 1: Use Docker (hot reloading enabled)
make dev

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Option 2: Run locally without Docker
make run-local   # Runs both API and frontend

# Or run separately:
# Run API locally (update the module path if needed):
python -m ollama_local_serve.api  # API on http://localhost:8000
make run-frontend  # Frontend on http://localhost:5173
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

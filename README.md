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

See [Installation Guide](docs/INSTALLATION.md) for detailed installation options and prerequisites.

### Basic Usage

```python
import asyncio
from ollama_local_serve import OllamaService, NetworkConfig

async def main():
    config = NetworkConfig(host="0.0.0.0", port=11434)
    
    async with OllamaService(config) as service:
        print(f"Service running at {service.base_url}")
        await service.health_check()

asyncio.run(main())
```

See [Installation Guide](docs/INSTALLATION.md) for more examples and error handling.

## Use Cases

Ollama Local Serve is ideal for:

- **Development & Testing**: Quick local LLM setup with integrated monitoring
- **Research & Experimentation**: Compare models, track metrics, benchmark performance
- **Small to Medium Scale Inference**: Single or small cluster deployments (10-100 concurrent users)
- **AI Agent Development**: Build ReAct agents with LangChain/LangGraph integration
- **Educational Projects**: Learn about LLMs, monitoring, distributed systems
- **Internal Tools**: Deploy custom AI features within organizations
- **Prototyping**: Fast iteration with live metrics and dashboard feedback

## Deployment Comparison

| Aspect | Docker Compose | Kubernetes | Local Development |
|--------|---|---|---|
| **Setup Time** | 5 minutes | 15-30 minutes | 2-3 minutes |
| **Scalability** | Single machine | Multi-node clusters | Single machine |
| **Persistence** | Volumes | PersistentVolumeClaims | Local filesystem |
| **Best For** | Development, testing | Production, scaling | Quick prototyping |
| **GPU Support** | Yes | Yes (NVIDIA plugin) | Yes |
| **Cost** | Low | Moderate to High | Free |
| **Monitoring** | Built-in dashboard | Enhanced with Prometheus | Dashboard included |

**Recommendation**: Start with Docker Compose for development, move to Kubernetes for production multi-node deployments.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│  (Python Scripts, LangChain Agents, HTTP Clients, etc.)    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─────────────────┬─────────────────┐
                 │                 │                 │
        ┌────────▼────────┐   ┌───▼──────────┐  ┌──▼─────────────┐
        │   FastAPI Server │   │  Ollama      │  │  React Dashboard
        │   (Port 8000)    │   │  (Port 11434)│  │  (Port 3000/5173)
        │                  │   │              │  │
        │ REST API Layer   │   │ LLM Engine   │  │ Real-time UI
        │ - Chat Endpoint  │   │ - Models     │  │ - Metrics Viz
        │ - Stats/Metrics  │   │ - Generation │  │ - System Health
        │ - Health Checks  │   │ - Streaming  │  │ - Model Mgmt
        └────────┬─────────┘   └──────────────┘  └────────────────┘
                 │
        ┌────────▼──────────────────────────┐
        │   Metrics Collection Layer        │
        │   (OpenTelemetry Instrumentation) │
        │   - Request tracking              │
        │   - Token counting                │
        │   - Performance metrics           │
        │   - Error tracking                │
        └────────┬──────────────────────────┘
                 │
        ┌────────▼──────────────────────────┐
        │   Storage Layer (Choose one/both) │
        ├──────────────────────────────────┤
        │  ClickHouse (Time-series)        │
        │  - Fast metrics queries           │
        │  - Real-time aggregations         │
        │                                   │
        │  PostgreSQL/TimescaleDB (Query)  │
        │  - Relational queries             │
        │  - Model metadata                 │
        └───────────────────────────────────┘
```

## Common Workflows

### Quick Local Testing
```bash
make init && make up
# Open http://localhost:3000 → Start chatting & monitoring
```

### LangChain Agent Development
```python
from ollama_local_serve import create_langchain_chat_client, OllamaService
async with OllamaService() as service:
    llm = create_langchain_chat_client(model="llama3.2")
    # Build your agent...
```

### Production Kubernetes Deployment
```bash
cd k8s
helm install ollama-serve . -n production -f values.yaml
# Configure ingress, GPU, and database backends
```

### Performance Benchmarking
```bash
make up  # Start stack
# Generate load and monitor metrics in dashboard
# Check /api/stats/history for detailed performance data
```

## Documentation

Detailed documentation is organized into the following sections:

| Guide | Description |
|-------|-------------|
| [Installation Guide](docs/INSTALLATION.md) | Installation methods, prerequisites, and basic usage |
| [Docker Deployment](docs/DOCKER.md) | Docker Compose setup and Make commands |
| [Kubernetes Deployment](docs/KUBERNETES.md) | Helm charts and K8s deployment |
| [Configuration](docs/CONFIGURATION.md) | Environment variables and Pydantic config |
| [Monitoring & Instrumentation](docs/MONITORING.md) | Metrics, instrumentation, and API endpoints |
| [LangChain Integration](docs/LANGCHAIN.md) | LangChain and LangGraph usage examples |
| [Development Guide](docs/DEVELOPMENT.md) | Setup, code quality, and development mode |
| [API Reference](docs/API_REFERENCE.md) | Python API and REST endpoint documentation |
| [GPU Testing Guide](docs/GPU_TESTING_GUIDE.md) | GPU setup, verification, and benchmarking |

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
├── k8s/                         # Kubernetes configuration
│   ├── values.yaml
│   ├── values-local.yaml
│   └── local-databases.yaml
├── docker-compose.yml           # Production stack
├── docker-compose.dev.yml       # Development overrides
├── Dockerfile                   # API Dockerfile
├── Makefile                     # Convenience commands
├── pyproject.toml               # Python project config
├── requirements-api.txt         # API dependencies
└── docs/                        # Documentation
    ├── INSTALLATION.md
    ├── DOCKER.md
    ├── KUBERNETES.md
    ├── CONFIGURATION.md
    ├── MONITORING.md
    ├── LANGCHAIN.md
    ├── API_REFERENCE.md
    └── DEVELOPMENT.md
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

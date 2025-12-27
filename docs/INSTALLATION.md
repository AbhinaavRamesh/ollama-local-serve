# Installation Guide

## Prerequisites

- Python 3.12 or higher
- Ollama installed on your system ([Download Ollama](https://ollama.ai))

## Pre-Flight Checks

Before installation, verify your system setup:

```bash
# Check Python version
python --version  # Should be 3.12+

# Check Ollama installation
ollama --version

# Check Ollama service is accessible
curl http://localhost:11434/api/tags

# (Optional) Check Docker for Docker Compose deployment
docker --version

# (Optional) Check Kubernetes tools
kubectl version --client
helm version
```

If any checks fail, refer to the [Troubleshooting](#troubleshooting) section below.

## Installation Methods

### Basic Installation

```bash
# Core only
pip install ollama-local-serve
```

### With Specific Features

```bash
# With LangChain integration
pip install ollama-local-serve[langchain]

# With LangGraph integration (includes LangChain)
pip install ollama-local-serve[langgraph]

# With FastAPI server
pip install ollama-local-serve[api]

# With OpenTelemetry instrumentation
pip install ollama-local-serve[instrumentation]

# With ClickHouse exporter
pip install ollama-local-serve[clickhouse]

# With PostgreSQL exporter
pip install ollama-local-serve[postgres]

# With full monitoring stack
pip install ollama-local-serve[monitoring]

# Everything
pip install ollama-local-serve[all]
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/AbhinaavRamesh/ollama-local-serve.git
cd ollama-local-serve

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

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

## Troubleshooting

### Python Version Issues

**Problem**: `Error: Python 3.12+ required`

**Solutions**:
```bash
# Check your Python version
python --version

# Use python3 explicitly (macOS/Linux)
python3 --version
python3 -m pip install ollama-local-serve

# For multiple Python versions, use explicit version
python3.12 -m pip install ollama-local-serve

# Or create a virtual environment with Python 3.12
python3.12 -m venv venv
source venv/bin/activate
pip install ollama-local-serve
```

### Ollama Connection Issues

**Problem**: `ConnectionError: Failed to connect to Ollama`

**Solutions**:
```bash
# 1. Verify Ollama is running
ollama serve  # In a separate terminal

# 2. Check Ollama is accessible
curl http://localhost:11434/api/tags

# 3. If using remote Ollama, provide the correct host
config = NetworkConfig(host="192.168.1.100", port=11434)

# 4. Check firewall isn't blocking the port
# On macOS/Linux:
lsof -i :11434

# On Windows:
netstat -ano | findstr :11434

# 5. Increase timeout for slow networks
config = NetworkConfig(timeout=60, max_retries=5)
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'ollama_local_serve'`

**Solutions**:
```bash
# Verify installation
pip show ollama-local-serve

# Reinstall the package
pip install --force-reinstall ollama-local-serve

# If using development mode, ensure you're in the right directory
cd ollama-local-serve
pip install -e .

# Check Python path includes package
python -c "import sys; print(sys.path)"
```

### Virtual Environment Issues

**Problem**: Package installed but not found in virtual environment

**Solutions**:
```bash
# Deactivate and reactivate virtual environment
deactivate
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Verify you're in the correct venv
which python  # Should point to venv/bin/python

# Reinstall in the active environment
pip install ollama-local-serve

# Check installed packages
pip list | grep ollama
```

### LangChain Integration Issues

**Problem**: `ModuleNotFoundError` when importing LangChain components

**Solutions**:
```bash
# Install with LangChain support
pip install ollama-local-serve[langchain]

# Or add LangChain separately
pip install langchain langchain-community

# Verify installation
python -c "from langchain_ollama import OllamaLLM; print('OK')"
```

### Docker/Kubernetes Setup Issues

**Problem**: Issues with Docker Compose or Kubernetes deployment

**Solutions**:
```bash
# For Docker Compose:
# 1. Check Docker is running
docker ps

# 2. View detailed logs
docker compose logs -f

# 3. Check service health
docker compose ps

# 4. Restart services
docker compose restart

# For Kubernetes:
# 1. Check Helm is installed
helm version

# 2. Update chart dependencies
cd k8s && helm dependency update

# 3. Validate chart
helm lint .

# 4. Test template rendering
helm template ollama-serve . --values values-local.yaml
```

### No Module Named 'numpy' or Other Dependencies

**Problem**: Dependency resolution errors during installation

**Solutions**:
```bash
# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Clear pip cache and reinstall
pip install --no-cache-dir ollama-local-serve

# Install with specific features incrementally
pip install ollama-local-serve  # Core
pip install ollama-local-serve[langchain]  # Add LangChain
pip install ollama-local-serve[monitoring]  # Add monitoring

# Check for conflicting packages
pip check
```

### Async/Await Issues

**Problem**: `RuntimeError: no running event loop` when using OllamaService

**Solutions**:
```python
# Correct: Use asyncio.run()
import asyncio
from ollama_local_serve import OllamaService

async def main():
    async with OllamaService() as service:
        await service.health_check()

asyncio.run(main())

# If in Jupyter notebook:
import asyncio
from ollama_local_serve import OllamaService

# Use asyncio for Jupyter
await OllamaService().health_check()

# Or use nest_asyncio
import nest_asyncio
nest_asyncio.apply()
# Then use asyncio.run() normally
```

### Getting Help

If you encounter an issue not covered here:

1. **Check existing issues**: https://github.com/AbhinaavRamesh/ollama-local-serve/issues
2. **Review logs**:
   - Docker: `docker compose logs -f`
   - Local: Run with verbose output
3. **Enable debug logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
4. **Open a new issue** with:
   - Your Python version (`python --version`)
   - Installation method used
   - Full error message and traceback
   - Steps to reproduce

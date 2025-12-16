# ollama-local-serve

Local LLM infrastructure for distributed AI applications. Serve Ollama-powered models across your network with seamless LangChain integration.

## Features

- 🚀 **Service Management**: Easy start/stop control of Ollama server instances
- 🌐 **Network Accessible**: Configure host/port for LAN accessibility  
- 🔗 **LangChain Integration**: Seamless integration with LangChain for remote LLM clients
- ✅ **Health Checks**: Built-in health check endpoints to monitor service status
- 🛡️ **Error Handling**: Comprehensive error handling for connection failures
- ⚡ **Async/Await**: Production-ready async patterns throughout
- 📝 **Type Hints**: Full type annotations for better IDE support
- 📚 **Documentation**: Comprehensive docstrings and examples

## Installation

```bash
pip install -r requirements.txt
```

## Prerequisites

- Python 3.8 or higher
- Ollama installed on your system ([Download Ollama](https://ollama.ai))

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

### LangChain Integration

```python
import asyncio
from ollama_local_serve import (
    OllamaService,
    NetworkConfig,
    create_langchain_client
)

async def main():
    config = NetworkConfig(host="0.0.0.0", port=11434)
    
    async with OllamaService(config) as service:
        # Create a LangChain client
        llm = create_langchain_client(
            config=config,
            model="llama2",
            temperature=0.7
        )
        
        # Use with LangChain
        response = llm.invoke("What is the meaning of life?")
        print(response)

asyncio.run(main())
```

### Remote Client Connection

```python
from ollama_local_serve import create_langchain_client

# Connect to a remote Ollama service
llm = create_langchain_client(
    base_url="http://192.168.1.100:11434",
    model="mistral"
)

response = llm.invoke("Tell me a joke")
print(response)
```

## API Reference

### OllamaService

Main service class for managing Ollama server instances.

**Methods:**
- `async start(startup_delay: float = 2.0)` - Start the Ollama server
- `async stop(timeout: float = 5.0)` - Stop the Ollama server
- `async health_check(retries: Optional[int] = None)` - Check service health
- `async get_models()` - Get list of available models

**Properties:**
- `is_running: bool` - Check if service is running
- `base_url: str` - Get the base URL of the service

### NetworkConfig

Configuration for network settings.

**Attributes:**
- `host: str` - Host address (default: "0.0.0.0")
- `port: int` - Port number (default: 11434)
- `timeout: int` - Connection timeout in seconds (default: 30)
- `max_retries: int` - Maximum retry attempts (default: 3)

**Methods:**
- `base_url: str` - Get the base URL
- `api_url: str` - Get the API URL
- `get_connection_url(localhost_fallback: bool = False)` - Get connection URL

### create_langchain_client

Create a LangChain Ollama client for remote LLM access.

**Parameters:**
- `base_url: Optional[str]` - Base URL of Ollama service
- `config: Optional[NetworkConfig]` - Network configuration
- `model: str` - Model name (default: "llama2")
- `**kwargs` - Additional arguments for Ollama client

**Returns:** LangChain Ollama client instance

## Error Handling

The library provides specific exceptions for different error scenarios:

```python
from ollama_local_serve import (
    OllamaServiceError,      # Base exception
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

## Network Configuration

### Local Access Only

```python
config = NetworkConfig(host="localhost", port=11434)
```

### LAN Access

```python
config = NetworkConfig(host="0.0.0.0", port=11434)
# Service will be accessible at http://<your-ip>:11434
```

### Custom Port

```python
config = NetworkConfig(host="0.0.0.0", port=8080)
```

## Examples

Run the example script to see all features in action:

```bash
python example.py
```

The example script demonstrates:
- Basic service management
- Context manager usage
- LangChain integration
- Error handling patterns
- Network accessibility setup

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Code Quality

```bash
# Format code
black ollama_local_serve/

# Lint code
ruff check ollama_local_serve/

# Type checking
mypy ollama_local_serve/
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

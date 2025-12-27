# API Reference

## OllamaService

Main service class for managing Ollama server instances.

### Methods

- `async start(startup_delay: float = 2.0)` - Start the Ollama server
- `async stop(timeout: float = 5.0)` - Stop the Ollama server
- `async health_check(retries: Optional[int] = None)` - Check service health
- `async get_models()` - Get list of available models
- `async generate(model: str, prompt: str)` - Generate text

### Properties

- `is_running: bool` - Check if service is running
- `base_url: str` - Get the base URL of the service
- `uptime_seconds: float` - Get service uptime
- `metrics_enabled: bool` - Check if metrics are enabled

## NetworkConfig

Configuration for network settings (Pydantic BaseSettings).

### Attributes

- `host: str` - Host address (default: "0.0.0.0")
- `port: int` - Port number (default: 11434)
- `timeout: int` - Connection timeout in seconds (default: 30)
- `max_retries: int` - Maximum retry attempts (default: 3)

### Computed Properties

- `base_url: str` - Get the base URL
- `api_url: str` - Get the API URL

## REST API Endpoints

### Health & Stats

```
GET  /api/health           - Health check
GET  /api/stats/current    - Current statistics
GET  /api/stats/history    - Historical metrics
GET  /api/stats/logs       - Request logs (with prompt/response text)
GET  /api/models           - Model statistics
```

#### Health Check

**Request:**
```bash
curl http://localhost:8000/api/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "ollama_running": true,
  "database_connected": true,
  "message": "All systems operational"
}
```

#### Current Statistics

**Request:**
```bash
curl http://localhost:8000/api/stats/current
```

**Response (200 OK):**
```json
{
  "total_requests": 42,
  "total_tokens": 5230,
  "total_errors": 2,
  "avg_latency_ms": 1250.5,
  "models_in_use": ["llama3.2", "mistral"],
  "uptime_seconds": 3600,
  "timestamp": "2024-12-26T10:15:23Z"
}
```

#### Historical Metrics

**Request:**
```bash
curl "http://localhost:8000/api/stats/history?hours=24"
```

**Response (200 OK):**
```json
{
  "metrics": [
    {
      "timestamp": "2024-12-26T09:00:00Z",
      "requests_per_minute": 5,
      "tokens_per_second": 45,
      "avg_latency_ms": 1200,
      "error_rate": 0.05
    },
    {
      "timestamp": "2024-12-26T10:00:00Z",
      "requests_per_minute": 8,
      "tokens_per_second": 67,
      "avg_latency_ms": 1100,
      "error_rate": 0.02
    }
  ]
}
```

#### Request Logs

**Request:**
```bash
curl "http://localhost:8000/api/stats/logs?limit=5&model=llama3.2"
```

**Response (200 OK):**
```json
{
  "logs": [
    {
      "id": "req-001",
      "timestamp": "2024-12-26T10:15:23Z",
      "model": "llama3.2",
      "prompt": "What is Python?",
      "response": "Python is a high-level programming language...",
      "tokens_used": 150,
      "latency_ms": 1250,
      "status": "success",
      "client_ip": "192.168.1.100"
    },
    {
      "id": "req-002",
      "timestamp": "2024-12-26T10:14:10Z",
      "model": "llama3.2",
      "prompt": "Explain Docker",
      "response": "Docker is a containerization platform...",
      "tokens_used": 200,
      "latency_ms": 1500,
      "status": "success",
      "client_ip": "192.168.1.100"
    }
  ]
}
```

#### Model Statistics

**Request:**
```bash
curl http://localhost:8000/api/models
```

**Response (200 OK):**
```json
{
  "models": [
    {
      "name": "llama3.2",
      "total_requests": 25,
      "total_tokens": 3000,
      "avg_latency_ms": 1150,
      "tokens_per_second": 50,
      "error_rate": 0.04,
      "last_used": "2024-12-26T10:15:23Z"
    },
    {
      "name": "mistral",
      "total_requests": 17,
      "total_tokens": 2230,
      "avg_latency_ms": 1320,
      "tokens_per_second": 42,
      "error_rate": 0.12,
      "last_used": "2024-12-26T10:10:00Z"
    }
  ]
}
```

### Chat

```
POST /api/chat             - Stream chat with Ollama (SSE)
```

#### Chat Endpoint

**Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "prompt": "Explain quantum computing",
    "temperature": 0.7,
    "top_p": 0.9
  }'
```

**Response (200 OK - Server-Sent Events):**
```
data: {"token": "Quantum", "latency_ms": 150}
data: {"token": " computing", "latency_ms": 200}
data: {"token": " is", "latency_ms": 180}
...
data: {"token": "[DONE]", "latency_ms": 0, "total_tokens": 150}
```

### Ollama Proxy

```
GET  /api/ollama/models    - List installed Ollama models
POST /api/ollama/pull      - Pull a model (streaming progress)
DELETE /api/ollama/models/{name} - Delete a model
GET  /api/ollama/library   - Search model library
```

#### List Models

**Request:**
```bash
curl http://localhost:8000/api/ollama/models
```

**Response (200 OK):**
```json
{
  "models": [
    {
      "name": "llama3.2",
      "size": "4.7 GB",
      "modified_at": "2024-12-26T10:00:00Z",
      "digest": "sha256:abc123..."
    },
    {
      "name": "mistral",
      "size": "7.3 GB",
      "modified_at": "2024-12-25T15:30:00Z",
      "digest": "sha256:def456..."
    }
  ]
}
```

#### Pull Model

**Request:**
```bash
curl -X POST http://localhost:8000/api/ollama/pull \
  -H "Content-Type: application/json" \
  -d '{"model": "neural-chat"}'
```

**Response (200 OK - Streaming):**
```
data: {"status": "pulling manifest"}
data: {"status": "downloading", "digest": "sha256:...", "total": 1000000, "completed": 250000}
data: {"status": "downloading", "digest": "sha256:...", "total": 1000000, "completed": 500000}
data: {"status": "verifying checksum"}
data: {"status": "complete", "message": "Successfully pulled neural-chat"}
```

#### Delete Model

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/ollama/models/llama3.2
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Model 'llama3.2' deleted successfully"
}
```

### Model Repository (PostgreSQL)

```
GET  /api/models/repository         - Get all models with preferences
GET  /api/models/repository/{name}  - Get model details
POST /api/models/repository         - Add model to repository
PUT  /api/models/repository/{name}  - Update model (favorite, default)
POST /api/models/repository/sync    - Sync with installed models
```

#### Get All Repository Models

**Request:**
```bash
curl http://localhost:8000/api/models/repository
```

**Response (200 OK):**
```json
{
  "models": [
    {
      "name": "llama3.2",
      "description": "A fast and capable LLM",
      "is_favorite": true,
      "is_default": true,
      "tags": ["fast", "capable"],
      "created_at": "2024-12-26T10:00:00Z"
    }
  ]
}
```

#### Get Model Details

**Request:**
```bash
curl http://localhost:8000/api/models/repository/llama3.2
```

**Response (200 OK):**
```json
{
  "name": "llama3.2",
  "description": "A fast and capable LLM",
  "is_favorite": true,
  "is_default": true,
  "tags": ["fast", "capable"],
  "created_at": "2024-12-26T10:00:00Z",
  "stats": {
    "total_requests": 25,
    "avg_latency_ms": 1150
  }
}
```

#### Update Model

**Request:**
```bash
curl -X PUT http://localhost:8000/api/models/repository/llama3.2 \
  -H "Content-Type: application/json" \
  -d '{
    "is_favorite": true,
    "is_default": true,
    "description": "My preferred model"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Model updated successfully"
}
```

### Data Management

```
GET    /api/data/summary   - Get data summary
DELETE /api/data/metrics   - Clear all metrics
DELETE /api/data/logs      - Clear all request logs
DELETE /api/data/all       - Clear all data
```

#### Data Summary

**Request:**
```bash
curl http://localhost:8000/api/data/summary
```

**Response (200 OK):**
```json
{
  "total_requests": 42,
  "total_logs_entries": 42,
  "metric_points": 240,
  "oldest_timestamp": "2024-12-25T10:00:00Z",
  "newest_timestamp": "2024-12-26T10:15:23Z",
  "database_size_mb": 15.3
}
```

#### Clear Metrics

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/data/metrics
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "All metrics cleared",
  "rows_deleted": 240
}
```

#### Clear All Data

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/data/all
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "All data cleared",
  "metrics_deleted": 240,
  "logs_deleted": 42
}
```

## Error Responses

### 400 Bad Request

**Response:**
```json
{
  "detail": "Invalid request parameters",
  "error": "model parameter is required"
}
```

### 404 Not Found

**Response:**
```json
{
  "detail": "Model not found",
  "model": "unknown_model"
}
```

### 500 Internal Server Error

**Response:**
```json
{
  "detail": "Internal server error",
  "error": "Database connection failed"
}
```

## Common Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `limit` | int | Max results (default: 100) | `?limit=50` |
| `offset` | int | Pagination offset | `?offset=100` |
| `model` | string | Filter by model name | `?model=llama3.2` |
| `status` | string | Filter by status | `?status=success` |
| `hours` | int | Time range in hours | `?hours=24` |
| `sort` | string | Sort field | `?sort=latency_ms` |

## Rate Limiting

The API does not enforce rate limits by default. For production deployments, consider:
- Nginx rate limiting
- API Gateway rate limiting
- Application-level throttling

## Authentication

Currently, the API is open with CORS enabled. For production, consider:
- Adding API key authentication
- Implementing JWT tokens
- Using OAuth 2.0
- Deploying behind authentication proxy

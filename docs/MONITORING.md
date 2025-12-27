# Monitoring & Instrumentation

## Enable Instrumentation

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

## Available Metrics

- `ollama_requests_total` - Total number of requests
- `ollama_tokens_generated_total` - Total tokens generated
- `ollama_errors_total` - Total errors
- `ollama_request_latency_ms` - Request latency histogram

## API Endpoints

The monitoring API provides the following endpoints:

### Health & Stats

```
GET  /api/health           - Health check
GET  /api/stats/current    - Current statistics
GET  /api/stats/history    - Historical metrics
GET  /api/stats/logs       - Request logs (with prompt/response text)
GET  /api/models           - Model statistics
```

### Chat

```
POST /api/chat             - Stream chat with Ollama (SSE)
```

### Ollama Proxy

```
GET  /api/ollama/models    - List installed Ollama models
POST /api/ollama/pull      - Pull a model (streaming progress)
DELETE /api/ollama/models/{name} - Delete a model
GET  /api/ollama/library   - Search model library
```

### Model Repository (PostgreSQL)

```
GET  /api/models/repository         - Get all models with preferences
GET  /api/models/repository/{name}  - Get model details
POST /api/models/repository         - Add model to repository
PUT  /api/models/repository/{name}  - Update model (favorite, default)
POST /api/models/repository/sync    - Sync with installed models
```

### Data Management

```
GET    /api/data/summary   - Get data summary
DELETE /api/data/metrics   - Clear all metrics
DELETE /api/data/logs      - Clear all request logs
DELETE /api/data/all       - Clear all data
```

## Query Examples

### Get Current Statistics

```bash
curl http://localhost:8000/api/stats/current | python3 -m json.tool
```

**Response:**
```json
{
  "total_requests": 42,
  "total_tokens": 5230,
  "total_errors": 2,
  "avg_latency_ms": 1250,
  "models_in_use": ["llama3.2", "mistral"],
  "uptime_seconds": 3600
}
```

### Get Historical Metrics

```bash
curl http://localhost:8000/api/stats/history | python3 -m json.tool
```

**Response:**
```json
{
  "metrics": [
    {
      "timestamp": "2024-12-26T10:00:00Z",
      "requests_per_minute": 5,
      "tokens_per_second": 45,
      "avg_latency_ms": 1200,
      "error_rate": 0.05
    },
    {
      "timestamp": "2024-12-26T10:05:00Z",
      "requests_per_minute": 8,
      "tokens_per_second": 67,
      "avg_latency_ms": 1100,
      "error_rate": 0.02
    }
  ]
}
```

### Get Request Logs with Prompts/Responses

```bash
# Get last 10 requests
curl "http://localhost:8000/api/stats/logs?limit=10" | python3 -m json.tool

# Get logs for specific model
curl "http://localhost:8000/api/stats/logs?model=llama3.2&limit=5" | python3 -m json.tool

# Get failed requests only
curl "http://localhost:8000/api/stats/logs?status=error&limit=10" | python3 -m json.tool
```

**Response:**
```json
{
  "logs": [
    {
      "id": "req-001",
      "timestamp": "2024-12-26T10:15:23Z",
      "model": "llama3.2",
      "prompt": "What is machine learning?",
      "response": "Machine learning is a subset of artificial intelligence...",
      "tokens_used": 150,
      "latency_ms": 1250,
      "status": "success",
      "client_ip": "192.168.1.100"
    }
  ]
}
```

### Get Model Statistics

```bash
# Get stats for all models
curl http://localhost:8000/api/models | python3 -m json.tool

# Response includes per-model metrics
```

**Response:**
```json
{
  "models": [
    {
      "name": "llama3.2",
      "total_requests": 25,
      "total_tokens": 3000,
      "avg_latency_ms": 1150,
      "tokens_per_second": 50,
      "error_rate": 0.04
    },
    {
      "name": "mistral",
      "total_requests": 17,
      "total_tokens": 2230,
      "avg_latency_ms": 1320,
      "tokens_per_second": 42,
      "error_rate": 0.12
    }
  ]
}
```

### Get Prometheus Format Metrics

```bash
# Get Prometheus metrics (for Prometheus/Grafana scraping)
curl http://localhost:8000/api/metrics | head -30
```

**Sample output:**
```
# HELP ollama_requests_total Total number of requests
# TYPE ollama_requests_total counter
ollama_requests_total 42.0

# HELP ollama_tokens_generated_total Total tokens generated
# TYPE ollama_tokens_generated_total counter
ollama_tokens_generated_total 5230.0

# HELP ollama_request_latency_ms Request latency histogram
# TYPE ollama_request_latency_ms histogram
ollama_request_latency_ms_bucket{model="llama3.2",le="100"} 0.0
ollama_request_latency_ms_bucket{model="llama3.2",le="500"} 5.0
ollama_request_latency_ms_bucket{model="llama3.2",le="1000"} 18.0
ollama_request_latency_ms_bucket{model="llama3.2",le="5000"} 25.0
```

### Get GPU Metrics (if GPU available)

```bash
# Get current GPU status
curl http://localhost:8000/api/gpu | python3 -m json.tool

# Response includes GPU utilization, memory, temperature
```

**Response:**
```json
{
  "available": true,
  "gpu_count": 1,
  "gpus": [
    {
      "index": 0,
      "name": "NVIDIA RTX 3090",
      "utilization_percent": 75,
      "memory_used_mb": 8192,
      "memory_total_mb": 24576,
      "temperature_c": 65,
      "power_draw_w": 280
    }
  ]
}
```

## Advanced Queries

### Using ClickHouse (if enabled)

```bash
# Connect to ClickHouse CLI
clickhouse-client -h localhost

# Query request metrics
SELECT timestamp, model, avg(latency_ms) as avg_latency
FROM requests
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY timestamp, model
ORDER BY timestamp DESC;

# Find slow requests
SELECT model, prompt, response, latency_ms
FROM requests
WHERE latency_ms > 3000
ORDER BY latency_ms DESC
LIMIT 10;
```

### Using PostgreSQL/TimescaleDB (if enabled)

```bash
# Connect to PostgreSQL
psql -h localhost -U ollama -d ollama_metrics

# Query request logs
SELECT model, count(*) as total_requests,
       avg(latency_ms) as avg_latency,
       max(latency_ms) as max_latency
FROM request_logs
WHERE created_at > now() - interval '1 hour'
GROUP BY model
ORDER BY total_requests DESC;

# Find error patterns
SELECT model, error_message, count(*) as error_count
FROM request_logs
WHERE status = 'error'
AND created_at > now() - interval '24 hours'
GROUP BY model, error_message
ORDER BY error_count DESC;
```

## Dashboard Customization

### Dashboard Overview Panel

The overview panel displays key metrics:
- **Total Requests**: Cumulative request count
- **Total Tokens**: Total tokens generated
- **Active Models**: Recently used models
- **Avg Latency**: Average response time

The dashboard auto-refreshes every 5 seconds by default.

### Performance Metrics Visualization

The dashboard includes charts for:
- **Requests per Minute**: Real-time request rate
- **Tokens per Second**: Throughput metric
- **Latency Percentiles**: P50, P95, P99 latencies
- **Error Rate**: Percentage of failed requests

### Custom Refresh Intervals

Change auto-refresh timing in dashboard settings (look for Settings icon).

### Export Metrics

```bash
# Export current stats as JSON
curl http://localhost:8000/api/stats/current > metrics_$(date +%s).json

# Export historical data for analysis
curl http://localhost:8000/api/stats/history > history.json
```

### Integration with External Monitoring

#### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'ollama'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 30s
```

#### Grafana Dashboard

Create a new dashboard with panels:

```json
{
  "dashboard": {
    "title": "Ollama Metrics",
    "panels": [
      {
        "title": "Requests per Minute",
        "targets": [
          {
            "expr": "increase(ollama_requests_total[1m])"
          }
        ]
      },
      {
        "title": "Token Rate",
        "targets": [
          {
            "expr": "increase(ollama_tokens_generated_total[1m]) / 60"
          }
        ]
      },
      {
        "title": "Latency (ms)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, ollama_request_latency_ms)"
          }
        ]
      }
    ]
  }
}
```

## Alerting

### Common Alert Thresholds

```yaml
# Prometheus alert rules (prometheus_rules.yml)
groups:
  - name: ollama_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(ollama_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, ollama_request_latency_ms) > 3000
        for: 5m
        annotations:
          summary: "Request latency exceeding 3 seconds"

      - alert: ServiceDown
        expr: up{job="ollama"} == 0
        for: 1m
        annotations:
          summary: "Ollama service is down"
```

## Performance Tuning Tips

1. **Monitor P95/P99 latencies** - Focus on tail latencies, not just averages
2. **Track tokens/second** - Better indicator of throughput than requests/sec
3. **Watch error rate** - Should be < 1% in production
4. **Monitor GPU utilization** - Aim for 70-90% for optimal throughput
5. **Track queue depth** - Indicates if requests are backing up

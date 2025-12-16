# Claude Code Task: Build Monitoring Dashboard for ollama-local-serve

## 🎯 Project Overview

Extend the existing `ollama-local-serve` Python package with comprehensive observability features. Create a complete production-ready stack with:
1. OpenTelemetry (OTEL) instrumentation for the Ollama service
2. Real-time monitoring dashboard (React)
3. Time-series data persistence (ClickHouse + PostgreSQL support)
4. Docker Compose orchestration for local development

---

## 📋 Requirements & Scope

### Phase 1: Backend Instrumentation & Data Pipeline

#### 1.1 OTEL Instrumentation Module (`ollama_local_serve/instrumentation/`)
Create a new instrumentation package that tracks:

**Metrics to capture:**
- **Request Metrics**: Total requests, request latency (ms), tokens generated, tokens/second
- **System Metrics**: CPU usage (%), memory usage (%), uptime (hours)
- **Model Metrics**: Model load time, inference time per model
- **Service Health**: Service status (up/down), error count, error rate

**Implementation requirements:**
- Use `opentelemetry-api` and `opentelemetry-sdk` for instrumentation
- Create custom metrics using `Meter` provider
- Implement distributed tracing with spans for service start/stop/health_check
- Add context propagation for request tracking
- Export metrics in both OTEL format and custom JSON format for flexibility

**Key components:**
- `metrics_provider.py`: Initialize and configure metrics collection
- `tracer.py`: Setup tracing with automatic span creation
- `exporters/`: Support for OTEL gRPC exporter (for ClickHouse)
- Interceptors for automatic instrumentation of Ollama API calls

#### 1.2 Data Export Pipeline
Create exporters that push metrics to both databases:

**ClickHouse Exporter** (`ollama_local_serve/exporters/clickhouse_exporter.py`):
- Batch metrics at configurable intervals (default: 5 seconds)
- Create optimized table schema for time-series data
- Use ReplacingMergeTree engine for efficient updates
- Auto-create tables if they don't exist
- Handle retries and connection failures gracefully

**PostgreSQL Exporter** (`ollama_local_serve/exporters/postgres_exporter.py`):
- Use SQLAlchemy with asyncio support
- TimescaleDB extension for time-series optimization
- Schema with proper indexes for fast queries
- Connection pooling with retry logic

**Shared Interface** (`ollama_local_serve/exporters/base.py`):
- Abstract base class for exporters
- Common retry/error handling logic

#### 1.3 Enhanced OllamaService
Modify existing `OllamaService` class:
- Integrate metrics collection into existing methods (start, stop, health_check, get_models)
- Add token tracking per request
- Add timing instrumentation
- Initialize exporters on service creation
- Add configuration for which exporters to use

**New parameters in `NetworkConfig`:**
- `enable_instrumentation: bool = True`
- `exporter_type: str = "clickhouse"` (options: "clickhouse", "postgres", "both")
- `metrics_export_interval: int = 5` (seconds)

---

### Phase 2: React Dashboard

#### 2.1 Frontend Application (`frontend/`)
Build a modern, responsive React dashboard with:

**Layout Structure:**
- Header with service status indicator
- Real-time stats cards (4 main metrics)
- Time-series chart for trends (last 1 hour, 6 hours, 24 hours)
- Requests/logs table with filtering
- Model performance breakdown

**Dashboard Pages:**
1. **Overview Tab** (default):
   - Total tokens generated (all-time)
   - Average tokens/second (last hour)
   - Service uptime
   - Current error count
   - Mini charts for tokens and latency trends

2. **Performance Tab**:
   - Latency heatmap/line chart
   - Throughput graph
   - Model comparison
   - Resource utilization (CPU/Memory)

3. **Logs Tab**:
   - Request log table with columns: timestamp, model, tokens, latency, status
   - Filters by model, status, time range
   - Export to CSV

**Technical Requirements:**
- Use React hooks (useState, useEffect, useContext)
- Integrate Recharts for visualization
- Fetch data from `/api/stats` endpoint (see Phase 3)
- Auto-refresh every 5 seconds
- Responsive design (mobile-friendly)
- Dark mode support (optional but nice-to-have)
- Use TailwindCSS for styling

#### 2.2 Frontend Project Structure
```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── StatsCard.jsx
│   │   ├── TrendChart.jsx
│   │   ├── RequestLog.jsx
│   │   ├── ModelComparison.jsx
│   │   └── Header.jsx
│   ├── pages/
│   │   ├── Overview.jsx
│   │   ├── Performance.jsx
│   │   └── Logs.jsx
│   ├── hooks/
│   │   ├── useFetchStats.js
│   │   └── useAutoRefresh.js
│   ├── utils/
│   │   ├── api.js
│   │   └── formatters.js
│   ├── App.jsx
│   └── index.jsx
├── package.json
└── vite.config.js (or similar)
```

---

### Phase 3: FastAPI Backend API Server

#### 3.1 API Service (`ollama_local_serve/api/`)
Create a FastAPI application that serves metrics to the frontend:

**Endpoints:**

```
GET /api/stats/current
  - Returns latest metrics as JSON
  - Response: {tokens_total, tokens_per_sec, uptime_hours, error_count}

GET /api/stats/history?time_range=1h|6h|24h&granularity=1m|5m|1h
  - Returns time-series data for charting
  - Response: [{timestamp, tokens_total, latency_ms, throughput}, ...]

GET /api/stats/logs?limit=100&offset=0&status=success|error
  - Returns paginated request logs
  - Response: {total, logs: [{id, timestamp, model, tokens, latency, status}, ...]}

GET /api/models
  - Returns list of available models with stats
  - Response: [{model_name, requests_count, avg_latency}, ...]

GET /api/health
  - Service health check
  - Response: {status: "healthy"|"degraded"|"unhealthy"}

POST /api/config
  - Allow runtime configuration changes (optional)
```

#### 3.2 API Implementation Details
- Use FastAPI with async/await
- Connect to ClickHouse/PostgreSQL for data queries
- Implement proper error handling and logging
- Add CORS for frontend access
- Rate limiting (optional but recommended)
- Cache frequently accessed queries (Redis optional)

#### 3.3 Integration with OllamaService
- API service should be runnable independently or embedded
- Configuration via environment variables
- Graceful shutdown handling

---

### Phase 4: Docker Compose Orchestration

#### 4.1 Docker Compose Configuration (`docker-compose.yml`)
Define complete local stack with:

**Services:**

1. **ollama** (Existing Ollama service)
   - Image: ollama/ollama:latest
   - Ports: 11434:11434
   - Volumes: ollama-data:/root/.ollama
   - Environment: OLLAMA_HOST=0.0.0.0:11434

2. **clickhouse** (Time-series database)
   - Image: clickhouse/clickhouse-server:latest
   - Ports: 8123:8123 (HTTP), 9000:9000 (native)
   - Environment: CLICKHOUSE_DB=ollama_metrics
   - Volumes: clickhouse-data:/var/lib/clickhouse
   - Init script to create tables

3. **postgres** (Alternative database)
   - Image: postgres:15-alpine
   - Ports: 5432:5432
   - Environment: POSTGRES_DB=ollama_metrics
   - Volumes: postgres-data:/var/lib/postgresql/data
   - Init scripts for TimescaleDB setup

4. **ollama-monitor** (Python monitoring service)
   - Build: Dockerfile in project root
   - Depends on: ollama, clickhouse, postgres
   - Environment variables for configuration
   - Port: 8000 (for API)
   - Volumes: ./ollama_local_serve:/app/ollama_local_serve

5. **frontend** (React dashboard)
   - Build: Dockerfile in frontend/ directory
   - Ports: 3000:3000
   - Depends on: ollama-monitor
   - Environment: REACT_APP_API_URL=http://localhost:8000

**Volumes:**
- ollama-data
- clickhouse-data
- postgres-data

**Networks:**
- Create custom network for inter-service communication

#### 4.2 Dockerfiles

**Main Dockerfile** (Project root)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-api.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "ollama_local_serve.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile** (`frontend/Dockerfile`)
```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```

---

### Phase 5: Database Initialization & Schemas

#### 5.1 ClickHouse Schema (`schemas/clickhouse_init.sql`)
Create optimized table structure:

```sql
-- Main metrics table
CREATE TABLE IF NOT EXISTS ollama_metrics (
    timestamp DateTime,
    service_name String,
    metric_type String,  -- 'request', 'system', 'model'
    metric_name String,
    metric_value Float64,
    metadata String,  -- JSON with additional context
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_metric metric_type TYPE set(1) GRANULARITY 1
) ENGINE = ReplacingMergeTree()
ORDER BY (timestamp, service_name, metric_type)
PARTITION BY toYYYYMMDD(timestamp);

-- Request logs table
CREATE TABLE IF NOT EXISTS request_logs (
    request_id String,
    timestamp DateTime,
    model String,
    tokens_generated UInt32,
    latency_ms UInt32,
    status String,  -- 'success', 'error'
    error_message Nullable(String),
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_model model TYPE set(1) GRANULARITY 1
) ENGINE = MergeTree()
ORDER BY (timestamp, model)
PARTITION BY toYYYYMMDD(timestamp);
```

#### 5.2 PostgreSQL Schema (`schemas/postgres_init.sql`)
With TimescaleDB for optimization:

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Main metrics table
CREATE TABLE IF NOT EXISTS ollama_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value FLOAT NOT NULL,
    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('ollama_metrics', 'timestamp', if_not_exists => TRUE);
CREATE INDEX ON ollama_metrics (service_name, timestamp DESC);
CREATE INDEX ON ollama_metrics (metric_type, timestamp DESC);

-- Request logs table
CREATE TABLE IF NOT EXISTS request_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    model VARCHAR(255) NOT NULL,
    tokens_generated INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT
);

SELECT create_hypertable('request_logs', 'timestamp', if_not_exists => TRUE);
CREATE INDEX ON request_logs (model, timestamp DESC);
CREATE INDEX ON request_logs (status, timestamp DESC);
```

---

### Phase 6: Configuration & Environment

#### 6.1 Environment Variables (`.env.example`)
```env
# Ollama Configuration
OLLAMA_HOST=ollama:11434
OLLAMA_MODEL=mistral

# Instrumentation
ENABLE_INSTRUMENTATION=true
METRICS_EXPORT_INTERVAL=5

# Database Selection (clickhouse, postgres, or both)
EXPORTER_TYPE=clickhouse

# ClickHouse Configuration
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=ollama_metrics

# PostgreSQL Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=ollama_metrics

# API Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_LOG_LEVEL=info

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_REFRESH_INTERVAL=5000
```

#### 6.2 Configuration Management (`ollama_local_serve/config.py`)
- Load from environment variables with validation
- Support for multiple environments (dev, staging, prod)
- Type-safe configuration using Pydantic

---

## 🏗️ Detailed Implementation Steps

### Step 1: Core Instrumentation
1. Create `ollama_local_serve/instrumentation/` package
2. Implement `MetricsProvider` class
3. Create meter and counters for each metric
4. Update `OllamaService` to call metrics collection methods

### Step 2: Exporters
1. Create base exporter interface
2. Implement ClickHouse exporter with batch processing
3. Implement PostgreSQL exporter
4. Test both exporters with mock data

### Step 3: API Server
1. Create FastAPI application
2. Implement all endpoints with proper query logic
3. Add database connection pooling
4. Implement proper error handling and logging

### Step 4: Frontend Dashboard
1. Setup React project with Vite
2. Create all dashboard components
3. Implement data fetching with auto-refresh
4. Add styling with TailwindCSS

### Step 5: Docker Setup
1. Create Dockerfiles for each service
2. Write docker-compose.yml with all services
3. Create initialization scripts for databases
4. Add volumes and networking

### Step 6: Testing & Documentation
1. Write integration tests
2. Create comprehensive README
3. Add deployment instructions
4. Create example monitoring scenarios

---

## 📦 Dependencies to Add

### Backend (`requirements-api.txt`):
```
fastapi==0.104.1
uvicorn==0.24.0
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp==0.41b0
clickhouse-driver==0.4.6
asyncpg==0.29.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-dotenv==1.0.0
```

### Frontend (`package.json`):
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.10.3",
    "axios": "^1.6.0",
    "tailwindcss": "^3.3.6"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0"
  }
}
```

---

## 🎯 Key Design Decisions

1. **OTEL Integration**: Use OpenTelemetry for industry-standard observability
2. **Dual Database Support**: Allow users to choose ClickHouse (columnar, fast) or PostgreSQL (simpler setup)
3. **Docker Compose**: Make local development a single `docker-compose up` command
4. **Async/Await**: Maintain async patterns throughout for performance
5. **Type Safety**: Use Pydantic for validation
6. **Modular Exporters**: Easy to add new exporters (e.g., Prometheus, Datadog)

---

## 🚀 Success Criteria

✅ Complete backend instrumentation working  
✅ Both database exporters functional  
✅ FastAPI server running with all endpoints  
✅ React dashboard displaying real-time metrics  
✅ Docker Compose stack deployable with `docker-compose up`  
✅ All services healthy and communicating  
✅ Example data flowing through pipeline  
✅ Documentation for setup and usage  
✅ All code follows existing project patterns  

---

## 📝 Additional Notes

- **Backward Compatibility**: Ensure instrumentation can be disabled
- **Performance**: Metrics collection should have negligible overhead
- **Testing**: Include unit tests for exporters and API endpoints
- **Error Handling**: Graceful degradation if databases are unavailable
- **Extensibility**: Design for easy addition of new metrics/exporters
- **Documentation**: Comprehensive docstrings and API documentation

---

## 🔄 Deployment Workflow (Design, Build, Deploy, Repeat)

1. **Design**: Architecture and schema validation ✓ (this prompt)
2. **Build**: Implementation of all components
3. **Deploy**: Docker Compose deployment to local environment
4. **Test**: Verify all metrics flow and dashboard works
5. **Repeat**: Iterate based on feedback, add new metrics/visualizations

This follows your philosophy of rapid iteration with clean abstractions!
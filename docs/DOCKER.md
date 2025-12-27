# Docker Deployment

## Quick Start with Docker Compose

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

## Available Services

| Service | Port | Description |
|---------|------|-------------|
| Ollama | 11434 | LLM inference service |
| ClickHouse | 8123, 9000 | Time-series database |
| PostgreSQL | 5432 | TimescaleDB for relational storage |
| API Server | 8000 | FastAPI monitoring API |
| Dashboard | 3000 | React monitoring dashboard |

> **Note:** The API Server is named `ollama-monitor` in docker-compose files and commands. This naming reflects the service's primary purpose as a monitoring API for Ollama. When you see references to `ollama-monitor` in docker commands or compose files, this refers to the API Server listed above.

## Make Commands

### Core Commands

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

### Dependency Installation

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

### Selective Service Startup (Toggle Databases)

```bash
make up-minimal      # Start only Ollama + API (no databases, no frontend)
make up-clickhouse   # Start full stack with ClickHouse (includes frontend)
make up-postgres     # Start full stack with PostgreSQL (includes frontend)

# Or use environment variables to toggle services (with up-selective target):
make up-selective ENABLE_CLICKHOUSE=false    # Disable ClickHouse
make up-selective ENABLE_POSTGRES=false      # Disable PostgreSQL
make up-selective ENABLE_FRONTEND=false      # Disable frontend dashboard
```

### Local Development (without Docker)

```bash
make run-api        # Run API server locally (port 8000)
make run-frontend   # Run frontend dev server locally (port 5173)
make run-local      # Run both API and frontend in parallel
```

## Environment Setup Walkthrough

### Step 1: Clone and Navigate

```bash
git clone https://github.com/AbhinaavRamesh/ollama-local-serve.git
cd ollama-local-serve
```

### Step 2: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your settings (optional)
nano .env
```

**Key environment variables:**

```bash
# Ollama Configuration
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=120

# Database: Choose exporter type
ENABLE_INSTRUMENTATION=true
EXPORTER_TYPE=clickhouse  # Options: clickhouse, postgres, both, none

# ClickHouse Settings (if using)
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=ollama_metrics
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=

# PostgreSQL Settings (if using)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DATABASE=ollama_metrics
POSTGRES_USER=ollama
POSTGRES_PASSWORD=ollama_secure_password

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=*

# Frontend
VITE_API_URL=http://localhost:8000
```

### Step 3: Initialize and Start

```bash
# Install dependencies (one-time)
make install

# Initialize environment (creates volumes, etc.)
make init

# Start all services
make up

# Verify all services are running
docker compose ps
```

### Step 4: Verify Services

```bash
# Check health
make health

# View logs for all services
make logs

# View logs for specific service
docker compose logs -f ollama-monitor
docker compose logs -f ollama
docker compose logs -f frontend
```

### Step 5: Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:3000 | Monitor and manage Ollama |
| API | http://localhost:8000 | REST API endpoints |
| Ollama | http://localhost:11434 | Direct Ollama access |
| ClickHouse | http://localhost:8123 | Database UI (if enabled) |
| PostgreSQL | localhost:5432 | Database connection (if enabled) |

## Common Usage Examples

### Pull and Test a Model

```bash
# Use the dashboard chat interface (easiest)
# 1. Open http://localhost:3000
# 2. Click "Pull Model"
# 3. Select a model like "llama3.2"
# 4. Start chatting

# OR use the API directly
curl -X POST http://localhost:8000/api/ollama/pull \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2"}'
```

### Monitor Performance

```bash
# View current stats
curl http://localhost:8000/api/stats/current | python3 -m json.tool

# View historical stats
curl http://localhost:8000/api/stats/history | python3 -m json.tool

# View request logs
curl http://localhost:8000/api/stats/logs | python3 -m json.tool
```

### Generate Load for Testing

```bash
# Send parallel requests to test performance
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"model": "llama3.2", "prompt": "Tell me about yourself"}' &
done
wait

# Monitor metrics in dashboard: http://localhost:3000
```

### Use Only Specific Databases

```bash
# ClickHouse only (fast time-series)
make up-clickhouse

# PostgreSQL only (relational queries)
make up-postgres

# No databases (minimal stack - Ollama + API + Frontend only)
make up-minimal
```

### Custom Configuration

```bash
# Override environment variables at runtime
OLLAMA_MODEL=mistral make up

# Use custom docker-compose file
docker compose -f docker-compose.yml -f custom-compose.yml up

# Run with specific services only
docker compose up ollama ollama-monitor frontend
```

## Troubleshooting Docker Deployments

### Services Not Starting

```bash
# Check Docker is running
docker ps

# View error logs
docker compose logs

# Rebuild images
docker compose build --no-cache

# Remove old containers and restart
docker compose down -v
docker compose up
```

### Port Already in Use

```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process (replace PID)
kill -9 <PID>

# Or use different ports
docker compose -e "API_PORT=8001" up
```

### Database Connection Issues

```bash
# Test ClickHouse connection
docker compose exec clickhouse clickhouse-client --query "SELECT 1"

# Test PostgreSQL connection
docker compose exec postgres psql -U ollama -d ollama_metrics -c "SELECT 1"

# Check database health
curl http://localhost:8000/api/health | python3 -m json.tool
```

### Memory or Resource Issues

```bash
# Check container resource usage
docker stats

# Limit container memory
docker compose down
# Edit docker-compose.yml and add:
# services:
#   ollama:
#     deploy:
#       resources:
#         limits:
#           memory: 4G

docker compose up
```

## Cleanup and Maintenance

```bash
# Stop all services
make down

# Stop and remove volumes (clean state)
make clean

# Remove unused Docker resources
docker system prune

# View Docker disk usage
docker system df
```

# Development Guide

## Setup

### Check Dependencies

```bash
# Check what dependencies you have installed
make check-deps
```

### Installation Options

#### Option 1: Install All Dependencies at Once

```bash
make install
```

#### Option 2: Use Virtual Environment for Python

```bash
make install-python-venv   # Creates .venv and installs deps
source .venv/bin/activate  # Activate the virtual environment
make install-frontend      # Install frontend deps
```

#### Option 3: Manual Setup

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"
cd frontend && npm install
```

#### Optional: Install Database Clients

```bash
# Install database clients for local debugging
make install-db-clients
```

## Code Quality

### Format Code

```bash
black ollama_local_serve/
```

### Lint Code

```bash
ruff check ollama_local_serve/
```

### Type Checking

```bash
mypy ollama_local_serve/
```

### Run Tests

```bash
pytest
```

## Development Mode

### Option 1: Use Docker (Hot Reloading Enabled)

```bash
make dev
```

Or manually:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Option 2: Run Locally Without Docker

```bash
make run-local   # Runs both API and frontend
```

Or run separately:

```bash
# Run API locally (update the module path if needed):
python -m ollama_local_serve.api  # API on http://localhost:8000
make run-frontend  # Frontend on http://localhost:5173
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

## Common Development Workflows

### Workflow 1: Working on API Features

```bash
# Start the development environment
make dev

# In another terminal, watch for changes
# The container will auto-reload on file changes

# View API logs
docker compose logs -f ollama-monitor

# Test your API changes
curl http://localhost:8000/api/health

# Make a change to api/server.py
# Change is automatically reloaded
```

### Workflow 2: Frontend Development with Hot Reload

```bash
# Terminal 1: Start Ollama and API with hot-reload
make run-local

# Terminal 2: Start frontend with Vite dev server
cd frontend
npm run dev

# Frontend will be at http://localhost:5173 with hot reload
# API will be at http://localhost:8000

# Make changes to React components - they update instantly
```

### Workflow 3: Testing Database Changes

```bash
# Start stack with specific database
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Connect to PostgreSQL
docker compose exec postgres psql -U ollama -d ollama_metrics

# Run test queries
SELECT * FROM request_logs;

# Or test ClickHouse
docker compose exec clickhouse clickhouse-client
SELECT * FROM requests;

# Modify schema and test
# Changes to database code will require service restart
```

### Workflow 4: Testing New Endpoints

```bash
# Add new endpoint to api/server.py
# Example: add /api/custom-endpoint

# Start services
make run-api

# Test the endpoint
curl http://localhost:8000/api/custom-endpoint

# Debug with print statements or debugger
# Check logs: check stdout/docker logs

# Test with curl or Postman
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2", "prompt": "test"}'
```

### Workflow 5: Full Stack Testing

```bash
# Start everything with docker-compose
make up

# Run your local test suite
pytest

# View API metrics
curl http://localhost:8000/api/stats/current | python3 -m json.tool

# Check frontend at http://localhost:3000

# View metrics in ClickHouse
docker compose exec clickhouse clickhouse-client \
  --query "SELECT * FROM requests LIMIT 10"
```

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_service.py
```

### Run Tests with Coverage

```bash
pytest --cov=ollama_local_serve
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Specific Test

```bash
pytest tests/test_service.py::test_health_check
```

## Debugging

### Using Python Debugger

```python
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

### Using Docker Debugger

```bash
# Run with interactive terminal
docker compose run --rm ollama-monitor python -m pdb -c continue \
  -m ollama_local_serve.api
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f ollama-monitor

# Last 50 lines
docker compose logs --tail=50 ollama-monitor

# Filter logs
docker compose logs ollama-monitor | grep "error"
```

## Performance Profiling

### Profile CPU Usage

```python
import cProfile
import pstats
from io import StringIO

pr = cProfile.Profile()
pr.enable()

# Your code here
response = await service.generate("llama3.2", "test prompt")

pr.disable()
s = StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(10)  # Top 10 functions
print(s.getvalue())
```

### Memory Profiling

```bash
# Install memory_profiler
pip install memory-profiler

# Add decorator to function
from memory_profiler import profile

@profile
def my_function():
    # Your code
    pass

# Run with profiler
python -m memory_profiler your_script.py
```

## Git Workflow

### Creating a Feature Branch

```bash
git checkout -b feature/my-feature
```

### Committing Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add feature: describe what was added"

# Push to remote
git push origin feature/my-feature
```

### Creating a Pull Request

```bash
# After pushing, create a PR on GitHub
# Use descriptive title and include:
# - What changed
# - Why it changed
# - Testing performed
```

## Code Quality Checks

### Before Committing

Run all quality checks:

```bash
# Format code
black ollama_local_serve/

# Lint code
ruff check ollama_local_serve/

# Type check
mypy ollama_local_serve/

# Run tests
pytest
```

### Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
black ollama_local_serve/
ruff check ollama_local_serve/
mypy ollama_local_serve/
pytest
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Adding Dependencies

### Python Dependencies

```bash
# Add to requirements or pyproject.toml
pip install new-package

# Update requirements
pip freeze > requirements.txt

# Or use poetry
poetry add new-package
```

### Frontend Dependencies

```bash
cd frontend
npm install new-package
npm update
```

### Database Dependencies

For ClickHouse or PostgreSQL schema changes, update:
- `schemas/clickhouse_init.sql`
- `schemas/postgres_init.sql`

## Documentation Updates

When making code changes, update docs:

1. **API changes** → Update `docs/API_REFERENCE.md`
2. **Configuration changes** → Update `docs/CONFIGURATION.md`
3. **New features** → Add to `docs/` and reference in README
4. **Troubleshooting** → Add to relevant doc file

## Release Process

```bash
# Update version in pyproject.toml
# Create changelog entry

# Create a release tag
git tag v0.2.0

# Push tag
git push origin v0.2.0

# GitHub Actions will build and publish to PyPI
```

## Useful Commands Reference

| Command | Purpose |
|---------|---------|
| `make help` | Show all available make commands |
| `make install` | Install all dependencies |
| `make dev` | Start dev environment with hot-reload |
| `make run-local` | Run API and frontend locally |
| `make lint` | Run linting checks |
| `make format` | Format code with black |
| `make type-check` | Run mypy type checking |
| `make test` | Run test suite |
| `make clean` | Remove containers and volumes |
| `docker compose logs -f` | View real-time logs |
| `python -m pdb -c continue your_script.py` | Debug script |

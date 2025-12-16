# =============================================================================
# Ollama Local Serve - Makefile
# =============================================================================
# Common operations for managing the Docker Compose stack

# =============================================================================
# Configuration - Toggle services (set to 'true' or 'false')
# =============================================================================
ENABLE_CLICKHOUSE ?= true
ENABLE_POSTGRES ?= true
ENABLE_FRONTEND ?= true

# Detect OS for platform-specific commands
UNAME_S := $(shell uname -s)

.PHONY: help build up down restart logs shell clean dev prod pull status health init \
        install install-python install-frontend install-db-clients install-clickhouse-client install-postgres-client \
        up-minimal up-clickhouse up-postgres check-deps install-python-venv run-api run-frontend run-local

# Default target
help:
	@echo "Ollama Local Serve - Docker Compose Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Core Targets:"
	@echo "  help      - Show this help message"
	@echo "  init      - Initialize environment (copy .env, create dirs)"
	@echo "  build     - Build all Docker images"
	@echo "  up        - Start all services in detached mode"
	@echo "  down      - Stop and remove all services"
	@echo "  restart   - Restart all services"
	@echo "  logs      - View logs from all services"
	@echo "  status    - Show status of all services"
	@echo "  health    - Check health of all services"
	@echo "  shell     - Open shell in ollama-monitor container"
	@echo "  clean     - Remove all containers, volumes, and images"
	@echo "  dev       - Start development environment"
	@echo "  prod      - Start production environment"
	@echo "  pull      - Pull latest images"
	@echo ""
	@echo "Dependency Installation:"
	@echo "  install              - Install all dependencies (Python + Frontend)"
	@echo "  install-python       - Install Python dependencies"
	@echo "  install-frontend     - Install frontend (Node.js) dependencies"
	@echo "  install-db-clients   - Install database CLI clients (ClickHouse + PostgreSQL)"
	@echo "  install-clickhouse-client - Install ClickHouse client only"
	@echo "  install-postgres-client   - Install PostgreSQL client only"
	@echo "  check-deps           - Check if required dependencies are installed"
	@echo ""
	@echo "Selective Service Startup (toggle databases):"
	@echo "  up-minimal           - Start only Ollama + API (no databases)"
	@echo "  up-clickhouse        - Start with ClickHouse only (no PostgreSQL)"
	@echo "  up-postgres          - Start with PostgreSQL only (no ClickHouse)"
	@echo ""
	@echo "  You can also toggle services via environment variables:"
	@echo "    make up ENABLE_CLICKHOUSE=false"
	@echo "    make up ENABLE_POSTGRES=false"
	@echo "    make up ENABLE_FRONTEND=false"
	@echo ""
	@echo "Service-specific targets:"
	@echo "  logs-api       - View API service logs"
	@echo "  logs-frontend  - View frontend logs"
	@echo "  logs-clickhouse - View ClickHouse logs"
	@echo "  logs-postgres  - View PostgreSQL logs"
	@echo "  logs-ollama    - View Ollama logs"

# Initialize environment
init:
	@echo "Initializing environment..."
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; fi
	@mkdir -p data/clickhouse data/postgres data/ollama
	@echo "Environment initialized successfully!"

# Build all images
build:
	@echo "Building Docker images..."
	docker-compose build

# Build without cache
build-no-cache:
	@echo "Building Docker images (no cache)..."
	docker-compose build --no-cache

# Start all services
up:
	@echo "Starting all services..."
	docker-compose up -d

# Stop all services
down:
	@echo "Stopping all services..."
	docker-compose down

# Restart all services
restart:
	@echo "Restarting all services..."
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f ollama-monitor

logs-frontend:
	docker-compose logs -f frontend

logs-clickhouse:
	docker-compose logs -f clickhouse

logs-postgres:
	docker-compose logs -f postgres

logs-ollama:
	docker-compose logs -f ollama

# Show status
status:
	@echo "Service Status:"
	@docker-compose ps

# Health check
health:
	@echo "Checking service health..."
	@echo ""
	@echo "Ollama:"
	@curl -s http://localhost:11434/api/tags > /dev/null && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
	@echo ""
	@echo "ClickHouse:"
	@curl -s http://localhost:8123/ping > /dev/null && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
	@echo ""
	@echo "PostgreSQL:"
	@docker-compose exec -T postgres pg_isready -U ollama > /dev/null 2>&1 && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
	@echo ""
	@echo "API Server:"
	@curl -s http://localhost:8000/api/health > /dev/null && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
	@echo ""
	@echo "Frontend:"
	@curl -s http://localhost:3000 > /dev/null && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"

# Open shell in API container
shell:
	docker-compose exec ollama-monitor /bin/bash

shell-clickhouse:
	docker-compose exec clickhouse clickhouse-client

shell-postgres:
	docker-compose exec postgres psql -U ollama -d ollama_metrics

# Clean everything
clean:
	@echo "Cleaning up..."
	docker-compose down -v --rmi all --remove-orphans
	@echo "Cleanup complete!"

# Clean volumes only
clean-volumes:
	@echo "Removing volumes..."
	docker-compose down -v
	@echo "Volumes removed!"

# Development environment
dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-down:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Production environment
prod:
	@echo "Starting production environment..."
	docker-compose up -d --build

# Pull latest images
pull:
	@echo "Pulling latest images..."
	docker-compose pull

# Database operations
db-migrate:
	@echo "Running database migrations..."
	docker-compose exec clickhouse clickhouse-client --query="SOURCE '/docker-entrypoint-initdb.d/init.sql'"
	docker-compose exec postgres psql -U ollama -d ollama_metrics -f /docker-entrypoint-initdb.d/init.sql

db-backup:
	@echo "Backing up databases..."
	@mkdir -p backups
	@docker-compose exec clickhouse clickhouse-client --query="SELECT * FROM ollama_metrics.ollama_metrics FORMAT JSONEachRow" > backups/clickhouse_metrics_$$(date +%Y%m%d).json
	@docker-compose exec postgres pg_dump -U ollama ollama_metrics > backups/postgres_$$(date +%Y%m%d).sql
	@echo "Backups created in ./backups/"

# Model management
ollama-pull:
	@read -p "Enter model name: " model; \
	docker-compose exec ollama ollama pull $$model

ollama-list:
	docker-compose exec ollama ollama list

# Testing
test-api:
	@echo "Testing API endpoints..."
	@echo "Health check:"
	@curl -s http://localhost:8000/api/health | jq .
	@echo ""
	@echo "Current stats:"
	@curl -s http://localhost:8000/api/stats/current | jq .

# Scale services
scale-api:
	@read -p "Number of API instances: " n; \
	docker-compose up -d --scale ollama-monitor=$$n

# Resource usage
resources:
	@echo "Container Resource Usage:"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# =============================================================================
# Dependency Installation
# =============================================================================

# Install all dependencies
install: install-python install-frontend
	@echo ""
	@echo "All dependencies installed successfully!"

# Install Python dependencies
install-python:
	@echo "Installing Python dependencies..."
	@if command -v pip3 > /dev/null 2>&1; then \
		pip3 install -r requirements-api.txt; \
	elif command -v pip > /dev/null 2>&1; then \
		pip install -r requirements-api.txt; \
	else \
		echo "Error: pip not found. Please install Python first."; \
		exit 1; \
	fi
	@echo "Python dependencies installed!"

# Install Python dependencies in virtual environment
install-python-venv:
	@echo "Creating virtual environment and installing Python dependencies..."
	@python3 -m venv .venv
	@. .venv/bin/activate && pip install -r requirements-api.txt
	@echo "Python dependencies installed in .venv!"
	@echo "Activate with: source .venv/bin/activate"

# Install frontend dependencies
install-frontend:
	@echo "Installing frontend dependencies..."
	@if command -v npm > /dev/null 2>&1; then \
		cd frontend && npm install; \
	elif command -v yarn > /dev/null 2>&1; then \
		cd frontend && yarn install; \
	elif command -v pnpm > /dev/null 2>&1; then \
		cd frontend && pnpm install; \
	else \
		echo "Error: npm/yarn/pnpm not found. Please install Node.js first."; \
		exit 1; \
	fi
	@echo "Frontend dependencies installed!"

# Install all database clients
install-db-clients: install-clickhouse-client install-postgres-client
	@echo ""
	@echo "Database clients installed successfully!"

# Install ClickHouse client
install-clickhouse-client:
	@echo "Installing ClickHouse client..."
ifeq ($(UNAME_S),Darwin)
	@if command -v brew > /dev/null 2>&1; then \
		brew install --cask clickhouse || brew install clickhouse; \
	else \
		echo "Error: Homebrew not found. Install from https://clickhouse.com/docs/en/install"; \
		exit 1; \
	fi
else ifeq ($(UNAME_S),Linux)
	@if command -v apt-get > /dev/null 2>&1; then \
		sudo apt-get update && sudo apt-get install -y clickhouse-client; \
	elif command -v yum > /dev/null 2>&1; then \
		sudo yum install -y clickhouse-client; \
	else \
		echo "Please install ClickHouse client from https://clickhouse.com/docs/en/install"; \
		exit 1; \
	fi
endif
	@echo "ClickHouse client installed!"

# Install PostgreSQL client
install-postgres-client:
	@echo "Installing PostgreSQL client..."
ifeq ($(UNAME_S),Darwin)
	@if command -v brew > /dev/null 2>&1; then \
		brew install libpq && brew link --force libpq; \
	else \
		echo "Error: Homebrew not found. Install from https://www.postgresql.org/download/"; \
		exit 1; \
	fi
else ifeq ($(UNAME_S),Linux)
	@if command -v apt-get > /dev/null 2>&1; then \
		sudo apt-get update && sudo apt-get install -y postgresql-client; \
	elif command -v yum > /dev/null 2>&1; then \
		sudo yum install -y postgresql; \
	else \
		echo "Please install PostgreSQL client from https://www.postgresql.org/download/"; \
		exit 1; \
	fi
endif
	@echo "PostgreSQL client installed!"

# Check if required dependencies are installed
check-deps:
	@echo "Checking dependencies..."
	@echo ""
	@echo "Python:"
	@python3 --version 2>/dev/null || python --version 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "pip:"
	@pip3 --version 2>/dev/null || pip --version 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Node.js:"
	@node --version 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "npm:"
	@npm --version 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Docker:"
	@docker --version 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Docker Compose:"
	@docker-compose --version 2>/dev/null || docker compose version 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "ClickHouse client:"
	@clickhouse-client --version 2>/dev/null || echo "  Not found (optional - install with: make install-clickhouse-client)"
	@echo ""
	@echo "PostgreSQL client (psql):"
	@psql --version 2>/dev/null || echo "  Not found (optional - install with: make install-postgres-client)"

# =============================================================================
# Selective Service Startup (Toggle Databases)
# =============================================================================

# Determine which services to start based on toggles
define get_services
$(if $(filter true,$(ENABLE_CLICKHOUSE)),clickhouse) \
$(if $(filter true,$(ENABLE_POSTGRES)),postgres) \
$(if $(filter true,$(ENABLE_FRONTEND)),frontend) \
ollama ollama-monitor
endef

# Start with selective services
up-selective:
	@echo "Starting services (ClickHouse=$(ENABLE_CLICKHOUSE), PostgreSQL=$(ENABLE_POSTGRES), Frontend=$(ENABLE_FRONTEND))..."
	docker-compose up -d $(strip $(get_services))

# Start minimal - only Ollama and API (no databases, no frontend)
# Note: The API service is named 'ollama-monitor' in docker-compose
up-minimal:
	@echo "Starting minimal setup (Ollama + API only)..."
	@echo "Note: API (ollama-monitor service) will run without database exporters"
	docker-compose up -d ollama
	@echo "Waiting for Ollama to be healthy..."
	@sleep 5
	EXPORTER_TYPE=none docker-compose up -d ollama-monitor

# Start with ClickHouse only (no PostgreSQL)
# Note: The API service is named 'ollama-monitor' in docker-compose
up-clickhouse:
	@echo "Starting with ClickHouse only..."
	docker-compose up -d ollama clickhouse ollama-monitor frontend

# Start with PostgreSQL only (no ClickHouse)
# Note: The API service is named 'ollama-monitor' in docker-compose
up-postgres:
	@echo "Starting with PostgreSQL only..."
	EXPORTER_TYPE=postgres docker-compose up -d ollama postgres ollama-monitor frontend

# =============================================================================
# Local Development (without Docker)
# =============================================================================

# Run API server locally (requires dependencies installed)
run-api:
	@echo "Starting API server locally..."
	@echo "Make sure you have dependencies installed: make install-python"
	uvicorn ollama_local_serve.api.server:app --reload --host 0.0.0.0 --port 8000

# Run frontend locally (requires dependencies installed)
run-frontend:
	@echo "Starting frontend dev server locally..."
	@echo "Make sure you have dependencies installed: make install-frontend"
	cd frontend && npm run dev

# Run both API and frontend locally (in parallel)
run-local:
	@echo "Starting local development servers..."
	@echo "API will run on http://localhost:8000"
	@echo "Frontend will run on http://localhost:5173"
	@make -j2 run-api run-frontend

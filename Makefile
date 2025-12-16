# =============================================================================
# Ollama Local Serve - Makefile
# =============================================================================
# Common operations for managing the Docker Compose stack

.PHONY: help build up down restart logs shell clean dev prod pull status health init

# Default target
help:
	@echo "Ollama Local Serve - Docker Compose Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
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

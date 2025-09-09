.PHONY: help install build up down logs test clean setup run-local

# Default target
help:
	@echo "Praxis Python SDK - Available Commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup        - Complete setup (install deps, create dirs, copy env)"
	@echo "  make install      - Install Python dependencies with Poetry"
	@echo "  make build        - Build Docker images"
	@echo ""
	@echo "Running:"
	@echo "  make up           - Start all services with Docker Compose"
	@echo "  make down         - Stop all services"
	@echo "  make run-local    - Run agent locally (no Docker)"
	@echo ""
	@echo "Development:"
	@echo "  make logs         - View logs from all services"
	@echo "  make test         - Run test suite"
	@echo "  make clean        - Clean up generated files and containers"
	@echo ""
	@echo "Monitoring:"
	@echo "  make health       - Check health of all services"
	@echo "  make ps           - Show running containers"

# Complete setup
setup:
	@echo "Setting up Praxis Python SDK..."
	@cp -n .env.example .env || true
	@mkdir -p shared logs keys
	@poetry install
	@echo "Setup complete! Edit .env file with your OPENAI_API_KEY"
	@echo "Then run: make up"

# Install dependencies
install:
	poetry install

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	docker-compose up -d
	@echo "Services starting..."
	@sleep 5
	@make health

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# View logs for specific service
logs-%:
	docker-compose logs -f $*

# Run tests
test:
	poetry run pytest tests/

# Clean up
clean:
	docker-compose down -v
	rm -rf logs/*.log
	rm -rf keys/*.key
	rm -rf __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Run agent locally
run-local:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	poetry run praxis-agent run --config configs/orchestrator.yaml

# Check health of services
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8080/health | jq '.' || echo "Orchestrator: Not responding"
	@curl -s http://localhost:8081/health | jq '.' || echo "Worker: Not responding"
	@curl -s http://localhost:3002/health || echo "MCP Server: Not responding"
	@echo ""
	@echo "P2P Status:"
	@curl -s http://localhost:8080/agent/card | jq '.peer_id, .listen_addresses' || echo "P2P: Not available"

# Show running containers
ps:
	docker-compose ps

# Shell into a container
shell-%:
	docker-compose exec $* /bin/bash

# Run orchestrator only
run-orchestrator:
	docker-compose up orchestrator

# Run worker only
run-worker:
	docker-compose up worker-filesystem

# Run MCP server only
run-mcp:
	docker-compose up mcp-filesystem

# Test P2P connectivity
test-p2p:
	@echo "Testing P2P connectivity..."
	curl -X POST http://localhost:8080/agent/execute \
		-H "Content-Type: application/json" \
		-d '{"command": "list /"}'

# Test DSL execution with LLM
test-dsl:
	@echo "Testing DSL with LLM..."
	curl -X POST http://localhost:8080/agent/execute \
		-H "Content-Type: application/json" \
		-d '{"command": "create a test file with hello world content"}'

# Test A2A protocol
test-a2a:
	@echo "Testing A2A protocol..."
	curl -X POST http://localhost:8080/tasks \
		-H "Content-Type: application/json" \
		-d '{"method": "message/send", "params": {"message": {"parts": [{"type": "text", "content": "Hello from A2A"}]}}}'

# Development mode with hot reload
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Format code
fmt:
	poetry run black src/
	poetry run isort src/

# Lint code
lint:
	poetry run ruff check src/
	poetry run mypy src/

# Full check (format, lint, test)
check: fmt lint test

# Update dependencies
update:
	poetry update

# Show configuration
show-config:
	@cat configs/orchestrator.yaml

# Initialize example files in shared directory
init-examples:
	@echo "Creating example files in shared directory..."
	@echo "Hello, Praxis!" > shared/hello.txt
	@echo '{"name": "Praxis", "version": "0.1.0"}' > shared/config.json
	@mkdir -p shared/data
	@echo "Test data" > shared/data/test.txt
	@echo "Example files created in ./shared/"
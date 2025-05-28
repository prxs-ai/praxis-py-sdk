.PHONY: run-locally test-imports test-libp2p run-relay run-registry docker-build docker-up docker-down docker-logs

export PYTHONPATH := $(shell pwd)/src
export ENV_FILE := .env

run-locally:
	@echo "Running FastAPI app locally with .env loaded..."
	env $$(cat .env | xargs) python entrypoint.py

test-imports:
	@echo "Testing libp2p imports..."
	python tests/test_imports.py

test-libp2p:
	@echo "Running libp2p E2E test..."
	cd tests/e2e && python test_libp2p_integration.py

run-relay:
	@echo "Starting mock relay node..."
	python tests/e2e/mock_relay_node.py

run-registry:
	@echo "Starting mock registry..."
	cd tests/e2e && python -c "from test_libp2p_integration import run_mock_registry; import asyncio; asyncio.run(run_mock_registry())"

# Docker commands
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-up:
	@echo "Starting services with libp2p..."
	./start-with-libp2p.sh

docker-down:
	@echo "Stopping all services..."
	docker-compose -f docker-compose.yaml -f docker-compose.override.yaml down

docker-logs:
	@echo "Showing logs for all services..."
	docker-compose -f docker-compose.yaml -f docker-compose.override.yaml logs -f

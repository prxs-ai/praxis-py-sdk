# Praxis Python SDK Integration Tests

This directory contains comprehensive integration tests for the Praxis Python SDK's multi-agent system.

## Test Categories

### 1. Multi-Agent Communication (`test_multi_agent_communication.py`)
- Agent health checks and service availability
- A2A card exchange and capability discovery
- DSL command translation to A2A protocol
- Inter-agent task delegation
- Complex multi-agent workflows
- Error handling and recovery
- Concurrent task execution

### 2. P2P Connectivity (`test_p2p_connectivity.py`)
- P2P service startup validation
- Peer discovery via mDNS
- Agent card structure validation
- Remote tool invocation over P2P
- Capability advertisement
- Connection resilience and recovery
- Protocol versioning
- Security handshake validation

### 3. A2A Protocol Compliance (`test_a2a_protocol.py`)
- A2A message structure validation
- Complete task lifecycle testing
- Error handling and JSON-RPC compliance
- Context management and conversation flow
- Multipart message processing
- Tool result formatting
- Batch operations
- Protocol headers and metadata

### 4. Tool Execution (`test_tool_execution.py`)
- MCP filesystem server integration
- Direct MCP tool invocation
- Dagger-based Python execution
- Container isolation and security
- Tool error handling and recovery
- Concurrent tool execution
- Capability discovery and matching

### 5. WebSocket Connectivity (`test_websocket_connectivity.py`)
- Basic WebSocket connection testing
- DSL command streaming
- Workflow execution via WebSocket
- Chat-like interface testing
- Concurrent connections
- Error handling
- Large message handling
- Heartbeat and keep-alive
- Message ordering and sequencing

## Running Tests

### Prerequisites
1. Docker and Docker Compose installed
2. Environment variables configured (copy `.env.example` to `.env`)
3. All services running (`make up` or `docker-compose up`)

### Run All Integration Tests
```bash
make test-integration
```

### Run Specific Test Categories
```bash
# P2P connectivity tests
make test-p2p

# A2A protocol tests
make test-a2a

# Tool execution tests
make test-tools

# WebSocket connectivity tests
make test-websocket

# Multi-agent communication tests
make test-multi-agent
```

### Run Individual Test Files
```bash
# Using Docker Compose
docker-compose run --rm test_runner python -m pytest tests/integration/test_p2p_connectivity.py -v

# Using Poetry (if running locally)
poetry run pytest tests/integration/test_p2p_connectivity.py -v
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.integration` - All integration tests
- `@pytest.mark.p2p` - P2P communication tests
- `@pytest.mark.a2a` - A2A protocol tests
- `@pytest.mark.mcp` - MCP integration tests
- `@pytest.mark.dagger` - Dagger execution tests
- `@pytest.mark.websocket` - WebSocket communication tests
- `@pytest.mark.slow` - Long-running tests

### Filter Tests by Marker
```bash
# Run only P2P tests
docker-compose run --rm test_runner python -m pytest -m p2p -v

# Run only fast tests (exclude slow ones)
docker-compose run --rm test_runner python -m pytest -m "not slow" -v

# Run MCP and Dagger tests
docker-compose run --rm test_runner python -m pytest -m "mcp or dagger" -v
```

## Test Configuration

### Environment Variables
Tests use environment variables to connect to services:

- `PRAXIS_ORCHESTRATOR_URL` - Orchestrator HTTP endpoint (default: http://localhost:8000)
- `PRAXIS_WORKER_FS_URL` - Filesystem worker endpoint (default: http://localhost:8001)  
- `PRAXIS_WORKER_ANALYTICS_URL` - Analytics worker endpoint (default: http://localhost:8002)
- `PRAXIS_MCP_FILESYSTEM_URL` - MCP filesystem server (default: http://localhost:3000)
- `PRAXIS_SHARED_DIR` - Shared directory path (default: ./shared)

### Test Fixtures
The `conftest.py` file provides common fixtures:

- `wait_for_services` - Waits for all services to be healthy
- `orchestrator_client`, `worker_fs_client`, etc. - HTTP clients for each service
- `orchestrator_ws` - WebSocket connection to orchestrator
- `test_helper` - Utility class with common test operations
- `setup_test_files` - Creates test files in shared directory
- `sample_test_data` - Provides sample data for tests

## Expected Test Behavior

### Containerized Environment Considerations
These tests run in a containerized environment, which may affect certain behaviors:

1. **P2P Discovery**: May be limited due to Docker networking constraints
2. **Timing**: Some tests include generous timeouts to account for container startup
3. **File Operations**: All file operations occur in the shared volume
4. **Network Isolation**: Services communicate through Docker's internal network

### Graceful Degradation
Tests are designed to handle partial system functionality:

- P2P discovery failures don't fail the entire test suite
- Missing API keys (OpenAI, Apify) cause specific tests to be skipped
- Dagger execution issues are logged but don't crash tests
- WebSocket connection failures are handled gracefully

## Test Output and Debugging

### Verbose Output
All tests include descriptive print statements to aid in debugging:
```bash
docker-compose run --rm test_runner python -m pytest tests/integration/ -v -s
```

### Service Logs
Check service logs for debugging:
```bash
# All services
make logs

# Specific service
make orchestrator-logs
make worker-fs-logs
make worker-analytics-logs
make mcp-logs
```

### Test Debugging
For interactive debugging, you can shell into the test container:
```bash
docker-compose run --rm test_runner /bin/bash
cd /app
python -m pytest tests/integration/test_p2p_connectivity.py::test_peer_discovery -v -s
```

## Troubleshooting

### Common Issues

1. **Services Not Ready**
   - Increase wait times in `wait_for_services` fixture
   - Check service health with `make health`

2. **P2P Tests Failing**
   - P2P discovery may be limited in Docker
   - Check network configuration in docker-compose.yml

3. **Dagger Tests Failing**
   - Ensure Docker socket is properly mounted
   - Check if Dagger service is available

4. **WebSocket Connection Issues**
   - Verify WebSocket endpoints are accessible
   - Check firewall and network policies

5. **File Permission Issues**
   - Ensure shared volume has correct permissions
   - Check user/group settings in Dockerfile

### Getting Help
- Review service logs with `make logs`
- Run health checks with `make health`
- Check configuration with `make validate-config`
- Use `make quick-test` for basic connectivity validation

## Contributing

When adding new integration tests:

1. Use appropriate pytest markers
2. Include descriptive print statements for debugging
3. Handle partial system failures gracefully
4. Add appropriate timeouts for network operations
5. Clean up test artifacts when possible
6. Update this README with new test categories
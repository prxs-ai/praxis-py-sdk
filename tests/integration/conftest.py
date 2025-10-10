"""Configuration and fixtures for integration tests"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import pytest
import websockets

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
ORCHESTRATOR_URL = os.getenv("PRAXIS_ORCHESTRATOR_URL", "http://localhost:8000")
WORKER_FS_URL = os.getenv("PRAXIS_WORKER_FS_URL", "http://localhost:8001")
WORKER_ANALYTICS_URL = os.getenv("PRAXIS_WORKER_ANALYTICS_URL", "http://localhost:8002")
MCP_FILESYSTEM_URL = os.getenv("PRAXIS_MCP_FILESYSTEM_URL", "http://localhost:3000")
SHARED_DIR = os.getenv("PRAXIS_SHARED_DIR", "./shared")

# WebSocket URLs
ORCHESTRATOR_WS = ORCHESTRATOR_URL.replace("http://", "ws://") + "/ws/workflow"
WORKER_FS_WS = WORKER_FS_URL.replace("http://", "ws://") + "/ws/workflow"
WORKER_ANALYTICS_WS = WORKER_ANALYTICS_URL.replace("http://", "ws://") + "/ws/workflow"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def http_client():
    """HTTP client for API requests"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client


@pytest.fixture
async def orchestrator_client():
    """HTTP client specifically for orchestrator"""
    async with httpx.AsyncClient(base_url=ORCHESTRATOR_URL, timeout=60.0) as client:
        yield client


@pytest.fixture
async def worker_fs_client():
    """HTTP client specifically for filesystem worker"""
    async with httpx.AsyncClient(base_url=WORKER_FS_URL, timeout=60.0) as client:
        yield client


@pytest.fixture
async def worker_analytics_client():
    """HTTP client specifically for analytics worker"""
    async with httpx.AsyncClient(base_url=WORKER_ANALYTICS_URL, timeout=60.0) as client:
        yield client


@pytest.fixture
async def mcp_client():
    """HTTP client specifically for MCP filesystem server"""
    async with httpx.AsyncClient(base_url=MCP_FILESYSTEM_URL, timeout=60.0) as client:
        yield client


@pytest.fixture
def shared_dir():
    """Path to shared directory"""
    path = Path(SHARED_DIR)
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture
async def orchestrator_ws():
    """WebSocket connection to orchestrator"""
    try:
        async with websockets.connect(ORCHESTRATOR_WS) as websocket:
            yield websocket
    except Exception as e:
        logger.error(f"Failed to connect to orchestrator WebSocket: {e}")
        pytest.skip("Orchestrator WebSocket not available")


@pytest.fixture
def sample_test_data():
    """Sample test data for various tests"""
    return {
        "test_file_content": "Hello, World!\nThis is a test file.",
        "test_json_data": {
            "name": "Test User",
            "age": 30,
            "skills": ["Python", "JavaScript", "Docker"],
            "active": True,
        },
        "test_csv_data": "name,age,city\nAlice,25,New York\nBob,30,London\nCharlie,35,Tokyo",
        "test_analysis_script": '''
import json
import sys
from pathlib import Path

def analyze_data(input_file, output_file=None):
    """Simple data analysis script"""
    try:
        with open(input_file, 'r') as f:
            content = f.read()

        analysis = {
            "file_size": len(content),
            "line_count": len(content.splitlines()),
            "word_count": len(content.split()),
            "character_count": len(content)
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2)

        return analysis

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "/shared/test_input.txt"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "/shared/analysis_result.json"

    result = analyze_data(input_file, output_file)
    print(json.dumps(result, indent=2))
''',
    }


@pytest.fixture
async def wait_for_services():
    """Wait for all services to be ready"""
    services = [
        (ORCHESTRATOR_URL, "orchestrator"),
        (WORKER_FS_URL, "worker-filesystem"),
        (WORKER_ANALYTICS_URL, "worker-analytics"),
        (MCP_FILESYSTEM_URL, "mcp-filesystem"),
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for url, name in services:
            max_retries = 30
            for attempt in range(max_retries):
                try:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200:
                        logger.info(f"Service {name} is ready")
                        break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Service {name} not ready after {max_retries} attempts: {e}"
                        )
                        pytest.fail(f"Service {name} is not available")
                    await asyncio.sleep(2)


class TestHelper:
    """Helper class for common test operations"""

    @staticmethod
    async def send_dsl_command(
        client: httpx.AsyncClient, command: str
    ) -> dict[str, Any]:
        """Send DSL command to agent"""
        response = await client.post("/execute", json={"dsl": command})
        response.raise_for_status()
        return response.json()

    @staticmethod
    async def send_a2a_message(
        client: httpx.AsyncClient, message_text: str
    ) -> dict[str, Any]:
        """Send A2A message to agent"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message_text}],
                    "messageId": "test-msg-001",
                    "kind": "message",
                }
            },
        }
        response = await client.post("/execute", json=request)
        response.raise_for_status()
        return response.json()

    @staticmethod
    async def wait_for_task_completion(
        client: httpx.AsyncClient, task_id: str, timeout: float = 60.0
    ) -> dict[str, Any]:
        """Wait for A2A task to complete"""
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                response = await client.get(f"/tasks/{task_id}")
                if response.status_code == 200:
                    task = response.json()
                    if task.get("status", {}).get("state") in ["completed", "failed"]:
                        return task

                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise TimeoutError(
                        f"Task {task_id} did not complete within {timeout} seconds"
                    )

                await asyncio.sleep(1.0)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Task {task_id} not found")
                raise

    @staticmethod
    async def send_websocket_message(
        websocket, message_type: str, payload: dict[str, Any]
    ) -> None:
        """Send WebSocket message"""
        message = {"type": message_type, "payload": payload}
        await websocket.send(json.dumps(message))

    @staticmethod
    async def receive_websocket_message(
        websocket, timeout: float = 10.0
    ) -> dict[str, Any]:
        """Receive WebSocket message with timeout"""
        try:
            message_str = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            return json.loads(message_str)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"No WebSocket message received within {timeout} seconds"
            )


@pytest.fixture
def test_helper():
    """Test helper instance"""
    return TestHelper


@pytest.fixture
async def setup_test_files(shared_dir, sample_test_data):
    """Setup test files in shared directory"""
    # Create test files
    test_files = {}

    # Text file
    text_file = shared_dir / "test_input.txt"
    with open(text_file, "w") as f:
        f.write(sample_test_data["test_file_content"])
    test_files["text"] = text_file

    # JSON file
    json_file = shared_dir / "test_data.json"
    with open(json_file, "w") as f:
        json.dump(sample_test_data["test_json_data"], f, indent=2)
    test_files["json"] = json_file

    # CSV file
    csv_file = shared_dir / "test_data.csv"
    with open(csv_file, "w") as f:
        f.write(sample_test_data["test_csv_data"])
    test_files["csv"] = csv_file

    # Analysis script
    script_file = shared_dir / "analyzer.py"
    with open(script_file, "w") as f:
        f.write(sample_test_data["test_analysis_script"])
    test_files["script"] = script_file

    yield test_files

    # Cleanup (optional - Docker volumes are ephemeral in tests)
    for file_path in test_files.values():
        if file_path.exists():
            file_path.unlink()


# Custom markers for test categorization
pytest_configure = lambda config: [
    config.addinivalue_line("markers", "unit: Unit tests"),
    config.addinivalue_line("markers", "integration: Integration tests"),
    config.addinivalue_line("markers", "p2p: P2P communication tests"),
    config.addinivalue_line("markers", "a2a: A2A protocol tests"),
    config.addinivalue_line("markers", "mcp: MCP integration tests"),
    config.addinivalue_line("markers", "dagger: Dagger execution tests"),
    config.addinivalue_line("markers", "websocket: WebSocket communication tests"),
    config.addinivalue_line("markers", "slow: Slow running tests"),
]

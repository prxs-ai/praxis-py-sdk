import asyncio
import os
import sys

import httpx
import pytest
from loguru import logger

# Add project root and py-libp2p to path for imports
# This assumes the test is run from the 'agents/base-agent' directory or similar context
# Adjust paths if necessary based on your testing environment
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))  # Should point to agents/base-agent
PY_LIBP2P_PATH_LOCAL = os.path.join(PROJECT_ROOT, "py-libp2p")
PY_LIBP2P_PATH_DOCKER = "/serve_app/py-libp2p"

if os.path.exists(PY_LIBP2P_PATH_DOCKER):
    sys.path.insert(0, PY_LIBP2P_PATH_DOCKER)
elif os.path.exists(PY_LIBP2P_PATH_LOCAL):
    sys.path.insert(0, PY_LIBP2P_PATH_LOCAL)
else:
    logger.warning(f"py-libp2p path not found at {PY_LIBP2P_PATH_LOCAL} or {PY_LIBP2P_PATH_DOCKER}")

# Add src to path
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if os.path.exists(SRC_PATH):
    sys.path.insert(0, SRC_PATH)
else:
    logger.warning(f"src path not found at {SRC_PATH}")


from base_agent.config import BasicAgentConfig, get_agent_config, set_agent_config
from base_agent.p2p import libp2p_node, setup_libp2p, shutdown_libp2p

# Configuration for the test agent and mock registry
# These would typically come from environment variables for flexibility
TEST_AGENT_NAME = "test-discovery-agent"
TEST_AGENT_LISTEN_ADDR = "/ip4/0.0.0.0/tcp/0"  # Use OS-assigned port

# Mock Relay Registry configuration (must match what mock_relay_node.py uses or is configured with)
# Assuming mock_relay_node.py provides the registry functionality
MOCK_REGISTRY_HTTP_URL = "http://127.0.0.1:8081"  # Default from relay-registry service in docker-compose potentially
MOCK_REGISTRY_RELAY_PEER_ID = os.getenv(
    "REGISTRY_RELAY_PEER_ID", "12D3KooWQz2q3Z4YyYjp123abc"
)  # Replace with actual or configured mock relay peer ID
MOCK_REGISTRY_RELAY_MULTIADDR_TEMPLATE = (
    "/ip4/127.0.0.1/tcp/4001/p2p/{}"  # Matches mock_relay_node.py default listen address
)


@pytest.fixture(scope="module")
async def test_agent_config_fixture():
    original_config = get_agent_config()
    test_config = BasicAgentConfig(
        agent_name=TEST_AGENT_NAME,
        agent_p2p_listen_addr=TEST_AGENT_LISTEN_ADDR,
        registry_http_url=MOCK_REGISTRY_HTTP_URL,
        registry_relay_peer_id=MOCK_REGISTRY_RELAY_PEER_ID,
        registry_relay_multiaddr_template=MOCK_REGISTRY_RELAY_MULTIADDR_TEMPLATE,
        # Add other necessary config fields if any, copying from original or using defaults
        ray_address=original_config.ray_address,
        redis_host=original_config.redis_host,
        redis_port=original_config.redis_port,
        redis_password=original_config.redis_password,
        postgres_host=original_config.postgres_host,
        postgres_port=original_config.postgres_port,
        postgres_user=original_config.postgres_user,
        postgres_password=original_config.postgres_password,
        postgres_db=original_config.postgres_db,
        minio_endpoint=original_config.minio_endpoint,
        minio_access_key=original_config.minio_access_key,
        minio_secret_key=original_config.minio_secret_key,
        minio_secure=original_config.minio_secure,
        default_bucket_name=original_config.default_bucket_name,
    )
    set_agent_config(test_config)
    logger.info(f"Using test agent config: {test_config}")
    yield test_config
    # Restore original config if necessary, though get_agent_config might be instance-based
    set_agent_config(original_config)
    logger.info("Restored original agent config")


@pytest.mark.asyncio
async def test_agent_registers_and_is_discoverable(test_agent_config_fixture):
    """
    Tests if an agent can setup libp2p, register with the mock registry,
    and then be discovered via the registry's /peers endpoint.
    """
    current_node = None
    try:
        logger.info("Starting test: Agent registration and discovery")

        # 1. Call setup_libp2p() for the test agent.
        # This will initialize the libp2p node and attempt registration.
        logger.info("Setting up libp2p for test agent...")
        await setup_libp2p()  # This uses the config set by test_agent_config_fixture
        logger.info("Libp2p setup for test agent completed.")

        assert libp2p_node is not None, "libp2p_node was not initialized"
        current_node = libp2p_node  # Keep a reference for shutdown
        agent_peer_id = current_node.get_id()
        logger.info(f"Test agent Peer ID: {agent_peer_id}")

        # 2. Confirm registration by querying the relay's /peers endpoint.
        # (setup_libp2p already logs success/failure of registration itself)
        # Give a slight delay for registry to process if needed.
        await asyncio.sleep(1)

        peers_url = f"{test_agent_config_fixture.registry_http_url}/peers"
        logger.info(f"Querying registry for peers at: {peers_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(peers_url, timeout=10.0)

        response.raise_for_status()  # Ensure registry's /peers endpoint is responsive
        peers_data = response.json()
        logger.info(f"Registry /peers response: {peers_data}")

        # 3. Assert the new peer is discoverable.
        # Assuming peers_data is a list of dicts like [{"peer_id": "...", "addrs": [...]}, ...]
        # Or it might be a dict like {"peers": [...]}

        # Let's assume the structure is a list of peers directly, or a dict with a "peers" key
        registered_peers = []
        if isinstance(peers_data, list):
            registered_peers = peers_data
        elif isinstance(peers_data, dict) and "peers" in peers_data and isinstance(peers_data["peers"], list):
            registered_peers = peers_data["peers"]
        else:
            pytest.fail(f"Unexpected format for /peers response: {peers_data}")

        found_agent = False
        for peer_info in registered_peers:
            if peer_info.get("peer_id") == str(agent_peer_id):
                found_agent = True
                logger.info(f"Test agent {agent_peer_id} found in registry's peer list.")
                # Optionally, could also check if addresses match
                # agent_addrs = [str(addr) for addr in await current_node.get_listen_addrs()]
                # assert all(addr in peer_info.get("addrs", []) for addr in agent_addrs)
                break

        assert found_agent, f"Test agent {agent_peer_id} not found in registry's peer list after registration."

        logger.info("Test successful: Agent registered and found in registry.")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during test: {e.response.status_code} - {e.response.text}")
        pytest.fail(f"HTTP error: {e}")
    except httpx.RequestError as e:
        logger.error(f"Request error during test: {e}")
        pytest.fail(f"Request error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during the test: {e}", exc_info=True)
        pytest.fail(f"Unexpected error: {e}")
    finally:
        logger.info("Shutting down libp2p for test agent...")
        if current_node:  # Check if libp2p_node was set
            await shutdown_libp2p()  # This uses the global libp2p_node
        logger.info("Libp2p shutdown for test agent completed.")


# To run this test:
# 1. Ensure the mock relay registry (e.g., mock_relay_node.py or the Docker service) is running and accessible.
#    - Its HTTP API should be at MOCK_REGISTRY_HTTP_URL.
#    - Its libp2p relay peer ID and multiaddr should match MOCK_REGISTRY_RELAY_PEER_ID and MOCK_REGISTRY_RELAY_MULTIADDR_TEMPLATE.
# 2. Set any necessary environment variables if not using defaults (e.g., for MOCK_REGISTRY_RELAY_PEER_ID).
# 3. Run pytest: `pytest tests/e2e/test_agent_registration.py` (adjust path as needed)
#
# Note on mock_relay_node.py PEER_ID:
# The mock_relay_node.py currently generates a new key pair (and thus peer ID) each time it starts.
# For this test to reliably connect to it using a pre-configured MOCK_REGISTRY_RELAY_PEER_ID,
# the mock_relay_node.py would need to be modified to:
#  a) Accept a private key as input (e.g., via env var) to deterministically generate the same peer ID.
#  b) Or, output its generated Peer ID in a way that this test can consume it dynamically.
# If using the docker-compose `relay-registry` service, its peer ID needs to be known.
# The current placeholder "12D3KooWQz2q3Z4YyYjp123abc" for MOCK_REGISTRY_RELAY_PEER_ID will likely not work
# unless the mock relay is specifically configured with it.
# The log `Use this peer ID in your .env: {peer_id}` from `mock_relay_node.py` is helpful for manual runs.

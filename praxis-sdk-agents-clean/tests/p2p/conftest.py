import pytest

from base_agent.p2p.config import P2PConfig
from base_agent.p2p.manager import P2PManager


@pytest.fixture
def p2p_config():
    """Fixture that provides a P2P configuration for testing."""
    return P2PConfig(relay_addr="/ip4/127.0.0.1/tcp/9000/p2p/TEST_RELAY_PEER_ID")


@pytest.fixture
def p2p_manager(p2p_config):
    return P2PManager(config=p2p_config)

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from libp2p.crypto.keys import KeyPair

from base_agent.p2p.config import P2PConfig
from base_agent.p2p.libp2p.node import LibP2PNode


@pytest.fixture
def config():
    return P2PConfig(
        keystore_path="/tmp/test_keystore", relay_addr="/ip4/127.0.0.1/tcp/8888/p2p/QmTest", noise_key="test_noise_key"
    )


@pytest.fixture
def mock_keypair():
    return MagicMock(spec=KeyPair)


@pytest.fixture
def node(config):
    with patch("base_agent.p2p.libp2p.node.load_or_create_node_key") as mock_load_key:
        mock_load_key.return_value = MagicMock(spec=KeyPair)
        return LibP2PNode(config)


class TestLibP2PNode:
    def test_init(self, config):
        with patch("base_agent.p2p.libp2p.node.load_or_create_node_key") as mock_load_key:
            mock_load_key.return_value = MagicMock(spec=KeyPair)
            node = LibP2PNode(config)

            assert node.config == config
            assert node.host is None
            assert node.shutdown_requested is False
            assert isinstance(node.keypair, MagicMock)
            mock_load_key.assert_called_once_with(os.path.join(config.keystore_path, "node.key"))

    def test_init_keypair(self, node, config):
        with patch("base_agent.p2p.libp2p.node.load_or_create_node_key") as mock_load_key:
            mock_load_key.return_value = MagicMock(spec=KeyPair)

            node._init_keypair("custom.key")

            mock_load_key.assert_called_with(os.path.join(config.keystore_path, "custom.key"))
            assert isinstance(node.keypair, MagicMock)

    def test_init_host(self, node):
        with (
            patch("base_agent.p2p.libp2p.node.new_host") as mock_new_host,
            patch("base_agent.p2p.libp2p.node.decode_noise_key") as mock_decode,
            patch("base_agent.p2p.libp2p.node.NoiseTransport") as mock_noise,
        ):
            mock_decode.return_value = "decoded_noise_key"
            mock_host = MagicMock()
            mock_new_host.return_value = mock_host

            result = node._init_host()

            mock_decode.assert_called_once_with(node.config.noise_key)
            mock_noise.assert_called_once()
            mock_new_host.assert_called_once()
            assert result == mock_host

    @pytest.mark.asyncio
    async def test_initialize(self, node):
        mock_host = MagicMock()
        mock_host.get_id.return_value = "test_id"
        mock_host.get_addrs.return_value = ["addr1", "addr2"]

        with (
            patch.object(node, "_init_host", return_value=mock_host),
            patch("base_agent.p2p.libp2p.node.CircuitV2Protocol") as mock_protocol,
            patch("base_agent.p2p.libp2p.node.CircuitV2Transport") as mock_transport,
        ):
            result = await node.initialize()

            mock_host.set_stream_handler.assert_called_once()
            mock_protocol.assert_called_once_with(mock_host)
            mock_transport.assert_called_once()
            assert result == mock_host
            assert node.host == mock_host

    @pytest.mark.asyncio
    async def test_connect_to_relay_success(self, node):
        mock_host = MagicMock()
        mock_host.connect = AsyncMock()
        node.host = mock_host

        with patch("base_agent.p2p.libp2p.node.info_from_p2p_addr") as mock_info:
            result = await node.connect_to_relay()

            mock_info.assert_called_once()
            mock_host.connect.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_connect_to_relay_failure(self, node):
        mock_host = MagicMock()
        mock_host.connect = AsyncMock(side_effect=Exception("Connection failed"))
        node.host = mock_host

        with patch("base_agent.p2p.libp2p.node.info_from_p2p_addr"):
            result = await node.connect_to_relay()

            assert result is False

    @pytest.mark.asyncio
    async def test_setup_listener(self, node):
        mock_transport = MagicMock()
        mock_listener = MagicMock()
        mock_listener.listen = AsyncMock()
        mock_transport.create_listener.return_value = mock_listener
        node.transport = mock_transport

        mock_nursery = MagicMock()

        with patch("base_agent.p2p.libp2p.node.handle_card"):
            await node.setup_listener(mock_nursery)

            mock_transport.create_listener.assert_called_once()
            mock_listener.listen.assert_called_once_with(None, mock_nursery)

    def test_init_host_with_noise_protocol(self, node):
        with (
            patch("base_agent.p2p.libp2p.node.new_host") as mock_new_host,
            patch("base_agent.p2p.libp2p.node.decode_noise_key") as mock_decode,
            patch("base_agent.p2p.libp2p.node.NoiseTransport") as mock_noise,
        ):
            mock_decode.return_value = "decoded_noise_key"
            mock_host = MagicMock()
            mock_new_host.return_value = mock_host

            # Ensure noise_key is set
            node.config.noise_key = "test_noise_key"

            result = node._init_host()

            # Verify noise protocol was configured
            mock_decode.assert_called_once_with("test_noise_key")
            mock_noise.assert_called_once_with(libp2p_keypair=node.keypair, noise_privkey="decoded_noise_key")
            mock_new_host.assert_called_once()
            assert result == mock_host

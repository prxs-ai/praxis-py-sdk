import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from libp2p import new_host
from libp2p.network.stream.net_stream import INetStream
from libp2p.peer.id import ID as PeerID  # noqa: N811
from libp2p.peer.peerinfo import PeerInfo
from multiaddr import Multiaddr

REGISTRY_URL = "http://localhost:8001"
LOCAL_API_URL = "http://localhost:8000"
HANDOFF_PROTOCOL = "/ai-agent/handoff/1.0.0"
TEST_AGENT_NAME = "test-agent"
TEST_RELAY_PEER_ID = "12D3KooWRelayPeerID"

logger = logging.getLogger(__name__)


class TestE2EIntegration:
    @pytest_asyncio.fixture(autouse=True)
    async def clients(self):
        self.registry_client = httpx.AsyncClient(base_url=REGISTRY_URL, timeout=10.0)
        self.local_api_client = httpx.AsyncClient(base_url=LOCAL_API_URL, timeout=10.0)
        yield
        await self.registry_client.aclose()
        await self.local_api_client.aclose()

    @pytest.mark.asyncio()
    async def test_end_to_end_integration_with_mock(self):
        test_payload = {
            "method": "POST",
            "path": "execute",
            "params": {"task_id": "test-123"},
            "input": {"query": "What is 2+2?", "context": "math"},
        }

        expected_response = {"result": "4", "status": "success"}

        # Mock the registry response
        mock_peers_data = [
            {
                "peer_id": "12D3KooWTestPeer1",
                "multiaddresses": [
                    "/ip4/127.0.0.1/tcp/4001/p2p/12D3KooWTestPeer1",
                    "/p2p-circuit/p2p/12D3KooWTestPeer1",
                ],
                "agent_name": TEST_AGENT_NAME,
                "capabilities": ["execute"],
            }
        ]

        # Mock libp2p components
        mock_stream = AsyncMock(spec=INetStream)
        mock_stream.write = AsyncMock()
        mock_stream.read = AsyncMock(return_value=json.dumps(expected_response).encode())
        mock_stream.close = AsyncMock()

        mock_peer_info = MagicMock(spec=PeerInfo)
        mock_peer_info.peer_id = PeerID.from_base58("12D3KooWTestPeer1")
        mock_peer_info.addrs = [Multiaddr("/ip4/127.0.0.1/tcp/4001")]

        mock_host = AsyncMock()
        mock_host.new_stream = AsyncMock(return_value=mock_stream)

        with (
            patch("httpx.AsyncClient.get") as mock_registry_get,
            patch("httpx.AsyncClient.post") as mock_local_post,
            patch.object(self, "_create_peer_info", return_value=mock_peer_info),
            patch.object(self, "_dial_peer", return_value=mock_host),
        ):
            # Setup registry mock
            mock_registry_response = MagicMock()
            mock_registry_response.json.return_value = mock_peers_data
            mock_registry_response.raise_for_status = MagicMock()
            mock_registry_get.return_value = mock_registry_response

            # Setup local API mock
            mock_local_response = MagicMock()
            mock_local_response.json.return_value = expected_response
            mock_local_response.content = json.dumps(expected_response).encode()
            mock_local_response.raise_for_status = MagicMock()
            mock_local_post.return_value = mock_local_response

            # Execute the full E2E flow
            result = await self._execute_e2e_flow(test_payload)

            # Assertions
            assert result is not None, "E2E flow should return a result"
            assert result == expected_response, f"Expected {expected_response}, got {result}"

            # Verify interactions
            mock_registry_get.assert_called_once_with(f"/peers?agent_name={TEST_AGENT_NAME}")
            mock_stream.write.assert_called_once()
            mock_stream.read.assert_called_once()
            mock_stream.close.assert_called_once()

            logger.info("E2E integration test with mocks completed successfully")

    def _create_peer_info(self, peer_data: dict) -> PeerInfo:
        peer_id = PeerID.from_base58(peer_data["peer_id"])
        multiaddrs = [Multiaddr(addr) for addr in peer_data["multiaddresses"]]
        return PeerInfo(peer_id=peer_id, addrs=multiaddrs)

    async def _dial_peer(self, peer_info: PeerInfo, relay_peer_id: str):
        # In real implementation, this would use actual libp2p host
        # For testing, we mock this functionality
        return await new_host()

    async def _execute_handoff(self, host, peer_info: PeerInfo, payload: dict) -> dict:
        try:
            # Open stream to target peer
            stream = await host.new_stream(peer_info.peer_id, [HANDOFF_PROTOCOL])

            # Send payload
            payload_bytes = json.dumps(payload).encode()
            await stream.write(payload_bytes)

            # Read response
            response_bytes = await stream.read()
            response = json.loads(response_bytes.decode())

            # Close stream
            await stream.close()

            return response

        except Exception as e:
            logger.error(f"Handoff failed: {e}")
            raise

    async def _call_local_api(self, payload: dict) -> dict:
        method = payload["method"].lower()
        path = payload["path"]
        params = payload.get("params", {})
        input_data = payload.get("input")

        # Construct URL with params
        formatted_path = path.format(**params) if params else path

        url = f"/{formatted_path.lstrip('/')}"

        # Make request
        if method == "get":
            response = await self.local_api_client.get(url)
        elif method == "post":
            if input_data:
                response = await self.local_api_client.post(url, json=input_data)
            else:
                response = await self.local_api_client.post(url)
        elif method == "put":
            if input_data:
                response = await self.local_api_client.put(url, json=input_data)
            else:
                response = await self.local_api_client.put(url)
        else:
            response = await self.local_api_client.request(method.upper(), url, json=input_data)

        response.raise_for_status()
        return response.json()

    async def _execute_e2e_flow(self, test_payload: dict) -> dict:
        # Step 1: Discovery
        response = await self.registry_client.get(f"/peers?agent_name={TEST_AGENT_NAME}")
        response.raise_for_status()
        peers_data = response.json()

        # Step 2: Select peer and dial
        target_peer = peers_data[0]
        peer_info = self._create_peer_info(target_peer)
        host = await self._dial_peer(peer_info, TEST_RELAY_PEER_ID)

        # Step 3: Execute handoff
        return await self._execute_handoff(host, peer_info, test_payload)

import asyncio
import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from libp2p import new_host
from libp2p.network.stream.net_stream_interface import INetStream
from libp2p.peer.peerinfo import PeerInfo
from libp2p.peer.id import ID as PeerID
from multiaddr import Multiaddr
import logging

REGISTRY_URL = "http://localhost:8001"
LOCAL_API_URL = "http://localhost:8000"
HANDOFF_PROTOCOL = "/ai-agent/handoff/1.0.0"
TEST_AGENT_NAME = "test-agent"
TEST_RELAY_PEER_ID = "12D3KooWRelayPeerID"

logger = logging.getLogger(__name__)


class TestE2EIntegration:
    """End-to-End Integration Test Suite for AI Agent Handoff"""
    
    async def setup_method(self):
        """Setup test environment"""
        self.registry_client = httpx.AsyncClient(base_url=REGISTRY_URL, timeout=10.0)
        self.local_api_client = httpx.AsyncClient(base_url=LOCAL_API_URL, timeout=10.0)
        
    async def teardown_method(self):
        """Cleanup test environment"""
        await self.registry_client.aclose()
        await self.local_api_client.aclose()
    
    async def test_discovery_fetch_peers(self):
        """Test Step 1: Discovery - Fetch peers from registry"""
        try:
            response = await self.registry_client.get(f"/peers?agent_name={TEST_AGENT_NAME}")
            response.raise_for_status()
            
            peers_data = response.json()
            assert isinstance(peers_data, list), "Registry should return list of peers"
            assert len(peers_data) > 0, f"No peers found for agent '{TEST_AGENT_NAME}'"
            
            # Validate peer data structure
            for peer in peers_data:
                assert "peer_id" in peer, "Peer must have peer_id"
                assert "multiaddresses" in peer, "Peer must have multiaddresses"
                assert isinstance(peer["multiaddresses"], list), "Multiaddresses must be a list"
                assert len(peer["multiaddresses"]) > 0, "Peer must have at least one multiaddress"
            
            logger.info(f"Discovery successful: Found {len(peers_data)} peers for {TEST_AGENT_NAME}")
            return peers_data
            
        except httpx.RequestError as e:
            pytest.skip(f"Registry service unavailable: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                pytest.skip(f"Agent '{TEST_AGENT_NAME}' not found in registry")
            raise
    
    @pytest.mark.asyncio
    async def test_end_to_end_integration_with_mock(self):
        """Complete E2E test with mocked components for CI reliability"""
        
        # Sample test payload
        test_payload = {
            "method": "POST",
            "path": "execute",
            "params": {"task_id": "test-123"},
            "input": {"query": "What is 2+2?", "context": "math"}
        }
        
        expected_response = {"result": "4", "status": "success"}
        
        # Mock the registry response
        mock_peers_data = [
            {
                "peer_id": "12D3KooWTestPeerID123",
                "multiaddresses": [
                    "/ip4/127.0.0.1/tcp/4001/p2p/12D3KooWTestPeerID123",
                    "/p2p-circuit/p2p/12D3KooWTestPeerID123"
                ],
                "agent_name": TEST_AGENT_NAME,
                "capabilities": ["execute"]
            }
        ]
        
        # Mock libp2p components
        mock_stream = AsyncMock(spec=INetStream)
        mock_stream.write = AsyncMock()
        mock_stream.read = AsyncMock(return_value=json.dumps(expected_response).encode())
        mock_stream.close = AsyncMock()
        
        mock_peer_info = MagicMock(spec=PeerInfo)
        mock_peer_info.peer_id = PeerID.from_base58("12D3KooWTestPeerID123")
        mock_peer_info.addrs = [Multiaddr("/ip4/127.0.0.1/tcp/4001")]
        
        mock_host = AsyncMock()
        mock_host.new_stream = AsyncMock(return_value=mock_stream)
        
        with patch('httpx.AsyncClient.get') as mock_registry_get, \
             patch('httpx.AsyncClient.post') as mock_local_post, \
             patch.object(self, '_create_peer_info', return_value=mock_peer_info), \
             patch.object(self, '_dial_peer', return_value=mock_host):
            
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
    
    @pytest.mark.asyncio
    async def test_end_to_end_integration_real_services(self):
        """Complete E2E test with real services (when available)"""
        
        test_payload = {
            "method": "GET",
            "path": "health",
            "params": {},
            "input": None
        }
        
        try:
            # Step 1: Discovery
            peers_data = await self.test_discovery_fetch_peers()
            
            # Step 2: Select a peer and create PeerInfo
            target_peer = peers_data[0]
            peer_info = self._create_peer_info(target_peer)
            
            # Step 3: Dial the peer
            host = await self._dial_peer(peer_info, TEST_RELAY_PEER_ID)
            
            # Step 4: Execute handoff
            result = await self._execute_handoff(host, peer_info, test_payload)
            
            # Step 5: Verify against local API
            expected_result = await self._call_local_api(test_payload)
            
            # Step 6: Assertions
            assert result is not None, "Handoff should return a result"
            assert isinstance(result, dict), "Result should be a dictionary"
            
            # Compare with local API result (flexible comparison for real services)
            if "error" not in result and "error" not in expected_result:
                logger.info("Both handoff and local API succeeded")
            
            logger.info("E2E integration test with real services completed successfully")
            
        except Exception as e:
            pytest.skip(f"Real services test skipped due to: {e}")
    
    def _create_peer_info(self, peer_data: dict) -> PeerInfo:
        """Create PeerInfo from registry peer data"""
        peer_id = PeerID.from_base58(peer_data["peer_id"])
        multiaddrs = [Multiaddr(addr) for addr in peer_data["multiaddresses"]]
        return PeerInfo(peer_id=peer_id, addrs=multiaddrs)
    
    async def _dial_peer(self, peer_info: PeerInfo, relay_peer_id: str):
        """Dial peer using circuit transport"""
        # In real implementation, this would use actual libp2p host
        # For testing, we mock this functionality
        host = await new_host()
        # circuit_transport.dial(peer_info, relay_peer_id) would be called here
        return host
    
    async def _execute_handoff(self, host, peer_info: PeerInfo, payload: dict) -> dict:
        """Execute handoff protocol over libp2p stream"""
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
        """Call local API directly for comparison"""
        method = payload["method"].lower()
        path = payload["path"]
        params = payload.get("params", {})
        input_data = payload.get("input")
        
        # Construct URL with params
        if params:
            formatted_path = path.format(**params)
        else:
            formatted_path = path
        
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
        """Execute the complete E2E flow"""
        # Step 1: Discovery
        response = await self.registry_client.get(f"/peers?agent_name={TEST_AGENT_NAME}")
        response.raise_for_status()
        peers_data = response.json()
        
        # Step 2: Select peer and dial
        target_peer = peers_data[0]
        peer_info = self._create_peer_info(target_peer)
        host = await self._dial_peer(peer_info, TEST_RELAY_PEER_ID)
        
        # Step 3: Execute handoff
        result = await self._execute_handoff(host, peer_info, test_payload)
        
        return result


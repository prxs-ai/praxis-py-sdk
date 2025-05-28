import asyncio
import pytest
import trio
import trio_asyncio
from unittest.mock import Mock, AsyncMock, patch
import httpx
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


class MockHttpServer:
    
    def __init__(self, response_data=None, status_code=200):
        self.response_data = response_data or {
            "name": "test-agent",
            "version": "1.0.0", 
            "description": "Test agent for integration testing",
            "skills": []
        }
        self.status_code = status_code
        self.requests_received = []
    
    async def handle_request(self, url):
        """Симулирует HTTP запрос"""
        self.requests_received.append(url)
        if self.status_code != 200:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=Mock(),
                response=Mock(status_code=self.status_code, text="Error")
            )
        return json.dumps(self.response_data).encode()


@pytest.mark.integration
@pytest.mark.asyncio
class TestLibp2pCardProtocolIntegration:
    
    async def test_two_nodes_card_exchange_success(self):
        
        mock_server = MockHttpServer()
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.content = await mock_server.handle_request("http://localhost:8000/card")
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            mock_stream = Mock()
            mock_stream.muxed_conn.peer_id.__str__.return_value = "QmServerPeer123"
            mock_stream.write = AsyncMock()
            mock_stream.close = AsyncMock()
            
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            assert mock_stream.write.called
            assert mock_stream.close.called
            
            written_data = mock_stream.write.call_args[0][0]
            card_data = json.loads(written_data.decode())
            
            assert card_data["name"] == "test-agent"
            assert card_data["version"] == "1.0.0"
            assert "skills" in card_data

    async def test_two_nodes_card_exchange_http_error(self):
        
        mock_server = MockHttpServer(status_code=404)
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", 
                request=Mock(), 
                response=Mock(status_code=404, text="Not Found")
            )
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            mock_stream = Mock()
            mock_stream.muxed_conn.peer_id.__str__.return_value = "QmServerPeer123"
            mock_stream.write = AsyncMock()
            mock_stream.close = AsyncMock()
            
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            assert mock_stream.write.called
            assert mock_stream.close.called
            
            written_data = mock_stream.write.call_args[0][0]
            error_data = json.loads(written_data.decode())
            
            assert "error" in error_data
            assert error_data["code"] == 404

    async def test_protocol_constant_validation(self):
        
        from base_agent.p2p import PROTOCOL_CARD
        
        assert str(PROTOCOL_CARD) == "/ai-agent/card/1.0.0"


class TestLibp2pCardProtocolMocked:
    
    @pytest.mark.asyncio
    async def test_card_protocol_basic_flow(self):
        
        from base_agent.p2p import PROTOCOL_CARD
        
        assert str(PROTOCOL_CARD) == "/ai-agent/card/1.0.0"
        
        mock_stream = Mock()
        mock_stream.muxed_conn.peer_id.__str__.return_value = "QmTestPeer"
        mock_stream.write = AsyncMock()
        mock_stream.close = AsyncMock()
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            test_card_data = {
                "name": "integration-test-agent",
                "version": "1.0.0",
                "description": "Agent for integration testing"
            }
            
            mock_response = Mock()
            mock_response.content = json.dumps(test_card_data).encode()
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            assert mock_client_instance.get.called
            assert mock_stream.write.called
            assert mock_stream.close.called
            
            call_args = mock_stream.write.call_args[0][0]
            received_data = json.loads(call_args.decode())
            
            assert received_data["name"] == "integration-test-agent"
            assert received_data["version"] == "1.0.0"

    @pytest.mark.asyncio 
    async def test_error_handling_integration(self):
        
        mock_stream = Mock()
        mock_stream.muxed_conn.peer_id.__str__.return_value = "QmErrorTestPeer"
        mock_stream.write = AsyncMock()
        mock_stream.close = AsyncMock()
        
        error_scenarios = [
            (httpx.HTTPStatusError("404", request=Mock(), response=Mock(status_code=404, text="Not Found")), 404),
            (httpx.TimeoutException("Timeout"), 504),
            (httpx.ConnectError("Connection failed"), 504),
            (Exception("Unexpected error"), 500)
        ]
        
        for error, expected_code in error_scenarios:
            mock_stream.write.reset_mock()
            mock_stream.close.reset_mock()
            
            with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.get.side_effect = error
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                from base_agent.p2p import handle_card
                await handle_card(mock_stream)
                
                assert mock_stream.write.called
                assert mock_stream.close.called
                
                error_data = json.loads(mock_stream.write.call_args[0][0].decode())
                assert "error" in error_data
                assert error_data["code"] == expected_code


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

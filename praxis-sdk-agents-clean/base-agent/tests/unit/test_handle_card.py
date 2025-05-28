import datetime
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx


class MockStream:
    """Mock класс для INetStream"""
    def __init__(self, peer_id="QmTestPeer123"):
        self.muxed_conn = Mock()
        self.muxed_conn.peer_id = Mock()
        self.muxed_conn.peer_id.__str__ = Mock(return_value=peer_id)
        self.written_data = []
        self.closed = False
    
    async def write(self, data):
        self.written_data.append(data)
    
    async def close(self):
        self.closed = True


@pytest.mark.asyncio
class TestHandleCard:
    
    async def test_handle_card_success(self):
        
        # Arrange
        mock_stream = MockStream()
        expected_response = b'{"card": "test_data", "version": "1.0.0"}'
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.content = expected_response
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Act
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            assert len(mock_stream.written_data) == 1
            assert mock_stream.written_data[0] == expected_response
            assert mock_stream.closed == True
            
            mock_client_instance.get.assert_called_once_with("http://localhost:8000/card")
            mock_response.raise_for_status.assert_called_once()

    async def test_handle_card_http_status_error(self):
        
        mock_stream = MockStream()
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=mock_response
            )
            
            # Act
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            # Assert
            assert len(mock_stream.written_data) == 1
            written_data = mock_stream.written_data[0].decode()
            assert '"error":"HTTP error: 404"' in written_data
            assert '"code":404' in written_data
            assert mock_stream.closed == True

    async def test_handle_card_request_timeout(self):
        
        mock_stream = MockStream()
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Act
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            # Assert
            assert len(mock_stream.written_data) == 1
            written_data = mock_stream.written_data[0]
            assert b'"error":"Request to /card failed or timed out"' in written_data
            assert b'"code":504' in written_data
            assert mock_stream.closed == True

    async def test_handle_card_connection_error(self):
        
        mock_stream = MockStream()
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Act
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            # Assert
            assert len(mock_stream.written_data) == 1
            written_data = mock_stream.written_data[0]
            assert b'"error":"Request to /card failed or timed out"' in written_data
            assert b'"code":504' in written_data
            assert mock_stream.closed == True

    async def test_handle_card_unexpected_error(self):
        
        mock_stream = MockStream()
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = Exception("Unexpected error")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            assert len(mock_stream.written_data) == 1
            written_data = mock_stream.written_data[0]
            assert b'"error":"Internal server error"' in written_data
            assert b'"code":500' in written_data
            assert mock_stream.closed == True

    async def test_handle_card_stream_close_error(self):
        """Тест сценария с ошибкой закрытия stream"""
        
        mock_stream = MockStream()
        mock_stream.close = AsyncMock(side_effect=Exception("Close error"))
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.content = b'{"test": "data"}'
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            from base_agent.p2p import handle_card
            await handle_card(mock_stream)
            
            assert len(mock_stream.written_data) == 1
            assert mock_stream.written_data[0] == b'{"test": "data"}'
            mock_stream.close.assert_called_once()

    async def test_handle_card_logging(self):
        
        mock_stream = MockStream("QmTestPeer456")
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.content = b'{"card": "test"}'
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with patch('base_agent.p2p.logger') as mock_logger:
                from base_agent.p2p import handle_card
                await handle_card(mock_stream)
                
                assert mock_logger.info.call_count >= 2
                
                logged_calls = [str(call) for call in mock_logger.info.call_args_list]
                peer_id_logged = any("QmTestPeer456" in call for call in logged_calls)
                assert peer_id_logged, "Peer ID должен быть в логах"
                
                protocol_logged = any("/ai-agent/card/1.0.0" in call for call in logged_calls)
                assert protocol_logged, "Протокол должен быть в логах"

    async def test_handle_card_with_none_peer_id(self):
        
        mock_stream = MockStream()
        mock_stream.muxed_conn.peer_id = None
        
        with patch('base_agent.p2p.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.content = b'{"card": "test"}'
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with patch('base_agent.p2p.logger') as mock_logger:
                from base_agent.p2p import handle_card
                await handle_card(mock_stream)
                
                assert len(mock_stream.written_data) == 1
                assert mock_stream.closed == True
                
                logged_calls = [str(call) for call in mock_logger.info.call_args_list]
                unknown_peer_logged = any("UnknownPeer" in call for call in logged_calls)
                assert unknown_peer_logged, "UnknownPeer должен быть в логах когда peer_id = None"

    async def test_protocol_card_constant(self):
        
        from base_agent.p2p import PROTOCOL_CARD
        
        assert str(PROTOCOL_CARD) == "/ai-agent/card/1.0.0", f"PROTOCOL_CARD должен быть '/ai-agent/card/1.0.0', но получен {PROTOCOL_CARD}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

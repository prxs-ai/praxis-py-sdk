import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from aiohttp import ClientSession
import pandas as pd
from hyperliquid_client.main import HyperLiquidManager


@pytest.fixture
def mock_session():
    return MagicMock(spec=ClientSession)


@pytest.fixture
def hyperliquid_manager(mock_session):
    return HyperLiquidManager(
        session=mock_session,
        base_url="https://test.hyperliquid.url"
    )


@pytest.mark.asyncio
async def test_send_request_success(hyperliquid_manager, mock_session):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"data": "test"})
    mock_session.request.return_value.__aenter__.return_value = mock_response

    result = await hyperliquid_manager._send_request(
        headers={"test": "header"},
        params={"param": "value"},
        body={"body": "data"},
        method="POST"
    )

    assert result == {"data": "test"}
    mock_session.request.assert_called_once_with(
        method="POST",
        url="https://test.hyperliquid.url",
        json={"body": "data"},
        params={"param": "value"},
        headers={"Content-Type": "application/json", "test": "header"}
    )


@pytest.mark.asyncio
async def test_send_request_failure(hyperliquid_manager, mock_session):
    mock_response = MagicMock()
    mock_response.status = 400
    mock_session.request.return_value.__aenter__.return_value = mock_response

    with pytest.raises(HTTPException) as exc_info:
        await hyperliquid_manager._send_request(headers={})

    assert exc_info.value.status_code == 400
    assert "Problem with hyperliquid request" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_pool_liquidity_success(hyperliquid_manager):
    test_data = {
        "levels": [
            [{"px": 100, "sz": 10}, {"px": 99, "sz": 5}],  # bids
            [{"px": 101, "sz": 8}, {"px": 102, "sz": 7}]  # asks
        ]
    }

    with patch.object(hyperliquid_manager, '_send_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = test_data

        result = await hyperliquid_manager.get_pool_liquidity("BTC")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert set(result["type"].tolist()) == {"bids", "asks", "sum_liquidity"}
        assert result[result["type"] == "sum_liquidity"]["sz"].iloc[0] == 30


@pytest.mark.asyncio
async def test_get_pool_liquidity_empty_response(hyperliquid_manager):
    with patch.object(hyperliquid_manager, '_send_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"levels": [[], []]}

        result = await hyperliquid_manager.get_pool_liquidity("BTC")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # только sum_liquidity
        assert result["type"].iloc[0] == "sum_liquidity"
        assert result["sz"].iloc[0] == 0


def test_make_headers_default(hyperliquid_manager):
    headers = hyperliquid_manager._make_headers()
    assert headers == {"Content-Type": "application/json"}


def test_make_headers_custom(hyperliquid_manager):
    custom_headers = {"X-API-Key": "test-key"}
    headers = hyperliquid_manager._make_headers(custom_headers)
    assert headers == {"Content-Type": "application/json", "X-API-Key": "test-key"}


@pytest.mark.asyncio
async def test_get_hyperliquid_manager():
    mock_settings = MagicMock()
    mock_settings.hyperliquid.base_url = "https://test.url"

    with patch('hyperliquid_client.main.get_server_settings', return_value=mock_settings), \
            patch('aiohttp.ClientSession', new_callable=MagicMock) as mock_session:
        async for manager in get_hyperliquid_manager():
            assert isinstance(manager, HyperLiquidManager)
            assert manager.base_url == "https://test.url"
            mock_session.assert_called_once()

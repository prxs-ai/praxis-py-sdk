import pytest
import pandas as pd
from aiohttp import ClientSession
from fastapi import HTTPException
from unittest.mock import AsyncMock
from hyperliquid_client.manager import HyperLiquidManager


@pytest.fixture
async def hyperliquid_manager(mocker):
    async with ClientSession() as session:
        manager = HyperLiquidManager(
            session=session,
            base_url="https://api.hyperliquid.xyz"
        )
        yield manager


@pytest.mark.asyncio
async def test_send_request_success(hyperliquid_manager, mocker):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": "test_data"}
    hyperliquid_manager.session.request = AsyncMock(return_value=mock_response)

    result = await hyperliquid_manager._send_request(
        headers={"Content-Type": "application/json"},
        body={"type": "test"},
        params={"key": "value"},
        method="POST"
    )

    assert result == {"data": "test_data"}
    hyperliquid_manager.session.request.assert_called_with(
        method="POST",
        url="https://api.hyperliquid.xyz",
        json={"type": "test"},
        params={"key": "value"},
        headers={"Content-Type": "application/json"}
    )


@pytest.mark.asyncio
async def test_send_request_failure(hyperliquid_manager, mocker):
    mock_response = AsyncMock()
    mock_response.status = 400
    hyperliquid_manager.session.request = AsyncMock(return_value=mock_response)

    with pytest.raises(HTTPException) as exc:
        await hyperliquid_manager._send_request(
            headers={"Content-Type": "application/json"},
            body={"type": "test"}
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Problem with hyperliquid request"


@pytest.mark.asyncio
async def test_get_pool_liquidity(hyperliquid_manager, mocker):
    mock_data = {
        "levels": [
            [{"px": "100", "sz": "10"}, {"px": "101", "sz": "20"}],
            [{"px": "102", "sz": "30"}, {"px": "103", "sz": "40"}]
        ]
    }
    hyperliquid_manager._send_request = AsyncMock(return_value=mock_data)

    result = await hyperliquid_manager.get_pool_liquidity(coin="BTC")

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["type", "sz"]
    assert len(result) == 3
    assert result["type"].tolist() == ["asks", "bids", "sum_liquidity"]
    assert result["sz"].tolist() == [70, 30, 100]
    hyperliquid_manager._send_request.assert_called_with(
        body={"type": "l2Book", "coin": "BTC"},
        headers={"Content-Type": "application/json"}
    )


@pytest.mark.asyncio
async def test_make_headers_default(hyperliquid_manager):
    headers = hyperliquid_manager._make_headers()
    assert headers == {"Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_make_headers_custom(hyperliquid_manager):
    custom_headers = {"Authorization": "Bearer token"}
    headers = hyperliquid_manager._make_headers(custom_headers)
    assert headers == {
        "Content-Type": "application/json",
        "Authorization": "Bearer token"
    }

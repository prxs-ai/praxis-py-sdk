import pytest
import pandas as pd
from aiohttp import ClientSession
from fastapi import HTTPException
from unittest.mock import AsyncMock
from coingecko_client.manager import CoinGeckoApiManager, prepare_historical_prices


@pytest.fixture
async def coingecko_manager(mocker):
    async with ClientSession() as session:
        manager = CoinGeckoApiManager(
            api_key="test_api_key",
            session=session,
            base_url="https://api.coingecko.com/api/v3"
        )
        yield manager


@pytest.mark.asyncio
async def test_send_request_success(coingecko_manager, mocker):
    mock_response = AsyncMock()
    mock_response.json.return_value = {"data": "test"}
    coingecko_manager.session.request = AsyncMock(return_value=mock_response)

    result = await coingecko_manager._send_request(
        endpoint="/test",
        params={"key": "value"},
        method="GET"
    )

    assert result == {"data": "test"}
    coingecko_manager.session.request.assert_called_with(
        method="GET",
        url="https://api.coingecko.com/api/v3/test",
        headers={"x-cg-demo-api-key": "test_api_key"},
        params={"key": "value"}
    )


@pytest.mark.asyncio
async def test_get_tokens_without_name(coingecko_manager, mocker):
    mock_data = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum"}
    ]
    coingecko_manager._send_request = AsyncMock(return_value=mock_data)

    result = await coingecko_manager.get_tokens()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert list(result["id"]) == ["bitcoin", "ethereum"]
    coingecko_manager._send_request.assert_called_with(method="GET", endpoint="/coins/list")


@pytest.mark.asyncio
async def test_get_tokens_with_name(coingecko_manager, mocker):
    mock_data = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum"}
    ]
    coingecko_manager._send_request = AsyncMock(return_value=mock_data)

    result = await coingecko_manager.get_tokens(token_name="bitcoin")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result["id"].iloc[0] == "bitcoin"


@pytest.mark.asyncio
async def test_get_historical_prices_success(coingecko_manager, mocker):
    mock_tokens = pd.DataFrame([{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}])
    mocker.patch.object(coingecko_manager, "get_tokens", AsyncMock(return_value=mock_tokens))

    mock_historical = {
        "prices": [[1000000, 50000.0]],
        "market_caps": [[1000000, 1000000000.0]],
        "total_volumes": [[1000000, 50000000.0]]
    }
    coingecko_manager._send_request = AsyncMock(return_value=mock_historical)

    result = await coingecko_manager.get_historical_prices(token_name="bitcoin", days=10, vs_currency="usd")

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["timestamp", "price", "market_cap", "total_volume"]
    assert len(result) == 1
    assert result["price"].iloc[0] == 50000.0


@pytest.mark.asyncio
async def test_get_historical_prices_no_token(coingecko_manager, mocker):
    mock_tokens = pd.DataFrame()
    mocker.patch.object(coingecko_manager, "get_tokens", AsyncMock(return_value=mock_tokens))

    with pytest.raises(HTTPException) as exc:
        await coingecko_manager.get_historical_prices(token_name="unknown")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Did not find any historical data"


@pytest.mark.asyncio
async def test_prepare_historical_prices():
    mock_data = {
        "prices": [[1000000000, 50000.0], [1000001000, 51000.0]],
        "market_caps": [[1000000000, 1000000000.0], [1000001000, 1100000000.0]],
        "total_volumes": [[1000000000, 50000000.0], [1000001000, 51000000.0]]
    }

    result = await prepare_historical_prices(mock_data)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert list(result.columns) == ["timestamp", "price", "market_cap", "total_volume"]
    assert result["price"].iloc[0] == 50000.0
    assert result["market_cap"].iloc[0] == "1000000000"
    assert result["total_volume"].iloc[0] == "50000000"
    assert pd.api.types.is_datetime64_any_dtype(result["timestamp"])

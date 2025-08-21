import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from coingecko_client.main import (
    CoinGeckoApiManager,
    prepare_historical_prices,
    get_coingecko_manager
)
from fastapi import HTTPException
from pandas import DataFrame
import pandas as pd
from aiohttp import ClientSession
from datetime import datetime



@pytest.fixture
def mock_session():
    return MagicMock(spec=ClientSession)


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("COINGECKO_API_KEY", "test_key")
    monkeypatch.setenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")


@pytest.fixture
def coingecko_manager(mock_session):
    return CoinGeckoApiManager(
        api_key="test_api_key",
        session=mock_session,
        base_url="https://api.coingecko.com/api/v3"
    )


@pytest.mark.asyncio
async def test_send_request_success(coingecko_manager, mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_session.request.return_value.__aenter__.return_value = mock_response

    result = await coingecko_manager._send_request("/test", {"param": "value"})

    assert result == {"data": "test"}
    mock_session.request.assert_called_once_with(
        method="POST",
        url="https://api.coingecko.com/api/v3/test",
        headers={"x-cg-demo-api-key": "test_api_key"},
        params={"param": "value"}
    )


@pytest.mark.asyncio
async def test_get_tokens_all(coingecko_manager):
    test_data = [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}]
    with patch.object(coingecko_manager, '_send_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = test_data
        result = await coingecko_manager.get_tokens()

        assert isinstance(result, DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["id"] == "bitcoin"


@pytest.mark.asyncio
async def test_get_tokens_filtered(coingecko_manager):
    test_data = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum"}
    ]
    with patch.object(coingecko_manager, '_send_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = test_data
        result = await coingecko_manager.get_tokens("bitcoin")

        assert isinstance(result, DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["id"] == "bitcoin"


@pytest.mark.asyncio
async def test_get_historical_prices_success(coingecko_manager):
    token_data = [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}]
    historical_data = {
        "prices": [[1672531200000, 16500.5], [1672617600000, 16600.3]],
        "market_caps": [[1672531200000, 300000000000], [1672617600000, 310000000000]],
        "total_volumes": [[1672531200000, 20000000000], [1672617600000, 21000000000]]
    }

    with patch.object(coingecko_manager, 'get_tokens', new_callable=AsyncMock) as mock_get_tokens, \
            patch.object(coingecko_manager, '_send_request', new_callable=AsyncMock) as mock_request:
        mock_get_tokens.return_value = DataFrame(token_data)
        mock_request.return_value = historical_data

        result = await coingecko_manager.get_historical_prices("bitcoin")

        assert isinstance(result, DataFrame)
        assert len(result) == 2
        assert "timestamp" in result.columns
        assert "price" in result.columns
        assert "market_cap" in result.columns
        assert "total_volume" in result.columns


@pytest.mark.asyncio
async def test_get_historical_prices_no_token(coingecko_manager):
    with patch.object(coingecko_manager, 'get_tokens', new_callable=AsyncMock) as mock_get_tokens:
        mock_get_tokens.return_value = DataFrame()

        with pytest.raises(HTTPException) as exc_info:
            await coingecko_manager.get_historical_prices("unknown")

        assert exc_info.value.status_code == 400
        assert "Did not find any historical data" in str(exc_info.value.detail)


def test_prepare_historical_prices():
    test_data = {
        "prices": [[1672531200000, 16500.5], [1672617600000, 16600.3]],
        "market_caps": [[1672531200000, 300000000000], [1672617600000, 310000000000]],
        "total_volumes": [[1672531200000, 20000000000], [1672617600000, 21000000000]]
    }

    result = prepare_historical_prices(test_data)

    assert isinstance(result, DataFrame)
    assert len(result) == 2
    assert result["timestamp"][0] == datetime.fromtimestamp(1672531200)
    assert result["price"][0] == 16500.5
    assert result["market_cap"][0] == "300000000000"
    assert result["total_volume"][0] == "20000000000"


@pytest.mark.asyncio
async def test_get_coingecko_manager():
    with patch('coingecko_client.main.ClientSession', new_callable=MagicMock) as mock_session, \
            patch('coingecko_client.main.get_server_settings') as mock_settings:
        mock_settings.return_value.coingecko.api_key = "test_key"
        mock_settings.return_value.coingecko.base_url = "https://test.url"

        manager_gen = get_coingecko_manager()
        manager = await manager_gen.__anext__()

        assert isinstance(manager, CoinGeckoApiManager)
        assert manager.api_key == "test_key"
        assert manager.base_url == "https://test.url"

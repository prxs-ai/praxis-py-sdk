from unittest.mock import AsyncMock

import pytest
from shared_clients.aiohhtp_.api import AiohttpAPI
from shared_clients.aiohttp_.session import AiohttpSession


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AiohttpSession)


@pytest.mark.asyncio
async def test_aiohttp_api_init(mock_session):
    api = AiohttpAPI(mock_session)
    assert api._session == mock_session


@pytest.mark.asyncio
async def test_aiohttp_api_enter(mock_session):
    api = AiohttpAPI(mock_session)
    async with api as context:
        assert context == api
        mock_session.__aenter__.assert_called_once()


@pytest.mark.asyncio
async def test_aiohttp_api_exit(mock_session):
    api = AiohttpAPI(mock_session)
    exc_type = type[Exception]
    exc_val = Exception("Test exception")
    exc_tb = None

    async with api:
        pass

    mock_session.__aexit__.assert_called_once_with(None, None, None)

    mock_session.__aexit__.reset_mock()
    try:
        async with api:
            raise exc_val
    except Exception:
        pass

    mock_session.__aexit__.assert_called_once_with(exc_type, exc_val, exc_tb)

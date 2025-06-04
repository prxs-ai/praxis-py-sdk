from unittest.mock import AsyncMock

import pytest
from rugcheck_api import RugCheckAPI


@pytest.fixture
async def rugcheck_api():
    api = RugCheckAPI()
    yield api
    await api.close()


@pytest.mark.asyncio
async def test_request_success(rugcheck_api, mocker):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": "test"}
    mocker.patch.object(rugcheck_api.session, "get", return_value=mock_response)

    result = await rugcheck_api._request("/test")
    assert result == {"data": "test"}
    rugcheck_api.session.get.assert_called_once_with(f"{rugcheck_api.BASE_URL}/test")


@pytest.mark.asyncio
async def test_request_failure(rugcheck_api, mocker):
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text.return_value = "Bad Request"
    mocker.patch.object(rugcheck_api.session, "get", return_value=mock_response)

    with pytest.raises(Exception, match="Error 400: Bad Request"):
        await rugcheck_api._request("/test")


@pytest.mark.asyncio
async def test_get_token_report(rugcheck_api, mocker):
    mock_response = {"report": "token_data"}
    mocker.patch.object(rugcheck_api, "_request", AsyncMock(return_value=mock_response))

    result = await rugcheck_api.get_token_report("0x123")
    assert result == mock_response
    rugcheck_api._request.assert_called_once_with("/tokens/0x123/report")


@pytest.mark.asyncio
async def test_close_session(rugcheck_api, mocker):
    mock_close = mocker.patch.object(rugcheck_api.session, "close", new=AsyncMock())
    await rugcheck_api.close()
    mock_close.assert_called_once()

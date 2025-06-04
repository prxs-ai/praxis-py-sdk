from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from shared_utils.http_client import HttpClient


@pytest.fixture
def http_client():
    return HttpClient(base_url="https://api.example.com")


@pytest.mark.asyncio
async def test_post_success(http_client, mocker):
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 200
    mock_session_post = mocker.patch(
        "aiohttp.ClientSession.post", return_value=mock_response
    )

    data = {"key": "value"}
    headers = {"Authorization": "Bearer token"}
    response = await http_client.post("/test", data=data, headers=headers)

    assert response == mock_response
    mock_session_post.assert_called_once_with(
        "https://api.example.com/test", data=data, headers=headers
    )


@pytest.mark.asyncio
async def test_post_failure(http_client, mocker):
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 400
    mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=None, history=None, status=400, message="Bad Request"
    )
    mocker.patch("aiohttp.ClientSession.post", return_value=mock_response)

    data = {"key": "value"}
    with pytest.raises(aiohttp.ClientResponseError):
        await http_client.post("/test", data=data)


@pytest.mark.asyncio
async def test_get_success(http_client, mocker):
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 200
    mock_session_get = mocker.patch(
        "aiohttp.ClientSession.get", return_value=mock_response
    )

    headers = {"Authorization": "Bearer token"}
    response = await http_client.get("/test", headers=headers)

    assert response == mock_response
    mock_session_get.assert_called_once_with(
        "https://api.example.com/test", headers=headers
    )


@pytest.mark.asyncio
async def test_get_failure(http_client, mocker):
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 404
    mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=None, history=None, status=404, message="Not Found"
    )
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_response)

    with pytest.raises(aiohttp.ClientResponseError):
        await http_client.get("/test", headers={})

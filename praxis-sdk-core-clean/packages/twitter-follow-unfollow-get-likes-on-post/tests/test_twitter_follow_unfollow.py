from unittest.mock import AsyncMock

import aiohttp
import pytest
from agents_tools_logger.main import log
from twitter_follow_unfollow_get_likes_on_post.main import get_likes_on_post


@pytest.mark.asyncio
async def test_get_likes_on_post_success(mocker):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": [{"id": "user1"}, {"id": "user2"}]}
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_response)
    mocker.patch.object(log, "info")

    result = await get_likes_on_post("token123", "tweet456")
    assert result == {"data": [{"id": "user1"}, {"id": "user2"}]}
    aiohttp.ClientSession.get.assert_called_once_with(
        "https://api.x.com/2/tweets/tweet456/liking_users",
        headers={"Authorization": "Bearer token123"},
    )
    log.info.assert_any_call("Getting user notifications")
    log.info.assert_any_call(
        "Notifications received: {'data': [{'id': 'user1'}, {'id': 'user2'}]}"
    )


@pytest.mark.asyncio
async def test_get_likes_on_post_failure(mocker):
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text.return_value = "Bad Request"
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_response)
    mocker.patch.object(log, "info")

    result = await get_likes_on_post("token123", "tweet456")
    assert result is None
    aiohttp.ClientSession.get.assert_called_once_with(
        "https://api.x.com/2/tweets/tweet456/liking_users",
        headers={"Authorization": "Bearer token123"},
    )
    log.info.assert_any_call("Getting user notifications")
    log.info.assert_any_call("Notifications not received: Bad Request")

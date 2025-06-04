from datetime import datetime
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from twitter_ambassador_utils import (
    TwitterAuthClient,
    create_post,
    post_request,
    retweet,
    set_like,
)


@pytest.fixture
def mock_settings():
    class MockSettings:
        TWITTER_CLIENT_ID = "test_client_id"
        TWITTER_CLIENT_SECRET = "test_client_secret"
        TWITTER_REDIRECT_URI = "https://example.com/callback"
        TWITTER_BASIC_BEARER_TOKEN = "test_bearer_token"

    return MockSettings()


@pytest.fixture
def mock_redis():
    mock = Mock()
    mock.hgetall.return_value = {}
    mock.hmset = Mock()
    mock.delete = Mock()
    mock.expire = Mock()
    return mock


@pytest.fixture
def twitter_auth_client(mock_settings, mock_redis, mocker):
    mocker.patch("twitter_ambassador_utils.get_settings", return_value=mock_settings)
    mocker.patch("twitter_ambassador_utils.get_redis_db", return_value=mock_redis)
    return TwitterAuthClient


@pytest.mark.asyncio
async def test_post_request_success(mocker):
    mock_response = AsyncMock()
    mock_response.ok = True
    mock_response.json.return_value = {"data": "success"}
    mocker.patch("aiohttp.ClientSession.post", return_value=mock_response)
    mocker.patch("loguru.logger.info")

    result = await post_request("https://api.x.com/test", "token", {"key": "value"})
    assert result == {"data": "success"}
    aiohttp.ClientSession.post.assert_called_once()


@pytest.mark.asyncio
async def test_post_request_failure(mocker):
    mock_response = AsyncMock()
    mock_response.ok = False
    mock_response.status = 400
    mock_response.text.return_value = "Bad Request"
    mock_response.json.return_value = {"error": "bad request"}
    mocker.patch("aiohttp.ClientSession.post", return_value=mock_response)
    mocker.patch("loguru.logger.error")

    result = await post_request("https://api.x.com/test", "token", {"key": "value"})
    assert result == {"error": "bad request"}
    aiohttp.ClientSession.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_post_success(mocker):
    mock_response = AsyncMock()
    mock_response.status = 201
    mock_response.json.return_value = {"data": {"id": "123"}}
    mocker.patch("aiohttp.ClientSession.post", return_value=mock_response)
    mocker.patch("loguru.logger.info")

    result = await create_post(
        "token", "Test tweet", quote_tweet_id="456", commented_tweet_id="789"
    )
    assert result == {"data": {"id": "123"}}
    aiohttp.ClientSession.post.assert_called_once_with(
        "https://api.x.com/2/tweets",
        json={
            "text": "Test tweet",
            "quote_tweet_id": "456",
            "reply": {"in_reply_to_tweet_id": "789"},
        },
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
    )


@pytest.mark.asyncio
async def test_create_post_failure(mocker):
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text.return_value = "Bad Request"
    mocker.patch("aiohttp.ClientSession.post", return_value=mock_response)
    mocker.patch("loguru.logger.error")

    await create_post("token", "Test tweet")
    aiohttp.ClientSession.post.assert_called_once()
    loguru.logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_retweet(mocker):
    mocker.patch(
        "twitter_ambassador_utils.post_request",
        AsyncMock(return_value={"data": "retweeted"}),
    )
    result = await retweet("token", "user123", "tweet456")
    assert result == {"data": "retweeted"}
    twitter_ambassador_utils.post_request.assert_called_once_with(
        "https://api.x.com/2/users/user123/retweets", "token", {"tweet_id": "tweet456"}
    )


@pytest.mark.asyncio
async def test_set_like(mocker):
    mocker.patch(
        "twitter_ambassador_utils.post_request",
        AsyncMock(return_value={"data": "liked"}),
    )
    result = await set_like("token", "user123", "tweet456")
    assert result == {"data": "liked"}
    twitter_ambassador_utils.post_request.assert_called_once_with(
        "https://api.x.com/2/users/user123/likes", "token", {"tweet_id": "tweet456"}
    )


@pytest.mark.asyncio
async def test_create_auth_link(twitter_auth_client, mocker):
    mocker.patch("os.urandom", return_value=b"random_bytes")
    mocker.patch("base64.urlsafe_b64encode", return_value=b"code_verifier_encoded")
    mocker.patch(
        "hashlib.sha256", return_value=Mock(digest=Mock(return_value=b"sha256_digest"))
    )
    mocker.patch.object(
        twitter_auth_client._CLIENT,
        "authorization_url",
        return_value=("https://auth.url", "state123"),
    )
    mocker.patch.object(twitter_auth_client, "_store_session_data")

    url = twitter_auth_client.create_auth_link()
    assert url == "https://auth.url"
    twitter_auth_client._store_session_data.assert_called_once_with(
        session_id="state123",
        data={
            "code_challenge": "code_verifier_encoded",
            "code_verifier": "code_verifier_encoded",
        },
        ex=60,
    )


@pytest.mark.asyncio
async def test_callback_success(twitter_auth_client, mocker):
    mocker.patch.object(
        twitter_auth_client,
        "get_tokens",
        AsyncMock(
            return_value={
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_at": 1234567890,
            }
        ),
    )
    mocker.patch.object(
        twitter_auth_client,
        "get_me",
        AsyncMock(
            return_value={
                "name": "Test User",
                "username": "testuser",
                "twitter_id": "123",
            }
        ),
    )
    mocker.patch.object(twitter_auth_client, "save_twitter_data")

    result = await twitter_auth_client.callback("state123", "code456")
    assert result is True
    twitter_auth_client.save_twitter_data.assert_called_once_with(
        access_token="access",
        refresh_token="refresh",
        expires_at=1234567890,
        name="Test User",
        username="testuser",
        twitter_id="123",
    )


@pytest.mark.asyncio
async def test_get_tokens(twitter_auth_client, mocker):
    mocker.patch.object(
        twitter_auth_client,
        "get_session_data",
        return_value={"code_verifier": "verifier"},
    )
    mocker.patch.object(
        twitter_auth_client._CLIENT,
        "fetch_token",
        return_value={
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": 1234567890,
        },
    )

    result = await twitter_auth_client.get_tokens("state123", "code456")
    assert result == {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_at": 1234567890,
    }
    twitter_auth_client._CLIENT.fetch_token.assert_called_once()


@pytest.mark.asyncio
async def test_get_me_success(twitter_auth_client, mocker):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "data": {"name": "Test User", "username": "testuser", "id": "123"}
    }
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_response)

    result = await twitter_auth_client.get_me("token")
    assert result == {"name": "Test User", "username": "testuser", "twitter_id": "123"}
    aiohttp.ClientSession.get.assert_called_once_with(
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": "Bearer token"},
        timeout=aiohttp.ClientTimeout(10),
    )


@pytest.mark.asyncio
async def test_get_me_failure(twitter_auth_client, mocker):
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.json.return_value = {"error": "bad request"}
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_response)
    mocker.patch("loguru.logger.error")

    result = await twitter_auth_client.get_me("token")
    assert result is None
    loguru.logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_generate_code_verifier(twitter_auth_client, mocker):
    mocker.patch("os.urandom", return_value=b"random_bytes")
    mocker.patch("base64.urlsafe_b64encode", return_value=b"code_verifier_encoded")
    result = twitter_auth_client._generate_code_verifier()
    assert result == "code_verifier_encoded"


@pytest.mark.asyncio
async def test_generate_code_challenge(twitter_auth_client, mocker):
    mocker.patch(
        "hashlib.sha256", return_value=Mock(digest=Mock(return_value=b"sha256_digest"))
    )
    mocker.patch("base64.urlsafe_b64encode", return_value=b"code_challenge_encoded==")
    result = twitter_auth_client._generate_code_challenge("verifier")
    assert result == "code_challenge_encoded"


@pytest.mark.asyncio
async def test_store_session_data(twitter_auth_client, mock_redis):
    twitter_auth_client._store_session_data("state123", {"key": "value"}, 60)
    mock_redis.hmset.assert_called_once_with(
        "session:state123", mapping={"key": "value"}
    )
    mock_redis.expire.assert_called_once_with("session:state123", 60)


@pytest.mark.asyncio
async def test_get_session_data(twitter_auth_client, mock_redis, mocker):
    mock_redis.hgetall.return_value = {b"key": b"value"}
    mocker.patch("twitter_ambassador_utils.decode_redis", return_value={"key": "value"})
    result = twitter_auth_client.get_session_data("state123")
    assert result == {"key": "value"}
    mock_redis.hgetall.assert_called_once_with("session:state123")


@pytest.mark.asyncio
async def test_save_twitter_data(twitter_auth_client, mock_redis, mocker):
    mocker.patch("twitter_ambassador_utils.cipher.encrypt", side_effect=lambda x: x)
    twitter_auth_client.save_twitter_data(
        access_token="access",
        refresh_token="refresh",
        expires_at=1234567890,
        name="Test User",
        username="testuser",
        twitter_id="123",
        user_id="456",
    )
    mock_redis.hmset.assert_called_once_with(
        "twitter_data:testuser",
        mapping={
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": 1234567890,
            "name": "Test User",
            "username": "testuser",
            "id": "123",
            "user_id": "456",
        },
    )


@pytest.mark.asyncio
async def test_refresh_tokens(twitter_auth_client, mocker):
    mocker.patch.object(
        twitter_auth_client._CLIENT,
        "refresh_token",
        return_value={
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_at": 1234567890,
        },
    )
    result = await twitter_auth_client._refresh_tokens("refresh")
    assert result == {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_at": 1234567890,
    }
    twitter_auth_client._CLIENT.refresh_token.assert_called_once()


@pytest.mark.asyncio
async def test_update_tokens(twitter_auth_client, mock_redis, mocker):
    mocker.patch.object(
        twitter_auth_client,
        "_refresh_tokens",
        AsyncMock(
            return_value={
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_at": 1234567890,
            }
        ),
    )
    mocker.patch("twitter_ambassador_utils.cipher.encrypt", side_effect=lambda x: x)
    result = await twitter_auth_client.update_tokens("refresh", "testuser")
    assert result == {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_at": 1234567890,
    }
    mock_redis.hmset.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect_twitter(twitter_auth_client, mock_redis):
    await twitter_auth_client.disconnect_twitter("testuser")
    mock_redis.delete.assert_called_once_with("twitter_data:testuser")


@pytest.mark.asyncio
async def test_get_twitter_data_valid(twitter_auth_client, mock_redis, mocker):
    mock_redis.hgetall.return_value = {
        b"access_token": b"encrypted_access",
        b"refresh_token": b"encrypted_refresh",
        b"expires_at": b"1234567890",
        b"name": b"Test User",
        b"username": b"testuser",
        b"id": b"123",
        b"auth_token": b"auth",
        b"csrf_token": b"csrf",
        b"guest_id": b"guest",
    }
    mocker.patch(
        "twitter_ambassador_utils.decode_redis",
        return_value={
            "access_token": "encrypted_access",
            "refresh_token": "encrypted_refresh",
            "expires_at": "1234567890",
            "name": "Test User",
            "username": "testuser",
            "id": "123",
            "auth_token": "auth",
            "csrf_token": "csrf",
            "guest_id": "guest",
        },
    )
    mocker.patch("twitter_ambassador_utils.cipher.decrypt", return_value=b"access")
    mocker.patch(
        "datetime.datetime.utcfromtimestamp", return_value=datetime(2023, 1, 1)
    )
    mocker.patch("datetime.datetime.utcnow", return_value=datetime(2023, 1, 2))

    mocker.patch.object(
        twitter_auth_client,
        "update_tokens",
        AsyncMock(
            return_value={
                "access_token": "new_encrypted_access",
                "refresh_token": "new_encrypted_refresh",
                "expires_at": 1234567890,
            }
        ),
    )
    mocker.patch(
        "twitter_ambassador_utils.cipher.decrypt",
        side_effect=[b"refresh", b"new_access"],
    )

    result = await twitter_auth_client.get_twitter_data("testuser")
    assert result == {
        "name": "Test User",
        "username": "testuser",
        "id": "123",
        "access_token": "new_encrypted_access",
        "auth_token": "auth",
        "csrf_token": "csrf",
        "guest_id": "guest",
    }
    twitter_auth_client.update_tokens.assert_called_once_with("refresh", "testuser")


@pytest.mark.asyncio
async def test_get_twitter_data_no_data(twitter_auth_client, mock_redis):
    mock_redis.hgetall.return_value = {}
    mocker.patch("twitter_ambassador_utils.decode_redis", return_value={})
    result = await twitter_auth_client.get_twitter_data("testuser")
    assert result is None


@pytest.mark.asyncio
async def test_get_static_data(twitter_auth_client, mock_redis, mocker):
    mock_redis.hgetall.return_value = {
        b"name": b"Test User",
        b"username": b"testuser",
        b"id": b"123",
        b"auth_token": b"auth",
        b"csrf_token": b"csrf",
        b"guest_id": b"guest",
    }
    mocker.patch(
        "twitter_ambassador_utils.decode_redis",
        return_value={
            "name": "Test User",
            "username": "testuser",
            "id": "123",
            "auth_token": "auth",
            "csrf_token": "csrf",
            "guest_id": "guest",
        },
    )
    result = twitter_auth_client.get_static_data("testuser")
    assert result == {
        "name": "Test User",
        "username": "testuser",
        "id": "123",
        "auth_token": "auth",
        "csrf_token": "csrf",
        "guest_id": "guest",
    }


@pytest.mark.asyncio
async def test_get_access_token_success(twitter_auth_client, mocker):
    mocker.patch.object(
        twitter_auth_client,
        "get_twitter_data",
        AsyncMock(
            return_value={"access_token": "encrypted_access", "username": "testuser"}
        ),
    )
    mocker.patch("twitter_ambassador_utils.cipher.decrypt", return_value=b"access")
    mocker.patch("loguru.logger.info")

    result = await twitter_auth_client.get_access_token("testuser")
    assert result == "access"
    loguru.logger.info.assert_called_once_with("Decoded access token successfully")


@pytest.mark.asyncio
async def test_get_access_token_no_data(twitter_auth_client, mocker):
    mocker.patch.object(
        twitter_auth_client, "get_twitter_data", AsyncMock(return_value=None)
    )
    mocker.patch("loguru.logger.error")
    with pytest.raises(ValueError, match="Twitter data not found for user testuser"):
        await twitter_auth_client.get_access_token("testuser")
    loguru.logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_get_access_token_decrypt_error(twitter_auth_client, mocker):
    mocker.patch.object(
        twitter_auth_client,
        "get_twitter_data",
        AsyncMock(return_value={"access_token": "invalid", "username": "testuser"}),
    )
    mocker.patch(
        "twitter_ambassador_utils.cipher.decrypt",
        side_effect=TypeError("Decrypt error"),
    )
    mocker.patch("loguru.logger.error")
    with pytest.raises(TypeError):
        await twitter_auth_client.get_access_token("testuser")
    loguru.logger.error.assert_called_once()

import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from loguru import logger

with patch("redis_client.config.Settings") as mock_settings:
    mock_settings.return_value = MagicMock(
        REDIS_HOST="mock_host",
        REDIS_PORT=6379,
        REDIS_DB=0,
    )
    with patch("redis_client.main.RedisDB"):
        from twitter_ambassador_utils.main import (
            post_request, create_post, retweet, set_like, TwitterAuthClient
        )


# Фикстуры
@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.TWITTER_CLIENT_ID = "test_client_id"
    settings.TWITTER_CLIENT_SECRET = "test_client_secret"
    settings.TWITTER_REDIRECT_URI = "https://example.com/callback"
    settings.TWITTER_BASIC_BEARER_TOKEN = "test_bearer_token"
    return settings


@pytest.fixture
def mock_aiohttp_session():
    session = AsyncMock()
    session.post = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
async def mock_client_session(mock_aiohttp_session):
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        yield mock_aiohttp_session


@pytest.fixture
def mock_redis_db():
    redis_db = MagicMock()
    redis_db.r.hgetall.return_value = {}
    redis_db.r.hmset = MagicMock()
    redis_db.r.delete = MagicMock()
    redis_db.r.expire = MagicMock()
    return redis_db


@pytest.fixture
def mock_cipher():
    cipher = MagicMock()
    cipher.encrypt.return_value = b"encrypted_data"
    cipher.decrypt.return_value = b"decrypted_data"
    return cipher


@pytest.fixture
def mock_oauth2_session():
    oauth_session = MagicMock()
    oauth_session.authorization_url.return_value = (
        "https://twitter.com/i/oauth2/authorize?state=test_state", "test_state")
    oauth_session.fetch_token.return_value = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": 1234567890
    }
    oauth_session.refresh_token.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_at": 1234567891
    }
    return oauth_session


@pytest.fixture
def mock_logger():
    with patch.object(logger, "info") as mock_info, patch.object(logger, "error") as mock_error:
        yield {"info": mock_info, "error": mock_error}


# Тесты для асинхронных функций
@pytest.mark.asyncio
async def test_post_request_success(mock_client_session, mock_logger):
    response = AsyncMock()
    response.ok = True
    response.json = AsyncMock(return_value={"data": "success"})
    mock_client_session.post.return_value.__aenter__.return_value = response

    result = await post_request("https://api.x.com/2/test", "test_token", {"key": "value"})
    assert result == {"data": "success"}
    mock_client_session.post.assert_called_with(
        "https://api.x.com/2/test",
        headers={"Authorization": "Bearer test_token", "Content-Type": "application/json"},
        json={"key": "value"}
    )
    mock_logger["info"].assert_called_with("Request successful: {'data': 'success'}")


@pytest.mark.asyncio
async def test_post_request_failure(mock_client_session, mock_logger):
    response = AsyncMock()
    response.ok = False
    response.status = 400
    response.text = AsyncMock(return_value="Bad request")
    response.json = AsyncMock(return_value={"error": "bad request"})
    mock_client_session.post.return_value.__aenter__.return_value = response

    result = await post_request("https://api.x.com/2/test", "test_token", {"key": "value"})
    assert result == {"error": "bad request"}
    mock_logger["error"].assert_called_with("Request failed. Status: 400, Response: Bad request")


@pytest.mark.asyncio
async def test_create_post_simple(mock_client_session, mock_logger):
    response = AsyncMock()
    response.status = 201
    response.json = AsyncMock(return_value={"data": {"id": "123"}})
    mock_client_session.post.return_value.__aenter__.return_value = response

    result = await create_post("test_access_token", "Test tweet")
    assert result == {"data": {"id": "123"}}
    mock_client_session.post.assert_called_with(
        "https://api.x.com/2/tweets",
        json={"text": "Test tweet"},
        headers={"Authorization": "Bearer test_access_token", "Content-Type": "application/json"}
    )
    mock_logger["info"].assert_called_with("Tweet posted: {'data': {'id': '123'}}")


@pytest.mark.asyncio
async def test_create_post_with_quote(mock_client_session):
    response = AsyncMock()
    response.status = 201
    response.json = AsyncMock(return_value={"data": {"id": "123"}})
    mock_client_session.post.return_value.__aenter__.return_value = response

    result = await create_post("test_access_token", "Test tweet", quote_tweet_id="456")
    assert result == {"data": {"id": "123"}}
    mock_client_session.post.assert_called_with(
        "https://api.x.com/2/tweets",
        json={"text": "Test tweet", "quote_tweet_id": "456"},
        headers={"Authorization": "Bearer test_access_token", "Content-Type": "application/json"}
    )


@pytest.mark.asyncio
async def test_create_post_with_comment(mock_client_session):
    response = AsyncMock()
    response.status = 201
    response.json = AsyncMock(return_value={"data": {"id": "123"}})
    mock_client_session.post.return_value.__aenter__.return_value = response

    result = await create_post("test_access_token", "Test tweet", commented_tweet_id="789")
    assert result == {"data": {"id": "123"}}
    mock_client_session.post.assert_called_with(
        "https://api.x.com/2/tweets",
        json={"text": "Test tweet", "reply": {"in_reply_to_tweet_id": "789"}},
        headers={"Authorization": "Bearer test_access_token", "Content-Type": "application/json"}
    )


@pytest.mark.asyncio
async def test_create_post_failure(mock_client_session, mock_logger):
    response = AsyncMock()
    response.status = 400
    response.text = AsyncMock(return_value="Bad request")
    mock_client_session.post.return_value.__aenter__.return_value = response

    result = await create_post("test_access_token", "Test tweet")
    assert result is None
    mock_logger["error"].assert_called_with("Twit not posted: Bad request")


@pytest.mark.asyncio
async def test_retweet(mock_client_session):
    with patch("twitter_ambassador_utils.main.post_request") as mock_post_request:
        mock_post_request.return_value = {"data": {"retweeted": True}}
        result = await retweet("test_token", "user_123", "tweet_456")
        assert result == {"data": {"retweeted": True}}
        mock_post_request.assert_called_with(
            "https://api.x.com/2/users/user_123/retweets",
            "test_token",
            {"tweet_id": "tweet_456"}
        )


@pytest.mark.asyncio
async def test_set_like(mock_client_session):
    with patch("twitter_ambassador_utils.main.post_request") as mock_post_request:
        mock_post_request.return_value = {"data": {"liked": True}}
        result = await set_like("test_token", "user_123", "tweet_456")
        assert result == {"data": {"liked": True}}
        mock_post_request.assert_called_with(
            "https://api.x.com/2/users/user_123/likes",
            "test_token",
            {"tweet_id": "tweet_456"}
        )


# Тесты для TwitterAuthClient
@pytest.fixture
def twitter_auth_client(mock_redis_db, mock_oauth2_session, mock_settings, mock_cipher):
    with patch("twitter_ambassador_utils.main.get_redis_db", return_value=mock_redis_db):
        with patch("twitter_ambassador_utils.main.get_settings", return_value=mock_settings):
            with patch("twitter_ambassador_utils.main.cipher", mock_cipher):
                with patch("twitter_ambassador_utils.main.OAuth2Session", return_value=mock_oauth2_session):
                    return TwitterAuthClient()


def test_create_auth_link(twitter_auth_client, mock_redis_db):
    with patch.object(TwitterAuthClient, "_generate_code_verifier", return_value="code_verifier"):
        with patch.object(TwitterAuthClient, "_generate_code_challenge", return_value="code_challenge"):
            url = TwitterAuthClient.create_auth_link()
            assert url == "https://twitter.com/i/oauth2/authorize?state=test_state"
            mock_redis_db.r.hmset.assert_called_with(
                "session:test_state",
                mapping={"code_challenge": "code_challenge", "code_verifier": "code_verifier"}
            )
            mock_redis_db.r.expire.assert_called_with("session:test_state", 60)


def test_generate_code_verifier(twitter_auth_client):
    with patch("os.urandom", return_value=b"random_data"):
        with patch("base64.urlsafe_b64encode", return_value=b"random_data_encoded"):
            verifier = TwitterAuthClient._generate_code_verifier()
            assert verifier == "random_data_encoded"


def test_generate_code_challenge(twitter_auth_client):
    with patch("hashlib.sha256") as mock_sha256:
        mock_sha256.return_value.digest.return_value = b"hashed_data"
        with patch("base64.urlsafe_b64encode", return_value=b"hashed_data_encoded="):
            challenge = TwitterAuthClient._generate_code_challenge("code_verifier")
            assert challenge == "hashed_data_encoded"


def test_store_session_data(twitter_auth_client, mock_redis_db):
    TwitterAuthClient._store_session_data("test_session", {"key": "value"}, 60)
    mock_redis_db.r.hmset.assert_called_with("session:test_session", mapping={"key": "value"})
    mock_redis_db.r.expire.assert_called_with("session:test_session", 60)


def test_get_session_data(twitter_auth_client, mock_redis_db):
    mock_redis_db.r.hgetall.return_value = {b"key": b"value"}
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={"key": "value"}):
        result = TwitterAuthClient.get_session_data("test_session")
        assert result == {"key": "value"}


def test_get_session_data_none(twitter_auth_client, mock_redis_db):
    mock_redis_db.r.hgetall.return_value = {}
    result = TwitterAuthClient.get_session_data("test_session")
    assert result is None


@pytest.mark.asyncio
async def test_get_tokens(twitter_auth_client, mock_redis_db, mock_oauth2_session):
    mock_redis_db.r.hgetall.return_value = {b"code_verifier": b"test_verifier"}
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={"code_verifier": "test_verifier"}):
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value={
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "expires_at": 1234567890
            })
            result = await TwitterAuthClient.get_tokens("test_state", "test_code")
            assert result == {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "expires_at": 1234567890
            }


@pytest.mark.asyncio
async def test_get_tokens_no_session_data(twitter_auth_client, mock_redis_db):
    mock_redis_db.r.hgetall.return_value = {}
    result = await TwitterAuthClient.get_tokens("test_state", "test_code")
    assert result is None


@pytest.mark.asyncio
async def test_get_me_success(mock_client_session, mock_logger):
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={
        "data": {"name": "Test User", "username": "testuser", "id": "123"}
    })
    mock_client_session.get.return_value.__aenter__.return_value = response

    result = await TwitterAuthClient.get_me("test_access_token")
    assert result == {"name": "Test User", "username": "testuser", "twitter_id": "123"}
    mock_logger["info"].assert_called_with("Get me twitter")


@pytest.mark.asyncio
async def test_get_me_suspended(mock_client_session, mock_logger):
    response = AsyncMock()
    response.status = 403
    response.json = AsyncMock(return_value={"detail": "User is suspended"})
    mock_client_session.get.return_value.__aenter__.return_value = response

    with pytest.raises(aiohttp.ClientResponseError):
        await TwitterAuthClient.get_me("test_access_token")


@pytest.mark.asyncio
async def test_get_me_failure(mock_client_session, mock_logger):
    response = AsyncMock()
    response.status = 400
    response.json = AsyncMock(return_value={"error": "bad request"})
    mock_client_session.get.return_value.__aenter__.return_value = response

    result = await TwitterAuthClient.get_me("test_access_token")
    assert result is None
    mock_logger["error"].assert_called_with("Bad request to twitter get_me - {'error': 'bad request'}")


def test_save_twitter_data(twitter_auth_client, mock_redis_db, mock_cipher):
    TwitterAuthClient.save_twitter_data(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=1234567890,
        name="Test User",
        username="testuser",
        twitter_id="123"
    )
    mock_redis_db.r.hmset.assert_called_with(
        "twitter_data:testuser",
        mapping={
            "access_token": "encrypted_data",
            "refresh_token": "encrypted_data",
            "expires_at": 1234567890,
            "name": "Test User",
            "username": "testuser",
            "id": "123",
            "user_id": "123"
        }
    )


@pytest.mark.asyncio
async def test_refresh_tokens(twitter_auth_client, mock_oauth2_session):
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_at": 1234567891
        })
        result = await TwitterAuthClient._refresh_tokens("test_refresh_token")
        assert result == {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_at": 1234567891
        }


@pytest.mark.asyncio
async def test_update_tokens(twitter_auth_client, mock_redis_db, mock_cipher):
    with patch.object(TwitterAuthClient, "_refresh_tokens", return_value={
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_at": 1234567891
    }):
        result = await TwitterAuthClient.update_tokens("test_refresh_token", "testuser")
        assert result == {
            "access_token": "encrypted_data",
            "refresh_token": "encrypted_data",
            "expires_at": 1234567891
        }
        mock_redis_db.r.hmset.assert_called_with(
            "twitter_data:testuser",
            mapping={
                "access_token": "encrypted_data",
                "refresh_token": "encrypted_data",
                "expires_at": 1234567891
            }
        )


@pytest.mark.asyncio
async def test_disconnect_twitter(twitter_auth_client, mock_redis_db):
    await TwitterAuthClient.disconnect_twitter("testuser")
    mock_redis_db.r.delete.assert_called_with("twitter_data:testuser")


@pytest.mark.asyncio
async def test_get_twitter_data_valid_token(twitter_auth_client, mock_redis_db, mock_cipher):
    mock_redis_db.r.hgetall.return_value = {
        b"access_token": b"encrypted_access_token",
        b"refresh_token": b"encrypted_refresh_token",
        b"expires_at": b"9999999999",
        b"name": b"Test User",
        b"username": b"testuser",
        b"id": b"123"
    }
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={
        "access_token": "encrypted_access_token",
        "refresh_token": "encrypted_refresh_token",
        "expires_at": "9999999999",
        "name": "Test User",
        "username": "testuser",
        "id": "123"
    }):
        with patch("datetime.utcnow", return_value=datetime(2000, 1, 1)):
            result = await TwitterAuthClient.get_twitter_data("testuser")
            assert result == {
                "name": "Test User",
                "username": "testuser",
                "id": "123",
                "access_token": "encrypted_access_token",
                "auth_token": None,
                "csrf_token": None,
                "guest_id": None
            }


@pytest.mark.asyncio
async def test_get_twitter_data_expired_token(twitter_auth_client, mock_redis_db, mock_cipher):
    mock_redis_db.r.hgetall.return_value = {
        b"access_token": b"encrypted_access_token",
        b"refresh_token": b"encrypted_refresh_token",
        b"expires_at": b"946684800",  # 2000-01-01
        b"name": b"Test User",
        b"username": b"testuser",
        b"id": b"123"
    }
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={
        "access_token": "encrypted_access_token",
        "refresh_token": "encrypted_refresh_token",
        "expires_at": "946684800",
        "name": "Test User",
        "username": "testuser",
        "id": "123"
    }):
        with patch("datetime.utcnow", return_value=datetime(2025, 1, 1)):
            with patch.object(TwitterAuthClient, "update_tokens", return_value={
                "access_token": "new_encrypted_access_token",
                "refresh_token": "new_encrypted_refresh_token",
                "expires_at": 1234567891
            }):
                result = await TwitterAuthClient.get_twitter_data("testuser")
                assert result["access_token"] == "new_encrypted_access_token"


@pytest.mark.asyncio
async def test_get_twitter_data_no_data(twitter_auth_client, mock_redis_db):
    mock_redis_db.r.hgetall.return_value = {}
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={}):
        result = await TwitterAuthClient.get_twitter_data("testuser")
        assert result is None


@pytest.mark.asyncio
async def test_get_access_token_success(twitter_auth_client, mock_redis_db, mock_cipher, mock_logger):
    mock_redis_db.r.hgetall.return_value = {
        b"access_token": b"encrypted_access_token",
        b"refresh_token": b"encrypted_refresh_token",
        b"expires_at": b"9999999999",
        b"name": b"Test User",
        b"username": b"testuser",
        b"id": b"123"
    }
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={
        "access_token": "encrypted_access_token",
        "refresh_token": "encrypted_refresh_token",
        "expires_at": "9999999999",
        "name": "Test User",
        "username": "testuser",
        "id": "123"
    }):
        with patch("datetime.utcnow", return_value=datetime(2000, 1, 1)):
            result = await TwitterAuthClient.get_access_token("testuser")
            assert result == "decrypted_data"
            mock_logger["info"].assert_called_with("Decoded access token successfully")


@pytest.mark.asyncio
async def test_get_access_token_no_data(twitter_auth_client, mock_redis_db, mock_logger):
    mock_redis_db.r.hgetall.return_value = {}
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={}):
        with pytest.raises(ValueError, match="Twitter data not found for user testuser"):
            await TwitterAuthClient.get_access_token("testuser")
            mock_logger["error"].assert_called_with("No twitter data found for testuser")


@pytest.mark.asyncio
async def test_get_access_token_decrypt_error(twitter_auth_client, mock_redis_db, mock_cipher, mock_logger):
    mock_redis_db.r.hgetall.return_value = {
        b"access_token": b"encrypted_access_token",
        b"refresh_token": b"encrypted_refresh_token",
        b"expires_at": b"9999999999",
        b"name": b"Test User",
        b"username": b"testuser",
        b"id": b"123"
    }
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={
        "access_token": "encrypted_access_token",
        "refresh_token": "encrypted_refresh_token",
        "expires_at": "9999999999",
        "name": "Test User",
        "username": "testuser",
        "id": "123"
    }):
        mock_cipher.decrypt.side_effect = TypeError("Decrypt error")
        with pytest.raises(TypeError, match="Decrypt error"):
            await TwitterAuthClient.get_access_token("testuser")
            mock_logger["error"].assert_called_with("Error decrypting access token for testuser: Decrypt error")


@pytest.mark.asyncio
async def test_callback(twitter_auth_client, mock_redis_db, mock_cipher):
    mock_redis_db.r.hgetall.return_value = {b"code_verifier": b"test_verifier"}
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={"code_verifier": "test_verifier"}):
        with patch.object(TwitterAuthClient, "get_tokens", return_value={
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": 1234567890
        }):
            with patch.object(TwitterAuthClient, "get_me", return_value={
                "name": "Test User",
                "username": "testuser",
                "twitter_id": "123"
            }):
                with patch.object(TwitterAuthClient, "save_twitter_data") as mock_save:
                    result = await TwitterAuthClient.callback("test_state", "test_code")
                    assert result is True
                    mock_save.assert_called_with(
                        access_token="test_access_token",
                        refresh_token="test_refresh_token",
                        expires_at=1234567890,
                        name="Test User",
                        username="testuser",
                        twitter_id="123"
                    )


def test_get_static_data(twitter_auth_client, mock_redis_db):
    mock_redis_db.r.hgetall.return_value = {
        b"name": b"Test User",
        b"username": b"testuser",
        b"id": b"123",
        b"auth_token": b"auth_token",
        b"csrf_token": b"csrf_token",
        b"guest_id": b"guest_id"
    }
    with patch("twitter_ambassador_utils.main.decode_redis", return_value={
        "name": "Test User",
        "username": "testuser",
        "id": "123",
        "auth_token": "auth_token",
        "csrf_token": "csrf_token",
        "guest_id": "guest_id"
    }):
        result = TwitterAuthClient.get_static_data("testuser")
        assert result == {
            "name": "Test User",
            "username": "testuser",
            "id": "123",
            "auth_token": "auth_token",
            "csrf_token": "csrf_token",
            "guest_id": "guest_id"
        }

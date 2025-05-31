import pytest
from unittest.mock import AsyncMock, patch
from tweetscout_utils import (
    User, QuotedStatus, RetweetedStatus, Tweet,
    parse_user, parse_retweeted_status, parse_quoted_status, parse_tweet,
    _make_request, fetch_user_tweets, search_tweets, get_tweet_by_link,
    get_conversation_from_tweet, create_conversation_string
)
import aiohttp


@pytest.fixture
def mock_settings():
    class MockSettings:
        TWEETSCOUT_API_KEY = "test_key"

    return MockSettings()


@pytest.fixture
def sample_user_data():
    return {
        "id_str": "123",
        "name": "Test User",
        "screen_name": "testuser",
        "description": "Test description",
        "followers_count": 100,
        "friends_count": 50,
        "statuses_count": 200,
        "created_at": "2023-01-01",
        "can_dm": True
    }


@pytest.fixture
def sample_tweet_data(sample_user_data):
    return {
        "created_at": "2023-01-01",
        "id_str": "456",
        "full_text": "Test tweet",
        "user": sample_user_data,
        "retweet_count": 10,
        "favorite_count": 20,
        "is_quote_status": False,
        "conversation_id_str": "789",
        "in_reply_to_status_id_str": None
    }


@pytest.mark.asyncio
async def test_parse_user(sample_user_data):
    user = parse_user(sample_user_data)
    assert user.id_str == "123"
    assert user.name == "Test User"
    assert user.screen_name == "testuser"
    assert user.description == "Test description"
    assert user.followers_count == 100
    assert user.friends_count == 50
    assert user.statuses_count == 200
    assert user.created_at == "2023-01-01"
    assert user.can_dm is True
    assert user.info == "Name: Test User\nUsername: testuser\nDescription: Test description"


@pytest.mark.asyncio
async def test_parse_retweeted_status_none():
    assert parse_retweeted_status(None) is None


@pytest.mark.asyncio
async def test_parse_retweeted_status(sample_user_data):
    data = {
        "created_at": "2023-01-01",
        "id_str": "456",
        "full_text": "Retweeted tweet",
        "user": sample_user_data,
        "retweet_count": 5,
        "favorite_count": 15
    }
    retweet = parse_retweeted_status(data)
    assert retweet.created_at == "2023-01-01"
    assert retweet.id_str == "456"
    assert retweet.full_text == "Retweeted tweet"
    assert retweet.user.id_str == "123"
    assert retweet.retweet_count == 5
    assert retweet.favorite_count == 15


@pytest.mark.asyncio
async def test_parse_quoted_status_none():
    assert parse_quoted_status(None) is None


@pytest.mark.asyncio
async def test_parse_quoted_status(sample_user_data):
    data = {
        "created_at": "2023-01-01",
        "id_str": "789",
        "full_text": "Quoted tweet",
        "user": sample_user_data,
        "retweet_count": 3,
        "favorite_count": 7
    }
    quote = parse_quoted_status(data)
    assert quote.created_at == "2023-01-01"
    assert quote.id_str == "789"
    assert quote.full_text == "Quoted tweet"
    assert quote.user.id_str == "123"
    assert quote.retweet_count == 3
    assert quote.favorite_count == 7


@pytest.mark.asyncio
async def test_parse_tweet(sample_tweet_data):
    tweet = parse_tweet(sample_tweet_data)
    assert tweet.created_at == "2023-01-01"
    assert tweet.id_str == "456"
    assert tweet.full_text == "Test tweet"
    assert tweet.user.id_str == "123"
    assert tweet.retweeted_status is None
    assert tweet.quoted_status is None
    assert tweet.retweet_count == 10
    assert tweet.favorite_count == 20
    assert tweet.is_quote_status is False
    assert tweet.conversation_id_str == "789"
    assert tweet.in_reply_to_status_id_str is None


@pytest.mark.asyncio
async def test_make_request_success(mock_settings, mocker):
    mocker.patch("tweetscout_utils.get_settings", return_value=mock_settings)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": "test"}
    mocker.patch("aiohttp.ClientSession.post", return_value=mock_response)

    result = await _make_request("https://api.tweetscout.io/v2/test", {"key": "value"})
    assert result == {"data": "test"}
    aiohttp.ClientSession.post.assert_called_once()


@pytest.mark.asyncio
async def test_make_request_client_error(mock_settings, mocker):
    mocker.patch("tweetscout_utils.get_settings", return_value=mock_settings)
    mocker.patch("aiohttp.ClientSession.post",
                 side_effect=aiohttp.ClientResponseError(status=400, request_info=None, history=None,
                                                         message="Bad Request"))

    with pytest.raises(aiohttp.ClientResponseError):
        await _make_request("https://api.tweetscout.io/v2/test", {"key": "value"})


@pytest.mark.asyncio
async def test_make_request_retry(mock_settings, mocker):
    mocker.patch("tweetscout_utils.get_settings", return_value=mock_settings)
    mocker.patch("aiohttp.ClientSession.post", side_effect=[aiohttp.ClientResponseError(status=429, request_info=None,
                                                                                        history=None,
                                                                                        message="Rate Limit")] * 2 + [
                                                               AsyncMock(status=200, json=AsyncMock(
                                                                   return_value={"data": "test"}))])

    result = await _make_request("https://api.tweetscout.io/v2/test", {"key": "value"})
    assert result == {"data": "test"}
    assert aiohttp.ClientSession.post.call_count == 3


@pytest.mark.asyncio
async def test_fetch_user_tweets(mock_settings, mocker, sample_tweet_data):
    mocker.patch("tweetscout_utils.get_settings", return_value=mock_settings)
    mocker.patch("tweetscout_utils._make_request", AsyncMock(return_value={"tweets": [sample_tweet_data]}))

    tweets = await fetch_user_tweets("testuser")
    assert len(tweets) == 1
    assert tweets[0].id_str == "456"
    tweetscout_utils._make_request.assert_called_once_with(
        "https://api.tweetscout.io/v2/user-tweets",
        {"link": "https://x.com/testuser"}
    )


@pytest.mark.asyncio
async def test_search_tweets(mock_settings, mocker, sample_tweet_data):
    mocker.patch("tweetscout_utils.get_settings", return_value=mock_settings)
    mocker.patch("tweetscout_utils._make_request", AsyncMock(return_value={"tweets": [sample_tweet_data]}))

    tweets = await search_tweets("query")
    assert len(tweets) == 1
    assert tweets[0].id_str == "456"
    tweetscout_utils._make_request.assert_called_once_with(
        "https://api.tweetscout.io/v2/search-tweets",
        {"query": "query"}
    )


@pytest.mark.asyncio
async def test_get_tweet_by_link(mock_settings, mocker, sample_tweet_data):
    mocker.patch("tweetscout_utils.get_settings", return_value=mock_settings)
    mocker.patch("tweetscout_utils._make_request", AsyncMock(return_value=sample_tweet_data))

    tweet = await get_tweet_by_link("https://twitter.com/apify/status/456")
    assert tweet.id_str == "456"
    tweetscout_utils._make_request.assert_called_once_with(
        "https://api.tweetscout.io/v2/tweet-info",
        {"tweet_link": "https://twitter.com/apify/status/456"}
    )


@pytest.mark.asyncio
async def test_get_conversation_from_tweet(mock_settings, mocker, sample_tweet_data):
    reply_tweet_data = sample_tweet_data.copy()
    reply_tweet_data["id_str"] = "789"
    reply_tweet_data["in_reply_to_status_id_str"] = None

    mocker.patch("tweetscout_utils.get_settings", return_value=mock_settings)
    mocker.patch("tweetscout_utils._make_request", AsyncMock(return_value=reply_tweet_data))

    tweet = parse_tweet({**sample_tweet_data, "in_reply_to_status_id_str": "789"})
    conversation = await get_conversation_from_tweet(tweet)

    assert len(conversation) == 2
    assert conversation[0].id_str == "789"
    assert conversation[1].id_str == "456"
    tweetscout_utils._make_request.assert_called_once_with(
        "https://api.tweetscout.io/v2/tweet-info",
        {"tweet_link": "https://twitter.com/apify/status/789"}
    )


@pytest.mark.asyncio
async def test_create_conversation_string(sample_tweet_data):
    tweet = parse_tweet(sample_tweet_data)
    conversation = [tweet]
    result = create_conversation_string(conversation)
    assert result == "testuser:\n    Test tweet"

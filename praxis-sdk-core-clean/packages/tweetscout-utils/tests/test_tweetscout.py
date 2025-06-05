import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from tweetscout_utils.main import (
    User, QuotedStatus, RetweetedStatus, Tweet,
    parse_user, parse_retweeted_status, parse_quoted_status, parse_tweet,
    _make_request, fetch_user_tweets, search_tweets, get_tweet_by_link,
    get_conversation_from_tweet, create_conversation_string
)


# Фикстуры
@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.TWEETSCOUT_API_KEY = "test_api_key"
    return settings


@pytest.fixture
def mock_aiohttp_session():
    session = AsyncMock()
    session.post = AsyncMock()
    return session


@pytest.fixture
async def mock_client_session(mock_aiohttp_session):
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        yield mock_aiohttp_session


# Тесты для классов данных
def test_user_dataclass():
    user = User(
        id_str="123",
        name="Test User",
        screen_name="testuser",
        description="Test description",
        followers_count=100,
        friends_count=50,
        statuses_count=200,
        created_at="2023-01-01",
        can_dm=True
    )
    assert user.id_str == "123"
    assert user.name == "Test User"
    assert user.info == "Name: Test User\nUsername: testuser\nDescription: Test description"


def test_quoted_status_dataclass():
    user = User(
        id_str="123", name="Test User", screen_name="testuser",
        description="Test", followers_count=100, friends_count=50,
        statuses_count=200, created_at="2023-01-01"
    )
    quoted_status = QuotedStatus(
        created_at="2023-01-01",
        id_str="456",
        full_text="Quoted tweet",
        user=user,
        retweet_count=10,
        favorite_count=20
    )
    assert quoted_status.id_str == "456"
    assert quoted_status.full_text == "Quoted tweet"
    assert quoted_status.user == user


def test_retweeted_status_dataclass():
    user = User(
        id_str="123", name="Test User", screen_name="testuser",
        description="Test", followers_count=100, friends_count=50,
        statuses_count=200, created_at="2023-01-01"
    )
    retweeted_status = RetweetedStatus(
        created_at="2023-01-01",
        id_str="789",
        full_text="Retweeted tweet",
        user=user,
        retweet_count=15,
        favorite_count=25
    )
    assert retweeted_status.id_str == "789"
    assert retweeted_status.full_text == "Retweeted tweet"
    assert retweeted_status.user == user


def test_tweet_dataclass():
    user = User(
        id_str="123", name="Test User", screen_name="testuser",
        description="Test", followers_count=100, friends_count=50,
        statuses_count=200, created_at="2023-01-01"
    )
    tweet = Tweet(
        created_at="2023-01-01",
        id_str="101",
        full_text="Test tweet",
        user=user,
        retweeted_status=None,
        quoted_status=None,
        retweet_count=5,
        favorite_count=10,
        is_quote_status=False,
        conversation_id_str="101",
        in_reply_to_status_id_str=None
    )
    assert tweet.id_str == "101"
    assert tweet.full_text == "Test tweet"
    assert tweet.user == user


# Тесты для функций парсинга
def test_parse_user():
    data = {
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
    user = parse_user(data)
    assert user.id_str == "123"
    assert user.name == "Test User"
    assert user.can_dm is True


def test_parse_user_no_can_dm():
    data = {
        "id_str": "123",
        "name": "Test User",
        "screen_name": "testuser",
        "description": "Test description",
        "followers_count": 100,
        "friends_count": 50,
        "statuses_count": 200,
        "created_at": "2023-01-01"
    }
    user = parse_user(data)
    assert user.can_dm is False


def test_parse_retweeted_status():
    data = {
        "created_at": "2023-01-01",
        "id_str": "789",
        "full_text": "Retweeted tweet",
        "user": {
            "id_str": "123",
            "name": "Test User",
            "screen_name": "testuser",
            "description": "Test",
            "followers_count": 100,
            "friends_count": 50,
            "statuses_count": 200,
            "created_at": "2023-01-01"
        },
        "retweet_count": 15,
        "favorite_count": 25
    }
    retweeted_status = parse_retweeted_status(data)
    assert retweeted_status.id_str == "789"
    assert retweeted_status.user.screen_name == "testuser"


def test_parse_retweeted_status_none():
    assert parse_retweeted_status(None) is None


def test_parse_quoted_status():
    data = {
        "created_at": "2023-01-01",
        "id_str": "456",
        "full_text": "Quoted tweet",
        "user": {
            "id_str": "123",
            "name": "Test User",
            "screen_name": "testuser",
            "description": "Test",
            "followers_count": 100,
            "friends_count": 50,
            "statuses_count": 200,
            "created_at": "2023-01-01"
        },
        "retweet_count": 10,
        "favorite_count": 20
    }
    quoted_status = parse_quoted_status(data)
    assert quoted_status.id_str == "456"
    assert quoted_status.user.screen_name == "testuser"


def test_parse_quoted_status_none():
    assert parse_quoted_status(None) is None


def test_parse_tweet():
    data = {
        "created_at": "2023-01-01",
        "id_str": "101",
        "full_text": "Test tweet",
        "user": {
            "id_str": "123",
            "name": "Test User",
            "screen_name": "testuser",
            "description": "Test",
            "followers_count": 100,
            "friends_count": 50,
            "statuses_count": 200,
            "created_at": "2023-01-01"
        },
        "retweeted_status": None,
        "quoted_status": None,
        "retweet_count": 5,
        "favorite_count": 10,
        "is_quote_status": False,
        "conversation_id_str": "101",
        "in_reply_to_status_id_str": None
    }
    tweet = parse_tweet(data)
    assert tweet.id_str == "101"
    assert tweet.full_text == "Test tweet"
    assert tweet.retweeted_status is None
    assert tweet.quoted_status is None


# Тесты для асинхронных функций
@pytest.mark.asyncio
async def test_make_request_success(mock_client_session, mock_settings):
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"tweets": []})
    mock_client_session.post.return_value.__aenter__.return_value = response

    result = await _make_request("https://api.tweetscout.io/v2/test", {"key": "value"})
    assert result == {"tweets": []}
    mock_client_session.post.assert_called_with(
        "https://api.tweetscout.io/v2/test",
        headers={"ApiKey": "test_api_key"},
        json={"key": "value"}
    )


@pytest.mark.asyncio
async def test_make_request_client_error(mock_client_session, mock_settings):
    response = AsyncMock()
    response.status = 400
    response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        status=400, request_info=MagicMock(), history=()
    )
    mock_client_session.post.return_value.__aenter__.return_value = response

    with pytest.raises(aiohttp.ClientResponseError):
        await _make_request("https://api.tweetscout.io/v2/test", {"key": "value"})


@pytest.mark.asyncio
async def test_fetch_user_tweets(mock_client_session, mock_settings):
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={
        "tweets": [{
            "created_at": "2023-01-01",
            "id_str": "101",
            "full_text": "Test tweet",
            "user": {
                "id_str": "123",
                "name": "Test User",
                "screen_name": "testuser",
                "description": "Test",
                "followers_count": 100,
                "friends_count": 50,
                "statuses_count": 200,
                "created_at": "2023-01-01"
            },
            "retweet_count": 5,
            "favorite_count": 10,
            "is_quote_status": False,
            "conversation_id_str": "101",
            "in_reply_to_status_id_str": None
        }]
    })
    mock_client_session.post.return_value.__aenter__.return_value = response

    tweets = await fetch_user_tweets("testuser")
    assert len(tweets) == 1
    assert tweets[0].id_str == "101"
    mock_client_session.post.assert_called_with(
        "https://api.tweetscout.io/v2/user-tweets",
        headers={"ApiKey": "test_api_key"},
        json={"link": "https://x.com/testuser"}
    )


@pytest.mark.asyncio
async def test_search_tweets(mock_client_session, mock_settings):
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={
        "tweets": [{
            "created_at": "2023-01-01",
            "id_str": "101",
            "full_text": "Test tweet",
            "user": {
                "id_str": "123",
                "name": "Test User",
                "screen_name": "testuser",
                "description": "Test",
                "followers_count": 100,
                "friends_count": 50,
                "statuses_count": 200,
                "created_at": "2023-01-01"
            },
            "retweet_count": 5,
            "favorite_count": 10,
            "is_quote_status": False,
            "conversation_id_str": "101",
            "in_reply_to_status_id_str": None
        }]
    })
    mock_client_session.post.return_value.__aenter__.return_value = response

    tweets = await search_tweets("test query")
    assert len(tweets) == 1
    assert tweets[0].id_str == "101"
    mock_client_session.post.assert_called_with(
        "https://api.tweetscout.io/v2/search-tweets",
        headers={"ApiKey": "test_api_key"},
        json={"query": "test query"}
    )


@pytest.mark.asyncio
async def test_get_tweet_by_link(mock_client_session, mock_settings):
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={
        "created_at": "2023-01-01",
        "id_str": "101",
        "full_text": "Test tweet",
        "user": {
            "id_str": "123",
            "name": "Test User",
            "screen_name": "testuser",
            "description": "Test",
            "followers_count": 100,
            "friends_count": 50,
            "statuses_count": 200,
            "created_at": "2023-01-01"
        },
        "retweet_count": 5,
        "favorite_count": 10,
        "is_quote_status": False,
        "conversation_id_str": "101",
        "in_reply_to_status_id_str": None
    })
    mock_client_session.post.return_value.__aenter__.return_value = response

    tweet = await get_tweet_by_link("https://twitter.com/testuser/status/101")
    assert tweet.id_str == "101"
    mock_client_session.post.assert_called_with(
        "https://api.tweetscout.io/v2/tweet-info",
        headers={"ApiKey": "test_api_key"},
        json={"tweet_link": "https://twitter.com/testuser/status/101"}
    )


@pytest.mark.asyncio
async def test_get_conversation_from_tweet(mock_client_session, mock_settings):
    tweet = Tweet(
        created_at="2023-01-01",
        id_str="101",
        full_text="Reply tweet",
        user=User(
            id_str="123", name="Test User", screen_name="testuser",
            description="Test", followers_count=100, friends_count=50,
            statuses_count=200, created_at="2023-01-01"
        ),
        retweeted_status=None,
        quoted_status=None,
        retweet_count=5,
        favorite_count=10,
        is_quote_status=False,
        conversation_id_str="100",
        in_reply_to_status_id_str="100"
    )
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={
        "created_at": "2023-01-01",
        "id_str": "100",
        "full_text": "Original tweet",
        "user": {
            "id_str": "123",
            "name": "Test User",
            "screen_name": "testuser",
            "description": "Test",
            "followers_count": 100,
            "friends_count": 50,
            "statuses_count": 200,
            "created_at": "2023-01-01"
        },
        "retweet_count": 5,
        "favorite_count": 10,
        "is_quote_status": False,
        "conversation_id_str": "100",
        "in_reply_to_status_id_str": None
    })
    mock_client_session.post.return_value.__aenter__.return_value = response

    conversation = await get_conversation_from_tweet(tweet)
    assert len(conversation) == 2
    assert conversation[0].id_str == "100"
    assert conversation[1].id_str == "101"


def test_create_conversation_string():
    user = User(
        id_str="123", name="Test User", screen_name="testuser",
        description="Test", followers_count=100, friends_count=50,
        statuses_count=200, created_at="2023-01-01"
    )
    tweets = [
        Tweet(
            created_at="2023-01-01",
            id_str="100",
            full_text="Original tweet",
            user=user,
            retweeted_status=None,
            quoted_status=None,
            retweet_count=5,
            favorite_count=10,
            is_quote_status=False,
            conversation_id_str="100",
            in_reply_to_status_id_str=None
        ),
        Tweet(
            created_at="2023-01-01",
            id_str="101",
            full_text="Reply tweet",
            user=user,
            retweeted_status=None,
            quoted_status=None,
            retweet_count=5,
            favorite_count=10,
            is_quote_status=False,
            conversation_id_str="100",
            in_reply_to_status_id_str="100"
        )
    ]
    result = create_conversation_string(tweets)
    expected = "testuser:\n    Original tweet\ntestuser:\n    Reply tweet"
    assert result == expected

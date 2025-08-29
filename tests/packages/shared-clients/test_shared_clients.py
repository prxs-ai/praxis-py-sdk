import pytest
import aiohttp
from aioresponses import aioresponses
from msgspec import json
from typing import Any
from shared_clients.aiohttp_.api import AiohttpAPI
from shared_clients.aiohttp_.session import AiohttpSession, ResponseWrapper, APIError
from shared_clients.tweetscout.api import TweetScoutAPI
from shared_clients.tweetscout.session import TweetScoutSession
from shared_clients.tweetscout.dto import (
    TypesAccount, HandlerSearchTweetsReq, HandlerSearchTweetsRes, HandlerLookupRes,
    HandlerListTweetsRes, HandlerTweetInfoReq, HandlerTweetInfoResp, HandlerUserTweetsReq,
    HandlerUserTweetsRes, HandlerIDRes, HandlerHandleRes, HandlerHandleHistoriesResp,
    HandlerFollowersStatsResp, HandlerScoreChangesResp, HandlerScoreResp, TypesFollower, HandlerListMember
)
from shared_clients.tweetscout.query import (
    QueryBuilder, Word, Phrase, Hashtag, FromUser, And, Negate, MinRetweets, build_query, Sequence, QueryNode
)
from shared_clients.exceptions import APIError as ExceptionsAPIError


# Тесты для shared_clients.aiohttp_.api
@pytest.mark.asyncio
async def test_aiohttp_api_context_manager():
    async with aiohttp.ClientSession() as session:
        api = AiohttpAPI(AiohttpSession(session_provider=lambda: session))
        async with api as api_ctx:
            assert api_ctx._session == api._session
        assert api._session._session.closed


@pytest.mark.asyncio
async def test_aiohttp_api_aexit_handles_exceptions():
    async with aiohttp.ClientSession() as session:
        api = AiohttpAPI(AiohttpSession(session_provider=lambda: session))
        async with api:
            pass  # Simulate normal exit
        assert api._session._session.closed


# Тесты для shared_clients.aiohttp_.session
@pytest.mark.asyncio
async def test_aiohttp_session_request():
    with aioresponses() as m:
        m.get("http://example.com/test", status=200, payload={"data": "test"})
        session = AiohttpSession(base_url="http://example.com/")
        async with session.get("/test") as resp:
            assert resp.status == 200
            assert await resp.json() == {"data": "test"}


@pytest.mark.asyncio
async def test_response_wrapper_error():
    with aioresponses() as m:
        m.get("http://example.com/test", status=400, body="Bad Request")
        session = AiohttpSession(base_url="http://example.com/")
        with pytest.raises(APIError) as exc_info:
            async with session.get("/test") as resp:
                pass
        assert exc_info.value.status == 400


@pytest.mark.asyncio
async def test_aiohttp_session_all_methods():
    methods = ["get", "post", "put", "delete", "patch", "head", "options", "trace", "connect"]
    session = AiohttpSession(base_url="http://example.com/")
    with aioresponses() as m:
        for method in methods:
            m.add(method.upper(), "http://example.com/test", status=200)
            wrapper = getattr(session, method)("test")
            async with wrapper as resp:
                assert resp.status == 200


@pytest.mark.asyncio
async def test_aiohttp_session_context_manager():
    session = AiohttpSession()
    async with session:
        assert isinstance(session._session, aiohttp.ClientSession)
    assert session._session.closed


@pytest.mark.asyncio
async def test_aiohttp_session_base_url():
    session = AiohttpSession(base_url="http://example.com")
    with aioresponses() as m:
        m.get("http://example.com/api/test", status=200, payload={"data": "test"})
        async with session.get("/api/test") as resp:
            assert resp.status == 200


# Тесты для shared_clients.tweetscout.api
@pytest.mark.asyncio
async def test_tweetscout_api_follows_by_link():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/follows?link=test_link",
            status=200,
            payload=[{"id": "123", "screen_name": "test_user"}]
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.follows(link="test_link")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], HandlerLookupRes)
        assert result[0].id == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_follows_by_user_id():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/follows?user_id=123",
            status=200,
            payload=[{"id": "123", "screen_name": "test_user"}]
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.follows(user_id="123")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], HandlerLookupRes)
        assert result[0].id == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_info():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/info/test_user",
            status=200,
            payload={"id": "123", "screen_name": "test_user"}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.info("test_user")
        assert isinstance(result, HandlerLookupRes)
        assert result.screen_name == "test_user"


@pytest.mark.asyncio
async def test_tweetscout_api_info_id():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/info-id/123",
            status=200,
            payload={"id": "123", "screen_name": "test_user"}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.info_id("123")
        assert isinstance(result, HandlerLookupRes)
        assert result.id == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_list_members():
    with aioresponses() as m:
        m.get("https://api.tweetscout.io/v2/list-tweets?list_id=456")
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.list_members("456")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], HandlerListMember)
        assert result[0].id == "123"


@pytest.mark.asyncio
async def test_tweetscouts_api_list_tweets():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/list-tweets?list_id=456",
            status=200,
            payload={"tweets": [{"id_str": "123", "full_text": "test tweet"}]}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.list_tweets("456")
        assert isinstance(result, HandlerListTweetsRes)
        assert len(result.tweets) == 1
        assert result.tweets[0].id_str == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_search_tweets():
    with aioresponses() as m:
        m.post(
            "https://api.tweetscout.io/v2/search-tweets",
            status=200,
            payload={"tweets": [{"id_str": "123", "full_text": "test tweet"}]}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        payload = HandlerSearchTweetsReq(query="test")
        result = await api.search_tweets(payload)
        assert isinstance(result, HandlerSearchTweetsRes)
        assert len(result.tweets) == 1
        assert result.tweets[0].id_str == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_tweet_info():
    with aioresponses() as m:
        m.post(
            "https://api.tweetscout.io/v2/tweet-info",
            status=200,
            payload={"id_str": "123", "full_text": "test tweet"}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        payload = HandlerTweetInfoReq(tweet_link="https://twitter.com/test/123")
        result = await api.tweet_info(payload)
        assert isinstance(result, HandlerTweetInfoResp)
        assert result.id_str == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_user_tweets():
    with aioresponses() as m:
        m.post(
            "https://api.tweetscout.io/v2/user-tweets",
            status=200,
            payload={"tweets": [{"id_str": "123", "full_text": "test tweet"}]}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        payload = HandlerUserTweetsReq(user_id="123")
        result = await api.user_tweets(payload)
        assert isinstance(result, HandlerUserTweetsRes)
        assert len(result.tweets) == 1
        assert result.tweets[0].id_str == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_handle_to_id():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/handle-to-id/test_user",
            status=200,
            payload={"id": "123"}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.handle_to_id("test_user")
        assert isinstance(result, HandlerIDRes)
        assert result.id == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_id_to_handle():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/id-to-handle/123",
            status=200,
            payload={"handle": "test_user"}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.id_to_handle("123")
        assert isinstance(result, HandlerHandleRes)
        assert result.handle == "test_user"


@pytest.mark.asyncio
async def test_tweetscout_api_handle_history():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/handle-history?user_id=123",
            status=200,
            payload={"handles": [{"handle": "test_user", "date": "2023-01-01"}]}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.handle_history(user_id="123")
        assert isinstance(result, HandlerHandleHistoriesResp)
        assert len(result.handles) == 1
        assert result.handles[0].handle == "test_user"


@pytest.mark.asyncio
async def test_tweetscout_api_followers_stats():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/followers-stats?user_id=123",
            status=200,
            payload={"followers_count": 100, "influencers_count": 10}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.followers_stats(user_id="123")
        assert isinstance(result, HandlerFollowersStatsResp)
        assert result.followers_count == 100


@pytest.mark.asyncio
async def test_tweetscout_api_new_following_7d():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/new-following-7d?user_id=123",
            status=200,
            payload=[{"id": "123", "screen_name": "test_user"}]
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.new_following_7d(user_id="123")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TypesFollower)
        assert result[0].id == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_score_changes():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/score-changes?user_id=123",
            status=200,
            payload={"week_delta": 0.5, "month_delta": 1.0}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.score_changes(user_id="123")
        assert isinstance(result, HandlerScoreChangesResp)
        assert result.week_delta == 0.5


@pytest.mark.asyncio
async def test_tweetscout_api_score():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/score/test_user",
            status=200,
            payload={"score": 0.9}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.score("test_user")
        assert isinstance(result, HandlerScoreResp)
        assert result.score == 0.9


@pytest.mark.asyncio
async def test_tweetscout_api_top_followers():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/top-followers/test_user",
            status=200,
            payload=[{"id": "123", "screen_name": "test_user"}]
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.top_followers("test_user")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TypesAccount)
        assert result[0].id == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_top_following():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/top-following/test_user",
            status=200,
            payload=[{"id": "123", "screen_name": "test_user"}]
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.top_following("test_user")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TypesAccount)
        assert result[0].id == "123"


# Тесты для shared_clients.tweetscout.dto
def test_dto_serialization():
    account = TypesAccount(id="123", screen_name="test_user", followers_count=100)
    result = account.to_dict()
    assert result == {"id": "123", "screen_name": "test_user", "followers_count": 100}

    account = TypesAccount(id="123", screen_name=None)
    result = account.to_dict(exclude_none=True)
    assert result == {"id": "123"}


def test_dto_deserialization():
    data = b'{"id": "123", "screen_name": "test_user"}'
    result = json.decode(data, type=TypesAccount)
    assert isinstance(result, TypesAccount)
    assert result.id == "123"
    assert result.screen_name == "test_user"


# Тесты для shared_clients.tweetscout.query
def test_query_builder_word():
    node = Word(value="test")
    assert QueryBuilder().walk(node) == "test"


def test_query_builder_phrase():
    node = Phrase(value="hello world")
    assert QueryBuilder().walk(node) == '"hello world"'


def test_query_builder_hashtag():
    node = Hashtag(value=Word(value="test"))
    assert QueryBuilder().walk(node) == "#test"


def test_query_builder_from_user():
    node = FromUser(from_user=Word(value="test_user"))
    assert QueryBuilder().walk(node) == "from:test_user"


def test_query_builder_and():
    node = And(left=Word(value="hello"), right=Word(value="world"))
    assert QueryBuilder().walk(node) == "(hello) AND (world)"


def test_query_builder_negate():
    node = Negate(operand=Word(value="bad"))
    assert QueryBuilder().walk(node) == "-(bad)"


def test_query_builder_min_retweets():
    node = MinRetweets(value=100)
    assert QueryBuilder().walk(node) == "min_retweets:100"


def test_query_builder_complex():
    node = And(
        left=Negate(operand=Word(value="bad")),
        right=Hashtag(value=Word(value="good"))
    )
    assert QueryBuilder().walk(node) == "(-(bad)) AND (#good)"


def test_build_query():
    node = Word(value="test")
    assert build_query(node) == "test"


# Тесты для shared_clients.tweetscout.session
@pytest.mark.asyncio
async def test_tweetscout_session_api_key():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/test",
            status=200,
            payload={"data": "test"}
        )
        session = TweetScoutSession(api_key="test_key")
        async with session.get("test") as resp:
            assert resp.status == 200
            assert resp.request_info.headers["ApiKey"] == "test_key"


def test_exceptions_api_error():
    error = ExceptionsAPIError(status=500, message="Server Error", detail="Internal")
    assert error.status == 500
    assert error.message == "Server Error"
    assert error.kwargs == {"detail": "Internal"}
    assert repr(error) == "\tStatus Code: 500\n\tMessage: Server Error\n\n{'detail': 'Internal'}"


def test_exceptions_api_error_no_kwargs():
    error = ExceptionsAPIError(status=503, message="Service Unavailable")
    assert error.status == 503
    assert error.message == "Service Unavailable"
    assert error.kwargs == {}
    assert repr(error) == "\tStatus Code: 503\n\tMessage: Service Unavailable\n\n{}"


# Дополнительные тесты для shared_clients.aiohttp_.api
@pytest.mark.asyncio
async def test_aiohttp_api_aexit_with_exception():
    async with aiohttp.ClientSession() as session:
        api = AiohttpAPI(AiohttpSession(session_provider=lambda: session))
        with pytest.raises(Exception):
            async with api:
                raise Exception("Test exception")
        assert api._session._session.closed


# Дополнительные тесты для shared_clients.aiohttp_.session
@pytest.mark.asyncio
async def test_aiohttp_session_create_session_reuse():
    session = AiohttpSession()
    async with session:
        first_session = session._session
        assert isinstance(first_session, aiohttp.ClientSession)
    async with session:
        second_session = session._session
        assert first_session is not second_session  # Проверяем, что сессия пересоздается, если закрыта


@pytest.mark.asyncio
async def test_aiohttp_session_full_url():
    session = AiohttpSession(base_url="http://example.com")
    with aioresponses() as m:
        m.get("https://external.com/test", status=200, payload={"data": "test"})
        async with session.get("https://external.com/test") as resp:
            assert resp.status == 200
            assert await resp.json() == {"data": "test"}


# Дополнительные тесты для shared_clients.tweetscout.api
@pytest.mark.asyncio
async def test_tweetscout_api_follows_no_params():
    session = TweetScoutSession(api_key="test_key")
    api = TweetScoutAPI(session)
    with pytest.raises(TypeError):
        await api.follows()  # Проверяем, что метод требует link или user_id


@pytest.mark.asyncio
async def test_tweetscout_api_handle_history_by_link():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/handle-history?link=test_link",
            status=200,
            payload={"handles": [{"handle": "test_user", "date": "2023-01-01"}]}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.handle_history(link="test_link")
        assert isinstance(result, HandlerHandleHistoriesResp)
        assert len(result.handles) == 1
        assert result.handles[0].handle == "test_user"


@pytest.mark.asyncio
async def test_tweetscout_api_followers_stats_by_handle():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/followers-stats?user_handle=test_user",
            status=200,
            payload={"followers_count": 200, "influencers_count": 20}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.followers_stats(user_handle="test_user")
        assert isinstance(result, HandlerFollowersStatsResp)
        assert result.followers_count == 200


@pytest.mark.asyncio
async def test_tweetscout_api_new_following_7d_by_handle():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/new-following-7d?user_handle=test_user",
            status=200,
            payload=[{"id": "123", "screen_name": "test_user"}]
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.new_following_7d(user_handle="test_user")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TypesFollower)
        assert result[0].id == "123"


@pytest.mark.asyncio
async def test_tweetscout_api_score_changes_by_handle():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/score-changes?user_handle=test_user",
            status=200,
            payload={"week_delta": 0.7, "month_delta": 1.2}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.score_changes(user_handle="test_user")
        assert isinstance(result, HandlerScoreChangesResp)
        assert result.week_delta == 0.7


@pytest.mark.asyncio
async def test_tweetscout_api_score_id():
    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/score-id/123",
            status=200,
            payload={"score": 0.8}
        )
        session = TweetScoutSession(api_key="test_key")
        api = TweetScoutAPI(session)
        result = await api.score_id("123")
        assert isinstance(result, HandlerScoreResp)
        assert result.score == 0.8


# Дополнительные тесты для shared_clients.tweetscout.dto
def test_dto_serialization_with_none():
    account = TypesAccount(id="123", screen_name=None, followers_count=None)
    result = account.to_dict(exclude_none=False)
    assert result == {"id": "123", "screen_name": None, "followers_count": None, "avatar": None,
                      "banner": None, "canDM": None, "description": None, "friendsCount": None,
                      "name": None, "protected": None, "registerDate": None, "score": None,
                      "screeName": None, "statuses_count": None, "verified": None}


def test_dto_follower_deserialization():
    data = b'{"id": "123", "screen_name": "test_user", "followerDate": "2023-01-01"}'
    result = json.decode(data, type=TypesFollower)
    assert isinstance(result, TypesFollower)
    assert result.id == "123"
    assert result.screen_name == "test_user"
    assert result.followerDate == "2023-01-01"


# Дополнительные тесты для shared_clients.tweetscout.query
def test_query_builder_sequence():
    node = Sequence(operands=[Word(value="hello"), Hashtag(value=Word(value="world"))])
    assert QueryBuilder().walk(node) == "hello #world"


def test_query_builder_missing_node():
    class UnknownNode(QueryNode):
        pass

    node = UnknownNode()
    with pytest.raises(RuntimeError, match="No implementation found for node"):
        QueryBuilder().walk(node)


# Дополнительные тесты для shared_clients.tweetscout.session
@pytest.mark.asyncio
async def test_tweetscout_session_no_api_key():
    with pytest.raises(TypeError):
        TweetScoutSession()  # Проверяем, что api_key обязателен


@pytest.mark.asyncio
async def test_tweetscout_session_custom_session_provider():
    def custom_provider():
        return aiohttp.ClientSession(headers={"Custom-Provider": "test"})

    with aioresponses() as m:
        m.get(
            "https://api.tweetscout.io/v2/test",
            status=200,
            payload={"data": "test"}
        )
        session = TweetScoutSession(api_key="test_key", session_provider=custom_provider)
        async with session.get("test") as resp:
            assert resp.status == 200
            assert resp.request_info.headers["Custom-Provider"] == "test"
            assert resp.request_info.headers["ApiKey"] == "test_key"

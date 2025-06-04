import asyncio
import json
import time
from datetime import datetime
from typing import Set
from unittest.mock import AsyncMock, Mock, patch

import pytest
import redis
from redis_client.client import (
    Post,
    PromptManager,
    RedisDB,
    decode_redis,
    ensure_delay_between_posts,
)


@pytest.fixture
def mock_redis():
    mock = Mock(spec=redis.Redis)
    mock.pubsub.return_value = Mock()
    return mock


@pytest.fixture
def redis_db(mock_redis, mocker):
    mocker.patch(
        "redis_client.client.get_settings",
        return_value=Mock(REDIS_HOST="localhost", REDIS_PORT=6379, REDIS_DB=0),
    )
    mocker.patch("redis.Redis", return_value=mock_redis)
    mocker.patch.object(RedisDB, "wait_for_redis", return_value=True)
    return RedisDB()


@pytest.fixture
def prompt_manager(redis_db, mocker):
    mocker.patch("threading.Thread.start")
    return PromptManager(redis_db)


@pytest.mark.asyncio
async def test_redis_init_success(redis_db, mocker):
    mocker.patch.object(RedisDB, "wait_for_redis", return_value=True)
    assert redis_db.r is not None
    redis_db.r.set.assert_called_with("__temp_test_key__", "value")
    redis_db.r.delete.assert_called_with("__temp_test_key__")


@pytest.mark.asyncio
async def test_redis_init_failure(redis_db, mocker):
    mocker.patch.object(RedisDB, "wait_for_redis", return_value=False)
    with pytest.raises(ConnectionError, match="Failed to connect to Redis."):
        RedisDB()


@pytest.mark.asyncio
async def test_add_to_set(redis_db):
    redis_db.add_to_set("test_set", "value1")
    redis_db.r.sadd.assert_called_once_with("test_set", "value1")


@pytest.mark.asyncio
async def test_get_set(redis_db, mocker):
    redis_db.r.smembers.return_value = [b"value1", b"value2"]
    result = redis_db.get_set("test_set")
    assert result == ["value1", "value2"]
    redis_db.r.smembers.assert_called_once_with("test_set")


@pytest.mark.asyncio
async def test_get(redis_db, mocker):
    redis_db.r.get.return_value = json.dumps({"key": "value"}).encode()
    result = redis_db.get("test_key")
    assert result == {"key": "value"}
    redis_db.r.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_get_default(redis_db, mocker):
    redis_db.r.get.return_value = None
    result = redis_db.get("test_key", default="default_value")
    assert result == "default_value"


@pytest.mark.asyncio
async def test_set(redis_db, mocker):
    redis_db.set("test_key", {"key": "value"})
    redis_db.r.set.assert_called_once_with(
        "test_key", json.dumps({"key": "value"}), keepttl=False
    )


@pytest.mark.asyncio
async def test_setex(redis_db, mocker):
    redis_db.setex("test_key", {"key": "value"}, 60)
    redis_db.r.setex.assert_called_once_with(
        "test_key", 60, json.dumps({"key": "value"})
    )


@pytest.mark.asyncio
async def test_set_default(redis_db, mocker):
    mocker.patch.object(redis_db, "get", return_value=None)
    redis_db.set_default("test_key", "default_value")
    redis_db.set.assert_called_once_with("test_key", "default_value")


@pytest.mark.asyncio
async def test_delete(redis_db):
    redis_db.delete("test_key")
    redis_db.r.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_get_keys_by_pattern(redis_db, mocker):
    redis_db.r.scan_iter.return_value = [b"key1", b"key2"]
    result = redis_db.get_keys_by_pattern("key*")
    assert result == ["key1", "key2"]
    redis_db.r.scan_iter.assert_called_once_with("key*")


@pytest.mark.asyncio
async def test_get_keys_by_pattern_blocking(redis_db, mocker):
    redis_db.r.keys.return_value = [b"key1", b"key2"]
    result = redis_db.get_keys_by_pattern_blocking("key*")
    assert result == ["key1", "key2"]
    redis_db.r.keys.assert_called_once_with("key*")


@pytest.mark.asyncio
async def test_parse_list(redis_db, mocker):
    mocker.patch.object(redis_db, "get", return_value="value1,value2")
    result = redis_db.parse_list("test_key")
    assert result == ["value1", "value2"]


@pytest.mark.asyncio
async def test_get_twitter_data_keys(redis_db, mocker):
    redis_db.r.scan_iter.return_value = [b"twitter_data:user1", b"twitter_data:user2"]
    result = redis_db.get_twitter_data_keys()
    assert result == ["twitter_data:user1", "twitter_data:user2"]


@pytest.mark.asyncio
async def test_add_user_post(redis_db, mocker):
    post = Post(id="1", text="test", sender_username="user1", timestamp=1234567890)
    redis_db.add_user_post("user1", post)
    redis_db.r.zadd.assert_called_once_with(
        "posted_tweets:user1", {json.dumps(asdict(post)): 1234567890}
    )


@pytest.mark.asyncio
async def test_get_user_posts(redis_db, mocker):
    post = Post(id="1", text="test", sender_username="user1", timestamp=1234567890)
    redis_db.r.zrange.return_value = [json.dumps(asdict(post)).encode()]
    result = redis_db.get_user_posts("user1")
    assert len(result) == 1
    assert result[0].id == "1"
    redis_db.r.zrange.assert_called_once_with("posted_tweets:user1", 0, -1)


@pytest.mark.asyncio
async def test_get_user_posts_by_create_time(redis_db, mocker):
    post = Post(id="1", text="test", sender_username="user1", timestamp=1234567890)
    redis_db.r.zrangebyscore.return_value = [json.dumps(asdict(post)).encode()]
    mocker.patch("time.time", return_value=1234567890 + 3600)
    result = redis_db.get_user_posts_by_create_time("user1", 7200)
    assert len(result) == 1
    assert result[0].id == "1"
    redis_db.r.zrangebyscore.assert_called_once()


@pytest.mark.asyncio
async def test_add_send_partnership(redis_db):
    redis_db.add_send_partnership("user1", "partner1")
    redis_db.r.zadd.assert_called_once_with(
        "send_partnership:user1", {"partner1": int(time.time())}
    )


@pytest.mark.asyncio
async def test_get_send_partnership(redis_db, mocker):
    redis_db.r.zrange.return_value = [b"partner1", b"partner2"]
    result = redis_db.get_send_partnership("user1")
    assert result == ["partner1", "partner2"]
    redis_db.r.zrange.assert_called_once_with("send_partnership:user1", 0, -1)


@pytest.mark.asyncio
async def test_get_active_twitter_accounts(redis_db, mocker):
    redis_db.r.scan_iter.return_value = [b"twitter_data:user1", b"twitter_data:user2"]
    result = redis_db.get_active_twitter_accounts()
    assert result == ["user1", "user2"]


@pytest.mark.asyncio
async def test_get_account_last_action_time(redis_db, mocker):
    redis_db.r.get.return_value = json.dumps(1234567890).encode()
    result = redis_db.get_account_last_action_time("user1", "last_action")
    assert result == 1234567890.0


@pytest.mark.asyncio
async def test_update_account_last_action_time(redis_db, mocker):
    redis_db.update_account_last_action_time("user1", "last_action", 1234567890)
    redis_db.set.assert_called_once_with("last_action:user1", 1234567890)


@pytest.mark.asyncio
async def test_is_account_active(redis_db, mocker):
    redis_db.r.exists.return_value = True
    result = redis_db.is_account_active("user1")
    assert result is True
    redis_db.r.exists.assert_called_once_with("twitter_data:user1")


@pytest.mark.asyncio
async def test_remove_account(redis_db):
    redis_db.remove_account("user1")
    assert redis_db.r.delete.call_count == 8
    redis_db.r.delete.assert_any_call("twitter_data:user1")
    redis_db.r.delete.assert_any_call("posted_tweets:user1")


@pytest.mark.asyncio
async def test_get_function_variables(redis_db, mocker):
    mocker.patch(
        "redis_client.client.FUNCTION_VARIABLES", {"test_func": {"var1", "var2"}}
    )
    result = redis_db.get_function_variables()
    assert result == {"test_func": ["var1", "var2"]}
    redis_db.set.assert_called_once_with(
        "function_variables", {"test_func": ["var1", "var2"]}
    )


@pytest.mark.asyncio
async def test_save_tweet_link(redis_db):
    redis_db.save_tweet_link("test_func", "12345")
    redis_db.r.rpush.assert_called_once_with(
        "created_tweet:test_func", "https://twitter.com/i/web/status/12345"
    )


@pytest.mark.asyncio
async def test_prompt_manager_init(prompt_manager, mocker):
    assert prompt_manager.redis is not None
    assert prompt_manager._subscriber_thread is not None
    assert prompt_manager._initialized is True


@pytest.mark.asyncio
async def test_get_prompt_from_cache(prompt_manager, mocker):
    prompt_manager.prompt_cache["prompt:test_func"] = "cached prompt"
    result = prompt_manager.get_prompt("test_func")
    assert result == "cached prompt"


@pytest.mark.asyncio
async def test_get_prompt_from_redis(prompt_manager, mocker):
    mocker.patch.object(prompt_manager.redis, "get", return_value="redis prompt")
    result = prompt_manager.get_prompt("test_func")
    assert result == "redis prompt"
    assert prompt_manager.prompt_cache["prompt:test_func"] == "redis prompt"


@pytest.mark.asyncio
async def test_get_prompt_default(prompt_manager, mocker):
    mocker.patch.object(prompt_manager.redis, "get", return_value=None)
    mocker.patch(
        "redis_client.client.DEFAULT_PROMPTS", {"test_func": "default prompt {var1}"}
    )
    mocker.patch("redis_client.client.FUNCTION_VARIABLES", {"test_func": {"var1"}})
    result = prompt_manager.get_prompt("test_func")
    assert result == "default prompt {var1}"
    prompt_manager.redis.set.assert_called_once_with(
        "prompt:test_func", "default prompt {var1}"
    )


@pytest.mark.asyncio
async def test_get_prompt_invalid_vars(prompt_manager, mocker):
    mocker.patch.object(
        prompt_manager.redis, "get", return_value="prompt {invalid_var}"
    )
    mocker.patch("redis_client.client.FUNCTION_VARIABLES", {"test_func": {"var1"}})
    with pytest.raises(ValueError, match="недопустимые переменные: {'invalid_var'}"):
        prompt_manager.get_prompt("test_func")


@pytest.mark.asyncio
async def test_extract_fstring_vars(prompt_manager):
    template = "test {var1} and {var2:.2f} and {var3}"
    result = prompt_manager._extract_fstring_vars(template)
    assert result == {"var1", "var2", "var3"}


@pytest.mark.asyncio
async def test_use_dynamic_prompt_success(mocker):
    redis_db = Mock(spec=RedisDB)
    prompt_manager = PromptManager(redis_db)
    mocker.patch.object(
        prompt_manager, "get_prompt", return_value="test {twitter_post}"
    )
    mocker.patch(
        "redis_client.client.FUNCTION_VARIABLES",
        {"create_comment_to_post": {"twitter_post"}},
    )

    @use_dynamic_prompt("create_comment_to_post")
    async def dummy_func(twitter_post, prompt=None):
        return prompt

    result = await dummy_func(twitter_post="test tweet")
    assert result == "test test tweet"


@pytest.mark.asyncio
async def test_use_dynamic_prompt_invalid_vars(mocker):
    redis_db = Mock(spec=RedisDB)
    prompt_manager = PromptManager(redis_db)
    mocker.patch.object(prompt_manager, "get_prompt", return_value="test {invalid_var}")
    mocker.patch(
        "redis_client.client.FUNCTION_VARIABLES",
        {"create_comment_to_post": {"twitter_post"}},
    )

    @use_dynamic_prompt("create_comment_to_post")
    async def dummy_func(twitter_post):
        pass

    with pytest.raises(ValueError, match="недопустимые переменные: {'invalid_var'}"):
        await dummy_func(twitter_post="test tweet")


@pytest.mark.asyncio
async def test_use_dynamic_prompt_marketing_comment(mocker):
    redis_db = Mock(spec=RedisDB)
    prompt_manager = PromptManager(redis_db)
    mocker.patch.object(
        prompt_manager, "get_prompt", return_value="test {tweet_text} {question_prompt}"
    )
    mocker.patch(
        "redis_client.client.FUNCTION_VARIABLES",
        {"create_marketing_comment": {"tweet_text", "question_prompt"}},
    )
    mocker.patch("random.random", return_value=0.4)

    @use_dynamic_prompt("create_marketing_comment")
    async def dummy_func(tweet_text, prompt=None):
        return prompt

    result = await dummy_func(tweet_text="test tweet")
    assert (
        result
        == "test test tweet or sometimes combine your thoughts with a relevant question."
    )


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_no_delay(mocker):
    redis_db = Mock(spec=RedisDB)
    mocker.patch.object(redis_db, "get_user_posts_by_create_time", return_value=[])
    mocker.patch("random.randint", return_value=300)
    await ensure_delay_between_posts("user1")
    assert not asyncio.get_event_loop()._scheduled


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_with_delay(mocker):
    past_date = datetime(2023, 1, 1, 12, 0)
    post = Post(
        id="1",
        text="Mock tweet",
        sender_username="user1",
        timestamp=int(past_date.timestamp()),
    )
    mocker.patch.object(RedisDB, "get_user_posts_by_create_time", return_value=[post])
    mocker.patch("time.time", return_value=past_date.timestamp() + 100)
    mocker.patch("random.randint", return_value=300)
    mock_sleep = mocker.patch("asyncio.sleep", new=AsyncMock())

    await ensure_delay_between_posts("user1")
    mock_sleep.assert_called_once_with(200)


@pytest.mark.asyncio
async def test_decode_redis_list():
    src = [b"item1", b"item2"]
    result = decode_redis(src)
    assert result == ["item1", "item2"]


@pytest.mark.asyncio
async def test_decode_redis_dict():
    src = {b"key1": b"value1", b"key2": [b"item1", b"item2"]}
    result = decode_redis(src)
    assert result == {"key1": "value1", "key2": ["item1", "item2"]}


@pytest.mark.asyncio
async def test_decode_redis_invalid_type():
    with pytest.raises(Exception, match="type not handled"):
        decode_redis(123)

import asyncio
import time
from random import randint
from datetime import datetime
from loguru import logger

from redis_client.main import get_redis_db, Post

db = get_redis_db()


async def ensure_delay_between_posts(username: str, delay: int = None):
    past_date = datetime(2023, 1, 1, 12, 0)
    past_timestamp = int(past_date.timestamp())
    posts = [
        Post(id="1", text="Mock tweet 1", sender_username=username, timestamp=past_timestamp),
        Post(
            id="2",
            text="Mock tweet 2",
            sender_username=username,
            timestamp=past_timestamp,
            is_news_summary_tweet=True,
        ),
    ]
    logger.info(f'ensure_delay_between_posts {username=} {len(posts)=}')
    if posts:
        last_post = posts[-1]
        time_since_last_post = time.time() - last_post.timestamp
        if not delay:
            delay = randint(5 * 60, 10 * 60)
        logger.info(f'ensure_delay_between_posts {username=} {time_since_last_post=}')
        if time_since_last_post < delay:
            wait_time = delay - time_since_last_post
            logger.info(f'Waiting: {username=} {wait_time=}')
            await asyncio.sleep(wait_time)


def decode_redis(src):
    if isinstance(src, list):
        rv = []
        for key in src:
            rv.append(decode_redis(key))
        return rv
    elif isinstance(src, dict):
        rv = {}
        for key in src:
            rv[key.decode()] = decode_redis(src[key])
        return rv
    elif isinstance(src, bytes):
        return src.decode()
    else:
        raise Exception("type not handled: " + type(src))

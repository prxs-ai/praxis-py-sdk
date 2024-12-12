import asyncio
import logging
import time
from random import randint

from database.redis.redis_client import db


async def ensure_delay_between_posts(username: str, delay: int = None):
    posts = db.get_user_posts(username)
    logging.info(f'ensure_delay_between_posts {username=} {len(posts)=}')
    if posts:
        last_post = posts[-1]
        time_since_last_post = time.time() - last_post.timestamp
        if not delay:
            delay = randint(5 * 60, 10 * 60)
        logging.info(f'ensure_delay_between_posts {username=} {time_since_last_post=}')
        if time_since_last_post < delay:
            wait_time = delay - time_since_last_post
            logging.info(f'Waiting: {username=} {wait_time=}')
            await asyncio.sleep(wait_time)
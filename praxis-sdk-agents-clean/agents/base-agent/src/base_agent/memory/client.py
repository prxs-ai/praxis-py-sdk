from typing import Any

import redis
from loguru import logger

from base_agent.memory.config import MemoryConfig


class MemoryClient:
    def __init__(self, config: MemoryConfig):
        self.redis_client = redis.Redis(
            host=config.host,
            port=config.port,
            db=config.db,
            decode_responses=True,
        )

    def store(self, key: str, interaction: dict[str, Any]) -> None:
        try:
            self.redis_client.lpush(key, str(interaction))
        except Exception as e:
            logger.error(f"Error storing interaction in Redis: {e}")

    def read(self, key: str) -> list[dict[str, Any]]:
        try:
            interactions = self.redis_client.lrange(key, 0, -1)
            return [eval(interaction) for interaction in interactions]
        except Exception as e:
            logger.error(f"Error retrieving interactions from Redis: {e}")
            return []

    def close(self):
        self.redis_client.close()

from typing import Any

from loguru import logger
from mem0 import Memory

from base_agent.memory.config import MemoryConfig


class MemoryClient:
    def __init__(self, config: MemoryConfig):
        self.memory = Memory.from_config(config.mem0_config)

    def store(self, key: str, interaction: list[Any]) -> None:
        try:
            logger.info(f"Storing interaction: {interaction} key: {key}")
            self.memory.add(interaction, run_id=key)
        except Exception as e:
            logger.error(f"Error storing interaction in Redis: {e}")

    def read(self, key: str, limit: int = 10) -> list[dict[str, Any]]:
        try:
            logger.info(f"Fetching all memories for key: {key}")
            return self.memory.get_all(run_id=key, limit=limit)
        except Exception as e:
            logger.error(f"Error retrieving interactions from Redis: {e}")
            return []


def memory_client(config: MemoryConfig) -> MemoryClient:
    return MemoryClient(config=config)

from typing import Any

from loguru import logger
from mem0 import Memory


class MemoryClient:
    def __init__(self):
        self.memory = Memory()

    def store(self, key: str, interaction: dict[str, Any]) -> None:
        try:
            self.memory.add(interaction, run_id=key)
        except Exception as e:
            logger.error(f"Error storing interaction in Redis: {e}")

    def read(self, key: str, limit: int = 3) -> list[dict[str, Any]]:
        try:
            return self.memory.get_all(run_id=key, limit=limit)
        except Exception as e:
            logger.error(f"Error retrieving interactions from Redis: {e}")
            return []


def memory_client() -> MemoryClient:
    return MemoryClient()

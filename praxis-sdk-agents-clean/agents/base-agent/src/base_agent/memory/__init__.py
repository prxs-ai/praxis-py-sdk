from base_agent.memory.client import MemoryClient
from base_agent.memory.config import memory_config


def memory_client(*args, **kwargs):
    return MemoryClient(config=memory_config)

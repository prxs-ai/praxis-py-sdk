from base_agent.ai_registry.client import AiRegistryClient
from base_agent.ai_registry.config import ai_registry_config


def ai_registry_client(*args, **kwargs):
    return AiRegistryClient(config=ai_registry_config)

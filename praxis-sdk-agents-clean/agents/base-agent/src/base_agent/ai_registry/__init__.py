from base_agent.ai_registry.client import AiRegistryClient
from base_agent.ai_registry.config import get_ai_registry_config


def ai_registry_client(*args, **kwargs):
    return AiRegistryClient(config=get_ai_registry_config())

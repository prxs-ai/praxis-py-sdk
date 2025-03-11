from base_agent.domain_knowledge.client import LightRagClient
from base_agent.domain_knowledge.config import get_light_rag_config


def light_rag_client(*args, **kwargs):
    return LightRagClient(config=get_light_rag_config())

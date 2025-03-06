from base_agent.domain_knowledge.client import LightRagClient
from base_agent.domain_knowledge.config import light_rag_config


def light_rag_client(*args, **kwargs):
    return LightRagClient(config=light_rag_config)

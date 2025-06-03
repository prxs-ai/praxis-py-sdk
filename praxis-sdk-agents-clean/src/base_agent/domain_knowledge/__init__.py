from base_agent.const import EntrypointGroup
from base_agent.prompt.config import BasicPromptConfig
from base_agent.utils import get_entrypoint


def light_rag_builder(*args, **kwargs):
    config: BasicPromptConfig = get_entrypoint(EntrypointGroup.DOMAIN_KNOWLEDGE_CONFIG_ENTRYPOINT).load()
    return get_entrypoint(EntrypointGroup.DOMAIN_KNOWLEDGE_ENTRYPOINT).load()(config())

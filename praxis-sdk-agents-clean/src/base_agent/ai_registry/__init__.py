from base_agent.const import EntrypointGroup
from base_agent.prompt.config import BasicPromptConfig
from base_agent.utils import get_entrypoint


def ai_registry_builder(*args, **kwargs):
    config: BasicPromptConfig = get_entrypoint(EntrypointGroup.AI_REGISTRY_CONFIG_ENTRYPOINT).load()
    return get_entrypoint(EntrypointGroup.AI_REGISTRY_ENTRYPOINT).load()(config())

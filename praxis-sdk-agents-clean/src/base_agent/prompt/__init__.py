from base_agent.const import EntrypointGroup
from base_agent.prompt.config import BasicPromptConfig
from base_agent.utils import get_entrypoint


def prompt_builder():
    config: BasicPromptConfig = get_entrypoint(EntrypointGroup.AGENT_PROMPT_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.AGENT_PROMPT_ENTRYPOINT).load()(config())

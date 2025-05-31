from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def executor_builder():
    config = get_entrypoint(EntrypointGroup.AGENT_EXECUTOR_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.AGENT_EXECUTOR_ENTRYPOINT).load()(config())

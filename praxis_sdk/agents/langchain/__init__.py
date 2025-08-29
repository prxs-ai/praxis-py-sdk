from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.utils import get_entrypoint


def executor_builder():
    config = get_entrypoint(EntrypointGroup.AGENT_EXECUTOR_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.AGENT_EXECUTOR_ENTRYPOINT).load()(config())

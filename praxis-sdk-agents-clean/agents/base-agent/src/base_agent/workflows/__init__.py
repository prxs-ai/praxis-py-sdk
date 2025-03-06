from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def workflow_builder():
    config = get_entrypoint(EntrypointGroup.AGENT_WORKFLOW_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.AGENT_WORKFLOW_ENTRYPOINT).load()(config())

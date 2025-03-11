from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def memory_builder(*args, **kwargs):
    return get_entrypoint(EntrypointGroup.MEMORY_ENTRYPOINT).load()()

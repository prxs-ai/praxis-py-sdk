from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def p2p_builder():
    return get_entrypoint(EntrypointGroup.P2P_ENTRYPOINT).load()() # type: ignore

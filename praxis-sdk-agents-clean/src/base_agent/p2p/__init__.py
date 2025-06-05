from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def p2p_builder():
    from base_agent.p2p.config import get_p2p_config
    from base_agent.p2p.utils import init_keystore

    # init keystore first
    init_keystore(get_p2p_config().keystore_path)

    # load p2p entrypoint
    return get_entrypoint(EntrypointGroup.P2P_ENTRYPOINT).load()() # type: ignore

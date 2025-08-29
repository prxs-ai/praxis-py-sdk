from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.utils import get_entrypoint


def p2p_builder():
    from praxis_sdk.agents.p2p.config import get_p2p_config
    from praxis_sdk.agents.p2p.utils import init_keystore

    # init keystore first
    init_keystore(get_p2p_config().keystore_path)

    # load p2p entrypoint
    return get_entrypoint(EntrypointGroup.P2P_ENTRYPOINT).load()()  # type: ignore

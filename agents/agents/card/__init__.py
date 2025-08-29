from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.utils import get_entrypoint


def card_builder():
    return get_entrypoint(EntrypointGroup.CARD_ENTRYPOINT).load()()

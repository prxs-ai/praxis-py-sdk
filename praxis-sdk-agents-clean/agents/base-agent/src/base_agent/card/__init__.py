from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def card_builder():
    return get_entrypoint(EntrypointGroup.CARD_ENTRYPOINT).load()()

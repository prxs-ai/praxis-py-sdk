from base_provider.abc import AbstractDataTrigger
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint


def trigger_builder() -> AbstractDataTrigger:
    config = get_entrypoint(EntrypointGroup.DATA_TRIGGER_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.DATA_TRIGGER_ENTRYPOINT).load()(config())

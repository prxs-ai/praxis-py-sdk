from base_provider.abc import AbstractDataContract
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint


def contract_builder() -> AbstractDataContract:
    config = get_entrypoint(EntrypointGroup.DATA_CONTRACT_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.DATA_CONTRACT_ENTRYPOINT).load()(config())

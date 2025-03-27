from base_provider.abc import AbstractDataSource
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint


def source_builder() -> AbstractDataSource:
    config = get_entrypoint(EntrypointGroup.DATA_SOURCE_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.DATA_SOURCE_ENTRYPOINT).load()(config())

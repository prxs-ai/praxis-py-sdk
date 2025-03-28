from base_provider.abc import AbstractDataStream
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint


def stream_builder() -> AbstractDataStream:
    config = get_entrypoint(EntrypointGroup.DATA_STREAM_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.DATA_STREAM_ENTRYPOINT).load()(config())

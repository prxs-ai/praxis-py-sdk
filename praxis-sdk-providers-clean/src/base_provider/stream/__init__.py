from base_provider.abc import AbstractDataStream
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint


def stream_builder(*args, **kwargs) -> AbstractDataStream:
    return get_entrypoint(EntrypointGroup.DATA_STREAM_ENTRYPOINT).load()(*args, **kwargs)

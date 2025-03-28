from base_provider.abc import AbstractDataSink
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint


def sink_builder() -> AbstractDataSink:
    config = get_entrypoint(EntrypointGroup.DATA_SINK_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.DATA_SINK_ENTRYPOINT).load()(config())

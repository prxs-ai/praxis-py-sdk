from base_provider.abc import AbstractDataSink
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint, get_entrypoints


def sinks_builder(sinks: list[str]) -> list[AbstractDataSink]:
    _sinks = []
    for entrypoint in get_entrypoints(EntrypointGroup.DATA_SINK_CONFIG_ENTRYPOINT):
        if entrypoint.name in sinks:
            sink_config = entrypoint.load()()
            _sinks.append(get_entrypoint(EntrypointGroup.DATA_SINK_ENTRYPOINT, entrypoint.name).load(sink_config))

    return _sinks

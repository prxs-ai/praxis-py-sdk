from base_provider.abc import AbstractDataSink
from base_provider.const import EntrypointGroup
from base_provider.sinks.const import DefaultSinkEntrypointType
from base_provider.utils import get_entrypoints


def sinks_builder(**kwargs) -> dict[str, AbstractDataSink]:
    _sinks_dict = {}
    for entrypoint in get_entrypoints(EntrypointGroup.DATA_SINK_ENTRYPOINT):
        _sinks_dict[entrypoint.name] = entrypoint.load()(**kwargs.pop(entrypoint.name, {}))

    basic = str(DefaultSinkEntrypointType.BASIC)
    if basic not in _sinks_dict:
        from base_provider.sinks.base import get_data_sink as get_default_data_processor

        _sinks_dict[basic] = get_default_data_processor(**kwargs.pop(basic, {}))

    kafka = str(DefaultSinkEntrypointType.KAFKA)
    if kafka not in _sinks_dict:
        from base_provider.sinks.kafka import get_kafka_data_sink as get_kafka_data_processor

        _sinks_dict[kafka] = get_kafka_data_processor(**kwargs.pop(kafka, {}))

    return _sinks_dict

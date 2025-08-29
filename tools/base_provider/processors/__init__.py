from base_provider.abc import AbstractDataProcessor
from base_provider.const import EntrypointGroup, EntrypointType
from base_provider.utils import get_entrypoints


def processors_builder(**kwargs) -> dict[str, AbstractDataProcessor]:
    _processors_dict = {}
    for entrypoint in get_entrypoints(EntrypointGroup.DATA_PROCESSOR_ENTRYPOINT):
        _processors_dict[entrypoint.name] = entrypoint.load()(**kwargs.pop(entrypoint.name, {}))
    if len(_processors_dict) < 1:
        from base_provider.processors.base import get_data_processor as get_default_data_processor
        basic = str(EntrypointType.BASIC)
        _processors_dict[basic] = get_default_data_processor(**kwargs.pop(basic, {}))

    return _processors_dict

from base_provider.abc import AbstractDataSource
from base_provider.const import EntrypointGroup, EntrypointType
from base_provider.utils import get_entrypoints


def sources_builder(**kwargs) -> dict[str, AbstractDataSource]:
    _sources_dict = {}
    for entrypoint in get_entrypoints(EntrypointGroup.DATA_SOURCE_ENTRYPOINT):
        _sources_dict[entrypoint.name] = entrypoint.load()(**kwargs.pop(entrypoint.name, {}))
    if len(_sources_dict) < 1:
        from base_provider.sources.base import get_data_source as get_default_data_processor
        basic = str(EntrypointType.BASIC)
        _sources_dict[basic] = get_default_data_processor(**kwargs.pop(basic, {}))

    return _sources_dict


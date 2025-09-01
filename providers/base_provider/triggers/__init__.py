from base_provider.abc import AbstractDataTrigger
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoints


def triggers_builder(*args, **kwargs) -> dict[str, AbstractDataTrigger]:
    _triggers_dict = {}
    for entrypoint in get_entrypoints(EntrypointGroup.DATA_TRIGGER_ENTRYPOINT):
        _triggers_dict[entrypoint.name] = entrypoint.load()(**kwargs.pop(entrypoint.name, {}))
    # no triggers by default

    return _triggers_dict

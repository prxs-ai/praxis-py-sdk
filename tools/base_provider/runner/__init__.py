from base_provider.abc import AbstractDataRunner
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint


def runner_builder(*args, **kwargs) -> AbstractDataRunner:
    try:
        return get_entrypoint(EntrypointGroup.DATA_RUNNER_ENTRYPOINT).load()(*args, **kwargs)
    except Exception:
        from base_provider.runner.base import get_data_runner as get_default_data_runner

        return get_default_data_runner(*args, **kwargs)

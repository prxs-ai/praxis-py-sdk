from typing import Any, TypeVar

from base_provider.abc import AbstractDataRunner, AbstractDataStream
from base_provider.runner.config import BaseDataRunnerConfig, get_data_runner_config
from base_provider.sinks.const import DefaultSinkEntrypointType
from fast_depends import Depends, inject

T = TypeVar("T")

class BaseDataRunner(AbstractDataRunner[T]):
    """Base implementation of data runner."""

    def __init__(self, config: BaseDataRunnerConfig):
        self.config = config

        self._is_running = False

    async def run_once(self, stream: AbstractDataStream[T, Any], *args, filters: dict[str, Any], **kwargs) -> Any:
        data = await stream.fetch_batch(*args, **kwargs)
        data = await stream.process_batch(data, filters=filters)
        # do not launch the sink, just return the data
        return data

    async def run(self, stream: AbstractDataStream[T, Any], *args, filters: dict[str, Any], topic: str, **kwargs) -> None:
        data = await stream.fetch_batch(*args, **kwargs)
        data = await stream.process_batch(data, filters=filters)

        # TODO: fix this
        kwargs[str(DefaultSinkEntrypointType.KAFKA)] = {"topic": topic}

        await stream.write_batch(data, *args, **kwargs)


    @classmethod
    def start(cls) -> None:
        pass

    @classmethod
    def stop(cls) -> None:
        pass

@inject
def get_data_runner(config: BaseDataRunnerConfig = Depends(get_data_runner_config)) -> BaseDataRunner:
    return BaseDataRunner(config)

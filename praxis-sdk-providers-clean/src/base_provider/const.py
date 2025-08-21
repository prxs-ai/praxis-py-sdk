from enum import Enum


class EntrypointGroup(str, Enum):
    APP_ENTRYPOINT = "provider.entrypoint"

    DATA_CONTRACT_ENTRYPOINT = "provider.contract.entrypoint"

    DATA_TRIGGER_ENTRYPOINT = "provider.trigger.entrypoint"

    DATA_SOURCE_ENTRYPOINT = "provider.source.entrypoint"

    DATA_PROCESSOR_ENTRYPOINT = "provider.processor.entrypoint"

    DATA_SINK_ENTRYPOINT = "provider.sink.entrypoint"

    DATA_STREAM_ENTRYPOINT = "provider.stream.entrypoint"
    DATA_RUNNER_ENTRYPOINT = "provider.runner.entrypoint"

    def __str__(self):
        return self.value

    @property
    def group_name(self):
        return str(self)


class EntrypointType(str, Enum):
    BASIC = "basic"
    TARGET = "target"

    def __str__(self):
        return self.value

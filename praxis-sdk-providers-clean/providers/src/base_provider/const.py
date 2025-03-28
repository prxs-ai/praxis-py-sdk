from enum import Enum


class EntrypointGroup(str, Enum):
    CONFIG_ENTRYPOINT = "provider.config.entrypoint"
    APP_ENTRYPOINT = "provider.entrypoint"

    DATA_CONTRACT_CONFIG_ENTRYPOINT = "provider.data_contract.config.entrypoint"
    DATA_CONTRACT_ENTRYPOINT = "provider.data_contract.entrypoint"

    DATA_TRIGGER_CONFIG_ENTRYPOINT = "provider.data_trigger.config.entrypoint"
    DATA_TRIGGER_ENTRYPOINT = "provider.data_trigger.entrypoint"

    DATA_SOURCE_CONFIG_ENTRYPOINT = "provider.data_source.config.entrypoint"
    DATA_SOURCE_ENTRYPOINT = "provider.data_source.entrypoint"

    DATA_PROCESSOR_CONFIG_ENTRYPOINT = "provider.data_processor.config.entrypoint"
    DATA_PROCESSOR_ENTRYPOINT = "provider.data_processor.entrypoint"

    DATA_SINK_CONFIG_ENTRYPOINT = "provider.data_sink.config.entrypoint"
    DATA_SINK_ENTRYPOINT = "provider.data_sink.entrypoint"

    DATA_STREAM_CONFIG_ENTRYPOINT = "provider.data_stream.config.entrypoint"
    DATA_STREAM_ENTRYPOINT = "provider.data_stream.entrypoint"

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

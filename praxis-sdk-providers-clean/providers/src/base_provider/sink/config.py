from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseDataSinkConfig(BaseSettings):
    pass


class KafkaDataSinkConfig(BaseDataSinkConfig):
    kafka_bootstrap_uri: str


@lru_cache
def get_data_sink_config() -> BaseDataSinkConfig:
    return BaseDataSinkConfig()


@lru_cache
def get_kafka_data_sink_config() -> KafkaDataSinkConfig:
    return KafkaDataSinkConfig()

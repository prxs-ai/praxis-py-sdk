from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseProviderConfig(BaseSettings):
    kafka_bootstrap_uri: str
    kafka_topic_template: str = "{domain}.{version}.{data_type}.{topic_spec_hash}"
    kafka_message_format: str = "msgpack"


@lru_cache
def get_provider_config() -> BaseProviderConfig:
    return BaseProviderConfig()

from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseDataContractConfig(BaseSettings):
    data_contract_version: str = "0.0.1"
    data_contract_uid_template: str = "urn:datacontract:provider:{domain}:{version}"


@lru_cache
def get_data_contract_config() -> BaseDataContractConfig:
    return BaseDataContractConfig()

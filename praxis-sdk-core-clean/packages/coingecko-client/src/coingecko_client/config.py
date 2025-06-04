from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InterfaceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class CoingeckoSettings(InterfaceSettings):
    api_key: str = Field(validation_alias="COINGECKO_API_KEY")
    base_url: str = Field(validation_alias="COINGECKO_API_URL")


class RedisSettings(InterfaceSettings):
    redis_host: str = Field(validation_alias="REDIS_HOST")
    redis_port: int = Field(validation_alias="REDIS_PORT")
    redis_db: int = Field(validation_alias="REDIS_DB")


class HyperLiquidSettings(InterfaceSettings):
    base_url: str = Field(validation_alias="HYPERLIQUD_API_URL")


class ServerSettings(InterfaceSettings):
    coingecko: CoingeckoSettings = CoingeckoSettings()
    redis: RedisSettings = RedisSettings()
    hyperliquid: HyperLiquidSettings = HyperLiquidSettings()

    REDIS_PERSONA_KEY: str = "available_personas"


@lru_cache
def get_server_settings() -> ServerSettings:
    return ServerSettings()  # type: ignore

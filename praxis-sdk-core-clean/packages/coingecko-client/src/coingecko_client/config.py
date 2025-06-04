from functools import lru_cache

from pydantic import Field, RedisDsn, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class InterfaceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra='ignore')


class CoingeckoSettings(InterfaceSettings):
    api_key: str = Field(validation_alias="COINGECKO_API_KEY", default="")
    base_url: str = Field(validation_alias="COINGECKO_API_URL", default="")


class RedisSettings(InterfaceSettings):
    redis_host: str = Field(validation_alias="REDIS_HOST", default="")
    redis_port: int = Field(validation_alias="REDIS_PORT", default=1)
    redis_db: int = Field(validation_alias="REDIS_DB", default=1)


class HyperLiquidSettings(InterfaceSettings):
    base_url: str = Field(validation_alias="HYPERLIQUD_API_URL", default="")


class ServerSettings(InterfaceSettings):
    coingecko: CoingeckoSettings = CoingeckoSettings()
    redis: RedisSettings = RedisSettings()
    hyperliquid: HyperLiquidSettings = HyperLiquidSettings()

    REDIS_PERSONA_KEY: str = "available_personas"


@lru_cache
def get_server_settings() -> ServerSettings:
    return ServerSettings()  # type: ignore

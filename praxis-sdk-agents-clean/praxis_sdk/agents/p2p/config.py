from functools import lru_cache

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentHost(BaseSettings):
    host: str = pydantic.Field("localhost", description="Agent Host")
    port: int = pydantic.Field(default=8000, description="Agent Port")
    schema: str = pydantic.Field(default="http", description="https or http")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RELAY_SERVICE_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )

    @property
    def url(self) -> str:
        return f"{self.schema}://{self.host}" if self.port == 80 else f"{self.schema}://{self.host}:{self.port}"


class RelayService(BaseSettings):
    host: str = pydantic.Field("relay-service.dev.prxs.ai", description="Relay Service Host")
    port: int = pydantic.Field(default=80, description="Relay Service Port")
    schema: str = pydantic.Field(default="https", description="https or http")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RELAY_SERVICE_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )

    @property
    def url(self) -> str:
        return f"{self.schema}://{self.host}" if self.port == 80 else f"{self.schema}://{self.host}:{self.port}"


class P2PConfig(BaseSettings):
    relay_addr: str = "/ip4/127.0.0.1/tcp/9000/p2p/RELAY_PEER_ID"
    keystore_path: str = "./keys"
    noise_key: str | None = None

    relay_service: RelayService = RelayService()  # type: ignore
    agent_host: AgentHost = AgentHost()  # type: ignore

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="P2P_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


@lru_cache
def get_p2p_config() -> P2PConfig:
    return P2PConfig()

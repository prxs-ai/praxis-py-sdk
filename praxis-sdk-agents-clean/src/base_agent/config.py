import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
import pydantic


class BasicAgentConfig(BaseSettings):
    system_prompt: str = "Act as a helpful assistant. You are given a task to complete."
    agents: dict[str, str] = {}

    # Libp2p configuration
    registry_http_url: str = pydantic.Field("http://localhost:8081")
    registry_relay_peer_id: str = pydantic.Field("12D3KooWL1N7R2UDf9bVeyP6QR2hR7F1qXSkX5cv3H5Xz7N4L7kE")
    registry_relay_multiaddr_template: str = pydantic.Field("/ip4/127.0.0.1/tcp/4001/p2p/{}")
    agent_p2p_listen_addr: str = pydantic.Field("/ip4/0.0.0.0/tcp/0")
    agent_name: str = pydantic.Field("base-agent")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore"
    )

    def __str__(self) -> str:
        """
        Serialize the config to a pretty JSON string for prompt usage.
        """
        return json.dumps(self.model_dump(), indent=2, ensure_ascii=False)


@lru_cache
def get_agent_config(**kwargs) -> BasicAgentConfig:
    return BasicAgentConfig(**kwargs)

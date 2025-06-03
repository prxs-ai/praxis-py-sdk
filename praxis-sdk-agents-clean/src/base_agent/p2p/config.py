from functools import lru_cache

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class P2PConfig(BaseSettings):
    relay_addr: str = "/ip4/127.0.0.1/tcp/9000/p2p/RELAY_PEER_ID"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="P2P_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


@lru_cache
def get_p2p_config() -> P2PConfig:
    return P2PConfig()

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemoryConfig(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REDIS_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


memory_config = MemoryConfig()

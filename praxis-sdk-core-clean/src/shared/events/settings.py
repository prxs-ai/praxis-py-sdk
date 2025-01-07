from pydantic_settings import BaseSettings, SettingsConfigDict


class AvroSettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_prefix="AVRO_")

    url: str
    auth: str | None = None

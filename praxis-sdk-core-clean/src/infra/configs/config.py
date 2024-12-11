from pydantic import BaseSettings, RedisDsn, validator
from starlette.config import Config


class Settings(BaseSettings):
    config = Config(".env")

    POSTGRES_DB: str = "postgres"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

settings = Settings()
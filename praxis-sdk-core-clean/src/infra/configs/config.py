from pydantic import field_validator, ValidationInfo, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


load_dotenv()


class InfrastructureConfig(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "postgres"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: str = "0"

    postgres_dsn: PostgresDsn | None = None
    redis_dsn: RedisDsn | None = None

    @field_validator('postgres_dsn', mode='before')
    @classmethod
    def get_postres_dsn(cls, _, info: ValidationInfo):
        return PostgresDsn.build(
            scheme='postgresql+asyncpg',
            username=info.data['postgres_user'],
            password=info.data['postgres_password'],
            host=info.data['postgres_host'],
            port=info.data['postgres_port'],
            path=info.data['postgres_db'],
        )

    @field_validator('redis_dsn', mode='before')
    @classmethod
    def get_redis_dsn(cls, _, info: ValidationInfo):
        return RedisDsn.build(
            scheme='redis',
            host=info.data['redis_host'],
            port=info.data['redis_port'],
            path=info.data['redis_db'],
        )


class Settings(BaseSettings):
    infrastructure: InfrastructureConfig = InfrastructureConfig()


settings = Settings()

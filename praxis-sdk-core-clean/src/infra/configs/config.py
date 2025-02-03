from functools import lru_cache

from pydantic import field_validator, ValidationInfo, PostgresDsn, RedisDsn, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from cryptography.fernet import Fernet


load_dotenv()


class InfrastructureConfig(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "postgres"
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = 5432
    postgres_logs: bool = False

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: str = "0"

    postgres_dsn: str | None = None
    redis_dsn: RedisDsn | None = None
    fernet_key: bytes = b"glEo_3r7sSMy8tIxqRyvwLW0CrKD44ADJ7qIgWVeOOI="

    # S3 storage
    s3_bucket_prefix: str = "praxis"
    s3_region: str = Field(validation_alias="S3_REGION")
    s3_access_key: str = Field(validation_alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(validation_alias="S3_SECRET")

    kafka_host: str = "localhost"
    kafka_port: int = 9092

    QDRANT_HOST: str = Field(default="qdrant", validation_alias="QDRANT_HOST")
    QDRANT_PORT: int = 6333

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    @field_validator('postgres_dsn', mode='before')
    @classmethod
    def get_postgres_dsn(cls, _, info: ValidationInfo):
        return f"postgresql+asyncpg://{info.data['postgres_user']}:{info.data['postgres_password']}@{info.data['postgres_host']}:{info.data['postgres_port']}/{info.data['postgres_db']}"
        # return PostgresDsn.build(
        #     scheme='postgresql+asyncpg',
        #     username=info.data['postgres_user'],
        #     password=info.data['postgres_password'],
        #     host=info.data['postgres_host'],
        #     port=info.data['postgres_port'],
        #     path=info.data['postgres_db'],
        # )

    @field_validator('redis_dsn', mode='before')
    @classmethod
    def get_redis_dsn(cls, _, info: ValidationInfo):
        return RedisDsn.build(
            scheme='redis',
            host=info.data['redis_host'],
            port=info.data['redis_port'],
            path=info.data['redis_db'],
        )

    @property
    def s3_base_url(self):
        return f"https://{self.s3_region}.digitaloceanspaces.com"


class TelegramAppSetupServiceConfig(BaseSettings):
    base_url: str = "https://my.telegram.org"
    send_password_endpoint: str = "/auth/send_password"
    login_endpoint: str = "/auth/login"
    app_endpoint: str = "/apps"
    create_endpoint: str = "/apps/create"

    class Config:
        env_prefix = "TELEGRAM_"


class Settings(BaseSettings):
    infrastructure: InfrastructureConfig = InfrastructureConfig()
    telegram_config: TelegramAppSetupServiceConfig = TelegramAppSetupServiceConfig()
    ambassador_username: str = "testandoo6"
    CREATE_POST_INTERVAL: int = 60 * 60 * 4
    GORILLA_MARKETING_INTERVAL: int = 60 * 60 * 4
    COMMENT_AGIX_INTERVAL: int = 60 * 60 * 4
    ANSWER_DIRECT_INTERVAL: int = 60 * 60 * 4
    ANSWER_COMMENT_INTERVAL: int = 60 * 60 * 4
    ANSWER_MY_COMMENT_INTERVAL: int = 60 * 4
    LIKES_INTERVAL: int = 6 * 60 * 60
    PARTNERSHIP_INTERVAL: int = 12 * 60 * 60
    TWITTER_CLIENT_ID: str = 'eG8wX3VEcVdtcnZyNnhEQ3ZUbTU6MTpjaQ'
    TWITTER_CLIENT_SECRET: str = 'TeK9tRPPirYbpGhiyb_yaOMYJA7ijvCQaU6O5vu5VioA8knBAA'
    TWITTER_BASIC_BEARER_TOKEN: str = 'AAAAAAAAAAAAAAAAAAAAAALFxQEAAAAAteK66aMgMrX%2BoWlqS1nuVBbo834%3DKvDbzJWyE0X6hea56JtvXGPvu58wP31Tym00sFi68RKJ9OqLfj'
    TWITTER_REDIRECT_URI: str = 'http://185.53.46.123:8000/twitter/oauth/callback/'
    OPENAI_API_KEY: str = '***REMOVED***'
    OPEN_AI_MODEL: str = "gpt-4o-2024-08-06"
    LOGS_DIR: str = "../logs"
    TWEETSCOUT_API_KEY: str = "***REMOVED***"
    ANTHROPIC_API_KEY: str = '***REMOVED***'

    # FAL AI
    fal_ai_api_key: str = ""

    # SIWE
    domain: str = "localhost"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_in: int = 1440

    # Creativity
    creativity_api_id: str = Field(validation_alias="CREATIVITY_API_ID")
    creativity_api_key: str = Field(validation_alias="CREATIVITY_API_KEY")
    creativity_base_url: str = "https://api.creatify.ai/api"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore


cipher = Fernet(get_settings().infrastructure.fernet_key)

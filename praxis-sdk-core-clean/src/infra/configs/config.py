from pydantic import field_validator, ValidationInfo, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from cryptography.fernet import Fernet


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
    fernet_key: bytes = b"glEo_3r7sSMy8tIxqRyvwLW0CrKD44ADJ7qIgWVeOOI="


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
    ambassador_username: str = "shuib420"
    CREATE_POST_INTERVAL: int = 60
    GORILLA_MARKETING_INTERVAL: int = 4 * 60 * 60
    COMMENT_AGIX_INTERVAL: int = 60 * 60
    ANSWER_DIRECT_INTERVAL: int = 10 * 60
    ANSWER_COMMENT_INTERVAL: int = 2 * 60 * 60
    ANSWER_MY_COMMENT_INTERVAL: int = 30 * 60
    LIKES_INTERVAL: int = 6 * 60 * 60
    PARTNERSHIP_INTERVAL: int = 12 * 60 * 60
    TWITTER_CLIENT_ID: str = 'eG8wX3VEcVdtcnZyNnhEQ3ZUbTU6MTpjaQ'
    TWITTER_CLIENT_SECRET: str = 'TeK9tRPPirYbpGhiyb_yaOMYJA7ijvCQaU6O5vu5VioA8knBAA'
    TWITTER_BASIC_BEARER_TOKEN: str = 'AAAAAAAAAAAAAAAAAAAAAALFxQEAAAAAteK66aMgMrX%2BoWlqS1nuVBbo834%3DKvDbzJWyE0X6hea56JtvXGPvu58wP31Tym00sFi68RKJ9OqLfj'
    TWITTER_REDIRECT_URI: str = 'http://localhost:8228/api/authenticate/twitter/callback'
    OPENAI_API_KEY: str = '***REMOVED***'
    OPEN_AI_MODEL: str = "gpt-4o-2024-08-06"
    LOGS_DIR: str = "../logs"
    TWEETSCOUT_API_KEY:str = "***REMOVED***"


settings = Settings()
cipher = Fernet(settings.infrastructure.fernet_key)

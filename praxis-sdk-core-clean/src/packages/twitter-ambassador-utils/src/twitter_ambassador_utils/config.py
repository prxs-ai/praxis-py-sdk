from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    TWITTER_CLIENT_ID: str
    TWITTER_REDIRECT_URI: str
    TWITTER_CLIENT_SECRET: str
    FERNET_KEY: bytes
    TWITTER_BASIC_BEARER_TOKEN: str
    VAULT_ADDRESS: str
    VAULT_NAMESPACE: str
    VAULT_ROLE_ID: str
    VAULT_SECRET_ID: str


@lru_cache
def get_settings():
    return Settings()


cipher = Fernet(get_settings().FERNET_KEY)

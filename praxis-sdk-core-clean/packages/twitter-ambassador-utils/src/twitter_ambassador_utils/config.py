from functools import lru_cache

import hvac
from cryptography.fernet import Fernet
from loguru import logger
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TWITTER_CLIENT_ID: str
    TWITTER_REDIRECT_URI: str
    TWITTER_CLIENT_SECRET: str
    FERNET_KEY: bytes
    TWITTER_BASIC_BEARER_TOKEN: str
    VAULT_URL: str | None = None
    VAULT_NAMESPACE: str | None = None
    VAULT_ROLE_ID: str | None = None
    VAULT_SECRET_ID: str | None = None


@lru_cache
def get_settings():
    return Settings()


cipher = Fernet(get_settings().FERNET_KEY)


def get_hvac_client():
    HVAC_CLIENT = hvac.Client(
        url=get_settings().VAULT_URL, namespace=get_settings().VAULT_NAMESPACE
    )
    HVAC_CLIENT.auth.approle.login(
        role_id=get_settings().VAULT_ROLE_ID, secret_id=get_settings().VAULT_SECRET_ID
    )

    if HVAC_CLIENT.is_authenticated():
        logger.info("Successfully connect to Vault")
        return HVAC_CLIENT
    logger.info("Error while connecting to Vault.")
    raise NotImplementedError("Error while connecting to Vault.")

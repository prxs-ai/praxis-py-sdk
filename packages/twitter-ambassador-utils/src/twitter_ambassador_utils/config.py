from typing import Optional

import hvac
from cryptography.fernet import Fernet
from loguru import logger
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    TWITTER_CLIENT_ID: str = ""
    TWITTER_REDIRECT_URI: str = ""
    TWITTER_CLIENT_SECRET: str = ""
    FERNET_KEY: bytes = b"ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
    TWITTER_BASIC_BEARER_TOKEN: str = "str"
    VAULT_URL: Optional[str] = None
    VAULT_NAMESPACE: Optional[str] = None
    VAULT_ROLE_ID: Optional[str] = None
    VAULT_SECRET_ID: Optional[str] = None


@lru_cache
def get_settings():
    return Settings()


cipher = Fernet(get_settings().FERNET_KEY)


def get_hvac_client():
    HVAC_CLIENT = hvac.Client(url=get_settings().VAULT_URL, namespace=get_settings().VAULT_NAMESPACE)
    auth_response = HVAC_CLIENT.auth.approle.login(role_id=get_settings().VAULT_ROLE_ID, secret_id=get_settings().VAULT_SECRET_ID)

    if HVAC_CLIENT.is_authenticated():
        logger.info("Successfully connect to Vault")
        return HVAC_CLIENT
    else:
        logger.info("Error while connecting to Vault.")
        raise NotImplementedError("Error while connecting to Vault.")

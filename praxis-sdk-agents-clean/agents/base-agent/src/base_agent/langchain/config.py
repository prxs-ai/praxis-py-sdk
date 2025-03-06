from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings

from base_agent.langchain.langfuse.config import BasicLangFuseConfig


class BasicLangChainConfig(BaseSettings):
    openai_api_key: SecretStr
    openai_api_model: str = "gpt-4o"

    langfuse_enabled: bool = False

class LangChainConfigWithLangfuse(BasicLangChainConfig, BasicLangFuseConfig):
    pass


@lru_cache
def get_langchain_config() -> BasicLangChainConfig:
    if BasicLangChainConfig().langfuse_enabled:
        return LangChainConfigWithLangfuse()
    return BasicLangChainConfig()

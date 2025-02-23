from functools import lru_cache

from pydantic_settings import BaseSettings

from base_agent.langfuse.config import BasicLangFuseConfig


class BasicLangChainConfig(BaseSettings):
    langfuse_enabled: bool = False

class LangChainConfigWithLangfuse(BasicLangChainConfig, BasicLangFuseConfig):
    pass


@lru_cache
def get_langchain_config() -> BasicLangChainConfig:
    if BasicLangChainConfig().langfuse_enabled:
        return LangChainConfigWithLangfuse()
    return BasicLangChainConfig()

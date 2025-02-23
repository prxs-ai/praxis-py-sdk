from functools import lru_cache

from pydantic_settings import BaseSettings

from base_agent.langfuse.config import BasicLangFuseConfig


class BasicPromptConfig(BaseSettings):
    group_name: str = "agent.prompt.entrypoint"

    langfuse_enabled: bool = False

class PromptConfigWithLangfuse(BasicPromptConfig, BasicLangFuseConfig):
    pass


@lru_cache
def get_prompt_config() -> BasicPromptConfig:
    if BasicPromptConfig().langfuse_enabled:
        return PromptConfigWithLangfuse()
    return BasicPromptConfig()

from enum import Enum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from base_agent.langchain.langfuse.config import BasicLangFuseConfig


class ProviderEnum(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"

    def __str__(self):
        return self.value


# Base class for any LLM provider
class BaseLLMProviderConfig(BaseSettings):
    model: Annotated[str, Field(..., description="Model identifier to use for this provider")]


# OpenAI provider configuration
class OpenAIConfig(BaseLLMProviderConfig):
    api_key: SecretStr | None = None
    model: str = "gpt-4o"


# DeepSeek provider configuration
class DeepSeekConfig(BaseLLMProviderConfig):
    api_key: SecretStr | None = None
    model: str = "deepseek-chat"


# Anthropic provider configuration
class AnthropicConfig(BaseLLMProviderConfig):
    api_key: SecretStr | None = None
    model: str = "claude-3-7-sonnet-latest"


class BasicLangChainConfig(BaseSettings):
    provider: ProviderEnum = ProviderEnum.OPENAI
    openai: OpenAIConfig | None = None
    deepseek: DeepSeekConfig | None = None
    anthropic: AnthropicConfig | None = None

    openai_api_key: SecretStr
    openai_api_model: str = "gpt-4o"

    langfuse_enabled: bool = False

    class Config:
        arbitrary_types_allowed = True


class LangChainConfigWithLangfuse(BasicLangChainConfig, BasicLangFuseConfig):
    pass


@lru_cache
def get_langchain_config() -> BasicLangChainConfig:
    config = BasicLangChainConfig()

    # Initialize provider configs if they're None but selected as provider
    if config.provider == ProviderEnum.OPENAI and config.openai is None:
        config.openai = OpenAIConfig(api_key=config.openai_api_key)
    elif config.provider == ProviderEnum.DEEPSEEK and config.deepseek is None:
        config.deepseek = DeepSeekConfig()
    elif config.provider == ProviderEnum.ANTHROPIC and config.anthropic is None:
        config.anthropic = AnthropicConfig()

    if BasicLangChainConfig().langfuse_enabled:
        # Transfer the provider settings to the Langfuse config
        langfuse_config = LangChainConfigWithLangfuse(
            provider=config.provider,
            openai=config.openai,
            deepseek=config.deepseek,
            anthropic=config.anthropic,
        )
        return langfuse_config

    return config

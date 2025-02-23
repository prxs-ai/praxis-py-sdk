from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class BasicAgentConfig(BaseSettings):
    group_name: str = "agent.entrypoint"

    openai_api_key: SecretStr
    openai_api_model: str = "gpt-4o"

    final_answer_tool_name: str = "return-answer-tool"
    handoff_tool_name: str = "handoff-tool"


@lru_cache
def get_agent_config() -> BasicAgentConfig:
    return BasicAgentConfig()

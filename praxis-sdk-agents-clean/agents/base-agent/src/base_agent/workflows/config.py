from functools import lru_cache

from pydantic_settings import BaseSettings


class BasicWorkflowConfig(BaseSettings):
    pass


@lru_cache
def get_workflow_config() -> BasicWorkflowConfig:
    return BasicWorkflowConfig()

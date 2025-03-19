from functools import lru_cache

from pydantic_settings import BaseSettings


class BasicWorkflowConfig(BaseSettings):
    RAY_MAX_RETRIES: int = 5  # Задаю дефолт так как мне кажется, что она не настолько динамическая


@lru_cache
def get_workflow_config() -> BasicWorkflowConfig:
    return BasicWorkflowConfig()

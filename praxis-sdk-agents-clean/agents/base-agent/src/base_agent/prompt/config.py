from functools import lru_cache
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings

from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def determine_template_path() -> str:
    # always exists
    candidate = get_entrypoint(EntrypointGroup.AGENT_ENTRYPOINT)
    pkg_path, _ = candidate.name.split(":", 1)

    # the templates should be in the root of the package
    return pkg_path.split(".")[0]


class BasicPromptConfig(BaseSettings):
    template_path: Annotated[str, Field(default_factory=determine_template_path)]
    template_dir: str = "templates"


@lru_cache
def get_prompt_config() -> BasicPromptConfig:
    return BasicPromptConfig()

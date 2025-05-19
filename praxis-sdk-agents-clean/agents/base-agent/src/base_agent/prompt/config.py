from functools import lru_cache
from typing import Annotated

from jinja2 import PackageLoader
from pydantic import Field
from pydantic_settings import BaseSettings

from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint


def determine_template_path(default_path="base_agent") -> str:
    # always exists
    candidate = get_entrypoint(EntrypointGroup.AGENT_ENTRYPOINT)
    pkg_path, _ = candidate.value.split(":", 1)

    # the templates should be in the root of the package
    package_name = pkg_path.split(".")[0]

    # try to load the package path
    try:
        PackageLoader(package_name=package_name)
    except ValueError:
        return default_path

    return package_name


class BasicPromptConfig(BaseSettings):
    template_path: Annotated[str, Field(default_factory=determine_template_path)]

    # GENERATE_PLAN
    generate_plan_template: str = "planner/generate_plan.txt.j2"
    generate_plan_examples_template: str = "planner/generate_plan_examples.txt.j2"

    # CHAT
    chat_template: str = "chatter/chat.txt.j2"

    # CLASSIFY_INTENT
    intent_classifier_template: str =  "intenter/classify_intent.txt.j2"
    intent_classifier_examples_template: str = "intenter/classify_intent.txt.j2"


    # SYSTEM PROMPT
    system_prompt_template: str = "system_prompt.txt.j2"



@lru_cache
def get_prompt_config() -> BasicPromptConfig:
    return BasicPromptConfig()

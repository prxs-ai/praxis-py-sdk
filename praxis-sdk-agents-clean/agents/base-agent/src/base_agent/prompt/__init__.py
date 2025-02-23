from base_agent.prompt.builder import PromptBuilder
from base_agent.prompt.config import get_prompt_config
from base_agent.prompt.utils import get_environment
from base_agent.utils import get_entrypoint


def prompt_builder(*args, **kwargs):
    # get the package name from the entrypoint
    config = get_prompt_config()
    entrypoint = get_entrypoint(config.group_name)
    package_name, _ = entrypoint.value.rsplit(":")

    return PromptBuilder(jinja2_env=get_environment(package_name))

from jinja2 import Environment
from langchain_core.prompts import PromptTemplate

from base_agent.prompt.config import BasicPromptConfig
from base_agent.prompt.const import END_OF_PLAN, FINISH_ACTION
from base_agent.prompt.utils import get_environment

GENERATE_PLAN_EXAMPLES_TEMPLATE_NAME = "planner/generate_plan_examples.txt.j2"
GENERATE_PLAN_TEMPLATE_NAME = "planner/generate_plan.txt.j2"


class PromptBuilder:
    def __init__(self, config: BasicPromptConfig, jinja2_env: Environment):
        self.config = config
        self.jinja2_env = jinja2_env

    def generate_plan_prompt(self, *args, **kwargs):
        template = self.jinja2_env.get_template(GENERATE_PLAN_TEMPLATE_NAME)
        examples = self.jinja2_env.get_template(GENERATE_PLAN_EXAMPLES_TEMPLATE_NAME)

        return PromptTemplate.from_template(
            template.render(
                finish_action=FINISH_ACTION,
                end_of_plan=END_OF_PLAN,
                examples=examples.render(finish_action=FINISH_ACTION, end_of_plan=END_OF_PLAN),
            ),
        )


def prompt_builder(config: BasicPromptConfig) -> PromptBuilder:
    return PromptBuilder(config, get_environment(config.template_path, config.template_dir))

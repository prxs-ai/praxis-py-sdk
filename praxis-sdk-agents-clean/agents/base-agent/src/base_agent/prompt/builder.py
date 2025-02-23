from jinja2 import Environment
from langchain_core.prompts import PromptTemplate

REACT_PROMPT_TEMPLATE_NAME = "react_prompt.txt.j2"
GENERATE_PLAN_TEMPLATE_NAME = "generate_plan.txt.j2"


OUTPUT_PLAN_EXAMPLE = """
api_version: 1
version: 0.0.1
name: example-pipeline
description: example pipeline
parameters:
  - name: example-param
    type: string
    default: example-value
steps:
  - name: example-step
    tool: example-tool
    inputs:
      - name: message
        value: "{{inputs.parameters.example-param}}"
    outputs:
      - name: example-output
  - name: example-step-2
    tool: example-tool
    dependencies: [example-tool]
    inputs:
      - name: message
        value: "{{steps.example-step.outputs.example-output}}"
    outputs:
     - name: example
outputs:
  - name: example-output
    value: "{{steps.example-step-2.outputs.example}}"
""".replace("{{", "{{{{").replace("}}", "}}}}")


class PromptBuilder:
    def __init__(self, jinja2_env: Environment):
        self.jinja2_env = jinja2_env

    # def generate_react_loop_prompt(self, *args, jinja2_placeholders: dict[str, str], **kwargs) -> PromptTemplate:
    #     template = self.jinja2_env.get_template(REACT_PROMPT_TEMPLATE_NAME)
    #     return PromptTemplate.from_template(template.render(jinja2_placeholders), *args, **kwargs)

    # def generate_react_prompt(self, *args, jinja2_placeholders: dict[str, str], **kwargs) -> PromptTemplate:
    #     template = self.jinja2_env.get_template(REACT_PROMPT_TEMPLATE_NAME)
    #     return PromptTemplate.from_template(template.render(jinja2_placeholders), *args, **kwargs)

    def generate_plan_prompt(self, *args, **kwargs):
        template = self.jinja2_env.get_template(GENERATE_PLAN_TEMPLATE_NAME)
        return PromptTemplate.from_template(
            template.render(output_plan_example=OUTPUT_PLAN_EXAMPLE),
        )

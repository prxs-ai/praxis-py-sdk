import re
from collections.abc import Sequence
from enum import Enum

import yaml
from langchain.agents.agent import AgentOutputParser
from langchain.schema import OutputParserException

from base_agent.models import InputItem, OutputItem, ParameterItem, ToolModel, Workflow, WorkflowStep


class RegexPattern(str, Enum):
    THOUGHT = r"Thought: ([^\n]*)"
    ACTION = r"\n*(\d+)\. (\w+)\((.*)\)(\s*#\w+\n)?"
    ID = r"\$\{?(\d+)\}?"
    YAML_PATTERN = r"```yaml\s+(.*?)\s+```"
    TEMPLATE_EXPR = r"\{\{(.*?)\}\}"


def default_dependency_rule(idx, args: str):
    matches = re.findall(RegexPattern.ID, args)
    numbers = [int(match) for match in matches]
    return idx in numbers


class AgentOutputPlanParser(AgentOutputParser, extra="allow"):
    """Planning output parser."""

    def __init__(self, tools: Sequence[ToolModel], **kwargs):
        super().__init__(**kwargs)
        self.tools = tools

    def parse(self, text: str) -> Workflow:
        # First try to extract YAML content
        yaml_match = re.search(RegexPattern.YAML_PATTERN, text, re.DOTALL)
        if not yaml_match:
            raise OutputParserException(f"Failed to parse YAML content from text: {text}")

        # If no YAML format found, fall back to the original parsing logic
        return self._parse_yaml_format(yaml_match.group(1))

    def _parse_yaml_format(self, yaml_content: str) -> Workflow:
        try:
            # Handle template expressions by temporarily replacing them
            template_expressions = {}

            def replace_template(match):
                placeholder = f"__TEMPLATE_{len(template_expressions)}__"
                template_expressions[placeholder] = match.group(0)
                return placeholder

            processed_content = re.sub(r"\{\{(.*?)\}\}", replace_template, yaml_content)

            # Parse YAML content
            workflow_data = yaml.safe_load(processed_content)

            # Convert back the template expressions
            def restore_templates(obj):
                if isinstance(obj, str):
                    for placeholder, template in template_expressions.items():
                        if placeholder in obj:
                            obj = obj.replace(placeholder, template)
                    return obj
                elif isinstance(obj, list):
                    return [restore_templates(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: restore_templates(v) for k, v in obj.items()}
                return obj

            workflow_data = restore_templates(workflow_data)

            # Convert to Workflow model
            workflow = Workflow(
                name=workflow_data.get("name", "unnamed_workflow"),
                description=workflow_data.get("description", ""),
                thought=workflow_data.get("thought", ""),
                steps=[
                    WorkflowStep(
                        name=step.get("name", f"step_{i}"),
                        # should pick only the defined tools
                        tool=_find_tool(step.get("tool", ""), self.tools),
                        thought=step.get("thought", ""),
                        parameters=self._parse_parameters(step.get("parameters", [])),
                        inputs=self._parse_inputs(step.get("inputs", [])),
                        outputs=[
                            OutputItem(name=output_item.get("name", ""), value=output_item.get("value", None))
                            for output_item in step.get("outputs", [])
                        ],
                    )
                    for i, step in enumerate(workflow_data.get("steps", []))
                ],
                outputs=[
                    OutputItem(name=output_item.get("name", ""), value=output_item.get("value", None))
                    for output_item in workflow_data.get("outputs", [])
                ],
            )
            return workflow

        except yaml.YAMLError as e:
            raise OutputParserException(f"Failed to parse YAML content: {e}") from e


    def _parse_parameters(self, params: list | dict) -> list:
        if isinstance(params, dict):
            return [ParameterItem(name=name, value=value) for name, value in params.items()]
        else:
            return [
                ParameterItem(name=input_item.get("name", ""), value=input_item.get("value", ""))
                for input_item in params
            ]

    def _parse_inputs(self, inputs: list | dict) -> list:
        if isinstance(inputs, dict):
            return [InputItem(name=name, value=value) for name, value in inputs.items()]
        else:
            return [
                InputItem(name=input_item.get("name", ""), value=input_item.get("value", ""))
                for input_item in inputs
            ]


### Helper functions


def _find_tool(tool_name: str, tools: Sequence[ToolModel]) -> ToolModel:
    """Find a tool by name.

    Args:
        tool_name: Name of the tool to find.

    Returns:
        Tool or StructuredTool.
    """
    for tool in tools:
        if tool.package_name == tool_name or tool.function_name == tool_name:
            return tool
    raise OutputParserException(f"Tool {tool_name} not found.")

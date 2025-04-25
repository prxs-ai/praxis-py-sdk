import ast
import re
from collections.abc import Sequence
from typing import Any

import yaml
from langchain.agents.agent import AgentOutputParser
from langchain.schema import OutputParserException

from base_agent.models import InputItem, OutputItem, Task, ToolModel, Workflow, WorkflowStep
from base_agent.prompt.const import FINISH_ACTION

THOUGHT_PATTERN = r"Thought: ([^\n]*)"
ACTION_PATTERN = r"\n*(\d+)\. (\w+)\((.*)\)(\s*#\w+\n)?"
# $1 or ${1} -> 1
ID_PATTERN = r"\$\{?(\d+)\}?"
# Pattern to extract YAML content between ```yaml and ``` markers
YAML_PATTERN = r"```yaml\s+(.*?)\s+```"
# Pattern for template expressions like {{steps.step-name.outputs.output-name}}
TEMPLATE_EXPR_PATTERN = r"\{\{(.*?)\}\}"


def default_dependency_rule(idx, args: str):
    matches = re.findall(ID_PATTERN, args)
    numbers = [int(match) for match in matches]
    return idx in numbers


class AgentOutputPlanParser(AgentOutputParser, extra="allow"):
    """Planning output parser."""

    def __init__(self, tools: Sequence[ToolModel], **kwargs):
        super().__init__(**kwargs)
        self.tools = tools

    def parse(self, text: str) -> Workflow:
        # First try to extract YAML content
        yaml_match = re.search(YAML_PATTERN, text, re.DOTALL)
        if not yaml_match:
            raise OutputParserException(f"Failed to parse YAML content from text: {text}")

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
                        tool=step.get("tool", ""),
                        thought=step.get("thought", ""),
                        inputs=[
                            InputItem(name=input_item.get("name", ""), value=input_item.get("value", ""))
                            for input_item in step.get("inputs", [])
                        ],
                        outputs=[
                            OutputItem(name=output_item.get("name", ""), value=output_item.get("value", None))
                            for output_item in step.get("outputs", [])
                        ],
                        task = instantiate_task(
                            tools=self.tools,
                            idx=i,
                            tool_name=step.get("tool", ""),
                            args=step.get("inputs", []),
                            thought=step.get("thought", ""),
                        )
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
        except Exception as e:
            raise OutputParserException(f"Failed to parse workflow: {e}") from e

### Helper functions


def _parse_llm_compiler_action_args(args: str) -> list[Any]:
    """Parse arguments from a string."""
    # This will convert the string into a python object
    # e.g. '"Ronaldo number of kids"' -> ("Ronaldo number of kids", )
    # '"I can answer the question now.", [3]' -> ("I can answer the question now.", [3])
    if args == "":
        return ()
    try:
        args = ast.literal_eval(args)
    except:  # noqa: E722
        args = args
    if not isinstance(args, list) and not isinstance(args, tuple):
        args = (args,)
    return args


def _find_tool(tool_name: str, tools: Sequence[ToolModel]) -> ToolModel:
    """Find a tool by name.

    Args:
        tool_name: Name of the tool to find.

    Returns:
        Tool or StructuredTool.
    """
    for tool in tools:
        if tool.function_name == tool_name:
            return tool
    raise OutputParserException(f"Tool {tool_name} not found.")


def _get_dependencies_from_graph(idx: int, tool_name: str, args: Sequence[Any]) -> list[int]:
    """Get dependencies from a graph."""
    if tool_name == FINISH_ACTION:
        # depends on the previous step
        dependencies = list(range(1, idx))
    else:
        # define dependencies based on the dependency rule in tool_definitions.py
        dependencies = [i for i in range(1, idx) if default_dependency_rule(i, args)]

    return dependencies


def instantiate_task(
    tools: Sequence[ToolModel],
    idx: int,
    tool_name: str,
    args: list[Any],
    thought: str,
) -> Task:
    return Task(
        idx=idx,
        name=tool_name,
        tool=_find_tool(tool_name, tools),
        args=args,
        thought=thought,
        is_finish=tool_name == FINISH_ACTION,
    )

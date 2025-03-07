import ast
import re
from collections.abc import Sequence
from typing import Any

import yaml
from langchain.agents.agent import AgentOutputParser
from langchain.schema import OutputParserException

from base_agent.models import Task, ToolModel
from base_agent.prompt.const import FINISH_ACTION

THOUGHT_PATTERN = r"Thought: ([^\n]*)"
ACTION_PATTERN = r"\n*(\d+)\. (\w+)\((.*)\)(\s*#\w+\n)?"
# $1 or ${1} -> 1
ID_PATTERN = r"\$\{?(\d+)\}?"
# Pattern to extract YAML content between ```yaml and ``` markers
YAML_PATTERN = r"```yaml\s+(.*?)\s+```"


def default_dependency_rule(idx, args: str):
    matches = re.findall(ID_PATTERN, args)
    numbers = [int(match) for match in matches]
    return idx in numbers


class AgentOutputPlanParser(AgentOutputParser, extra="allow"):
    """Planning output parser."""

    def __init__(self, tools: Sequence[ToolModel], **kwargs):
        super().__init__(**kwargs)
        self.tools = tools

    def parse(self, text: str) -> dict[int, Task]:
        # First try to extract YAML content
        yaml_match = re.search(YAML_PATTERN, text, re.DOTALL)
        if yaml_match:
            return self._parse_yaml_format(yaml_match.group(1))

        # If no YAML format found, fall back to the original parsing logic
        return self._parse_numbered_format(text)

    def _parse_yaml_format(self, yaml_content: str) -> dict[int, Task]:
        try:
            # Pre-process the YAML content to escape curly braces in template expressions
            # Convert {{...}} to a string that won't be interpreted as a mapping
            processed_content = re.sub(r"\{\{(.*?)\}\}", r'"{{$1}}"', yaml_content)

            plan_data = yaml.safe_load(processed_content)
            graph_dict = {}

            # Process each step in the plan
            for idx, step in enumerate(plan_data.get("steps", [])):
                tool_name = step.get("tool")

                # Extract inputs as arguments
                inputs = step.get("inputs", [])
                args_dict = {
                    input_item.get("name"): input_item.get("value")
                    for input_item in inputs
                    if "name" in input_item and "value" in input_item
                }

                # Convert to a format the existing function can handle
                args_str = str(args_dict) if args_dict else ""

                task = instantiate_task(
                    tools=self.tools,
                    idx=idx,
                    tool_name=tool_name,
                    args=args_str,
                    thought=step.get("thought", plan_data.get("description", "")),
                )

                graph_dict[idx] = task

            idx = len(graph_dict)

            # The last step is implicitly a finish action
            finish_task = instantiate_task(
                tools=self.tools,
                idx=idx + 1,
                tool_name=FINISH_ACTION,
                args=str(plan_data.get("outputs", [])),
                thought=f"Completed all steps in the plan for: {plan_data.get('name', 'unknown')}",
            )
            graph_dict[idx + 1] = finish_task

            return graph_dict

        except yaml.YAMLError as e:
            raise OutputParserException(f"Failed to parse YAML content: {e}") from e

    def _parse_numbered_format(self, text: str) -> dict[int, Task]:
        # Original parsing logic for numbered steps
        pattern = rf"(?:{THOUGHT_PATTERN}\n)?{ACTION_PATTERN}"
        matches = re.findall(pattern, text)

        graph_dict = {}

        for match in matches:
            # idx = 1, function = "search", args = "Ronaldo number of kids"
            # thought will be the preceding thought, if any, otherwise an empty string
            thought, idx, tool_name, args, _ = match
            idx = int(idx)

            task = instantiate_task(
                tools=self.tools,
                idx=idx,
                tool_name=tool_name,
                args=args,
                thought=thought,
            )

            graph_dict[idx] = task
            if task.is_finish:
                break

        return graph_dict


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
    except:
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
    args: str,
    thought: str,
) -> Task:
    dependencies = _get_dependencies_from_graph(idx, tool_name, args)
    args = _parse_llm_compiler_action_args(args)

    tool = _find_tool(tool_name, tools)

    return Task(
        idx=idx,
        name=tool_name,
        tool=tool,
        args=args,
        dependencies=dependencies,
        thought=thought,
        is_finish=tool_name == FINISH_ACTION,
    )

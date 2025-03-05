from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from base_agent.utils import default_stringify_rule_for_arguments


class ToolModel(BaseModel):
    name: str
    version: str
    openai_function_spec: dict[str, Any]

    @property
    def function_name(self) -> str:
        return self.openai_function_spec["function"]["name"]

    def render_openai_function_spec(self) -> str:
        return f"""
- {self.openai_function_spec["function"]["name"]}
    - description: {self.openai_function_spec["function"]["description"]}
    - parameters: {self.openai_function_spec["function"]["parameters"]}
"""


class AgentModel(BaseModel):
    name: str
    description: str
    version: str


class GoalModel(BaseModel):
    goal: str = Field(..., description="Goal to reach")


@dataclass
class Task:
    idx: int
    name: str
    tool: ToolModel
    args: Collection[Any]
    dependencies: Collection[int]
    thought: str | None = None
    observation: str | None = None
    is_finish: bool = False

    @property
    def task_id(self) -> str:
        return f"{self.idx}:{self.name}"

    def get_thought_action_observation(
        self, include_action=True, include_thought=True, include_action_idx=False
    ) -> str:
        thought_action_observation = ""
        if self.thought and include_thought:
            thought_action_observation = f"Thought: {self.thought}\n"
        if include_action:
            idx = f"{self.idx}. " if include_action_idx else ""

            thought_action_observation += f"{idx}{self.name}{default_stringify_rule_for_arguments(self.args)}\n"
        if self.observation is not None:
            thought_action_observation += f"Observation: {self.observation}\n"
        return thought_action_observation

    @staticmethod
    def _replace_arg_mask_with_real_value(args, dependencies: list[int], tasks: dict[str, "Task"]):
        if isinstance(args, (list, tuple)):
            return type(args)(Task._replace_arg_mask_with_real_value(item, dependencies, tasks) for item in args)
        elif isinstance(args, str):
            for dependency in sorted(dependencies, reverse=True):
                # consider both ${1} and $1 (in case planner makes a mistake)
                for arg_mask in ["${" + str(dependency) + "}", "$" + str(dependency)]:
                    if arg_mask in args:
                        if tasks[dependency].observation is not None:
                            args = args.replace(arg_mask, str(tasks[dependency].observation))
            return args
        else:
            return args

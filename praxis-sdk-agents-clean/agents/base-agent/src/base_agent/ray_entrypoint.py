from collections.abc import Sequence
from typing import Any
from urllib.parse import urljoin

import requests

from base_agent import abc
from base_agent.bootstrap import bootstrap_main
from base_agent.config import BasicAgentConfig, get_agent_config
from base_agent.langchain import executor_builder
from base_agent.models import AgentModel, Task, ToolModel
from base_agent.prompt import prompt_builder
from base_agent.workflows import workflow_builder


class BaseAgent(abc.AbstractAgent):
    """Base default implementation for all agents."""

    workflow_runner: abc.AbstractWorkflowRunner
    prompt_builder: abc.AbstractPromptBuilder
    agent_executor: abc.AbstractExecutor

    def __init__(self, config: BasicAgentConfig, *args, **kwargs):
        self.config = config
        self.workflow_runner = workflow_builder()
        self.agent_executor = executor_builder()
        self.prompt_builder = prompt_builder()

    async def handle(self, goal: str, plan: dict | None = None):
        """This is one of the most important endpoint of MAS.
        It handles all requests made by handoff from other agents or by user."""

        agents = self.get_most_relevant_agents(goal)
        tools = self.get_most_relevant_tools(goal)

        plan = self.generate_plan(goal, agents, tools, plan)

        return self.run_workflow(plan)

    def get_most_relevant_agents(self, goal: str) -> list[AgentModel]:
        """This method is used to find the most useful agents for the given goal."""
        return []

    def get_most_relevant_tools(self, goal: str) -> list[ToolModel]:
        """This method is used to find the most useful tools for the given goal."""
        return [
            ToolModel(
                name="handoff-tool",
                version="0.1.0",
                openai_function_spec={
                    "type": "function",
                    "function": {
                        "name": "handoff_tool",
                        "description": "A tool that returns the string passed in as an output.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "agent": {"type": "string", "description": "The name of the agent to use.", "enum": []},
                                "goal": {"type": "string", "description": "The goal to achieve."},
                            },
                            "required": ["agent", "goal"],
                        },
                        "output": {
                            "type": "object",
                            "properties": {
                                "result": {"type": "string", "description": "The result returned by the agent."}
                            },
                        },
                    },
                },
            ),
            ToolModel(
                name="return-answer-tool",
                version="0.1.2",
                openai_function_spec={
                    "type": "function",
                    "function": {
                        "name": "return_answer_tool",
                        "description": "Returns the input as output.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "answer": {
                                    "type": "string",
                                    "description": "The answer in JSON string.",
                                    "default": '{"result": 42}',
                                }
                            },
                            "required": ["answer"],
                        },
                        "output": {
                            "type": "object",
                            "properties": {
                                "result": {
                                    "type": "string",
                                    "description": "Returns the input as output in JSON string.",
                                }
                            },
                        },
                    },
                },
            ),
        ]

    def generate_plan(
        self, goal: str, agents: Sequence[AgentModel], tools: Sequence[ToolModel], plan: dict | None = None
    ):
        """This method is used to generate a plan for the given goal."""
        return self.agent_executor.generate_plan(
            self.prompt_builder.generate_plan_prompt(system_prompt=self.config.system_prompt),
            available_functions=tools,
            available_agents=agents,
            goal=goal,
        )

    def run_workflow(self, plan: dict[int, Task]):
        return self.workflow_runner.run(plan)

    def reconfigure(self, config: dict[str, Any]):
        pass

    async def handoff(self, endpoint: str, goal: str, plan: dict):
        """This method means that agent can't find a solution (wrong route/wrong plan/etc)
        and decide to handoff the task to another agent."""
        return requests.post(urljoin(endpoint, goal), json=plan).json()


def agent_builder(args: dict):
    return bootstrap_main(BaseAgent).bind(config=get_agent_config(**args))

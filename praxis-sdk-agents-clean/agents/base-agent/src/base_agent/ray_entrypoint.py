from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urljoin

import requests
from fastapi import FastAPI

from base_agent.config import get_agent_config
from base_agent.langchain import agent_executor
from base_agent.langchain.executor import LangChainExecutor
from base_agent.models import AgentModel, Task, ToolModel
from base_agent.prompt import prompt_builder
from base_agent.prompt.builder import PromptBuilder
from base_agent.workflows.runner import dag_runner


class BaseAgent:
    prompt_builder: PromptBuilder
    agent_executor: LangChainExecutor

    def __init__(self, *args, **kwargs):
        self.config = get_agent_config()
        self.dag_runner = dag_runner()
        self.agent_executor = agent_executor()
        self.prompt_builder = prompt_builder()

    def handle(self, goal: str, plan: dict | None = None):
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
                version="0.0.1",
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
                }
            ),
            ToolModel(
                name="return-answer-tool",
                version="0.0.1",
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
        prompt = self.prompt_builder.generate_plan_prompt(
            final_answer_tool_name=self.config.final_answer_tool_name,
            # handoff_tool_name=self.config.handoff_tool_name
        )

        return self.agent_executor.generate_plan(
            prompt,
            available_functions=tools,
            available_agents=agents,
            goal=goal,
        )

    def run_workflow(self, plan: dict[int, Task]):
        return self.dag_runner.run(plan)

    def reconfigure(self, config: dict[str, Any]):
        pass

    def handoff(self, endpoint: str, goal: str, plan: dict):
        """This method means that agent can't find a solution (wrong route/wrong plan/etc)
        and decide to handoff the task to another agent."""
        return requests.post(urljoin(endpoint, goal), json=plan).json()


def agent_builder(args: dict):
    from ray import serve

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # launch some tasks on app start
        yield
        # handle clean up

    app = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(app)
    class Agent(BaseAgent):
        @app.post("/{goal}")
        async def handle(self, goal: str, plan: dict | None = None):
            return super().handle(goal, plan)

    return Agent.bind(**args)

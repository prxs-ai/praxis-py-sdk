from collections.abc import Sequence
from typing import Any
from urllib.parse import urljoin

import requests

from base_agent import abc
from base_agent.ai_registry import ai_registry_builder
from base_agent.bootstrap import bootstrap_main
from base_agent.config import BasicAgentConfig, get_agent_config
from base_agent.domain_knowledge import light_rag_builder
from base_agent.langchain import executor_builder
from base_agent.memory import memory_builder
from base_agent.models import AgentModel, GoalModel, InsightModel, MemoryModel, QueryData, Task, ToolModel
from base_agent.prompt import prompt_builder
from base_agent.workflows import workflow_builder


class BaseAgentInputModel(abc.AbstractAgentInputModel): ...


class BaseAgentOutputModel(abc.AbstractAgentOutputModel): ...


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

        # ---------- AI Registry ----------#
        self.ai_registry_client = ai_registry_builder()

        # ---------- LightRAG Memory -------#
        self.lightrag_client = light_rag_builder()

        # ---------- Redis Memory ----------#
        self.memory_client = memory_builder()

    async def handle(
        self,
        goal: str,
        plan: dict | None = None,
        context: BaseAgentInputModel | None = None,
    ) -> BaseAgentOutputModel:
        """This is one of the most important endpoints of MAS.
        It handles all requests made by handoff from other agents or by user.

        If a predefined plan is provided, it skips plan generation and executes the plan directly.
        Otherwise, it follows the standard logic to generate a plan and execute it.
        """

        if plan is not None:
            result = self.run_workflow(plan, context)
            self.store_interaction(goal, plan, result, context)
            return result

        insights = self.get_relevant_insights(goal)
        past_interactions = self.get_past_interactions(goal)
        agents = self.get_most_relevant_agents(goal)
        tools = self.get_most_relevant_tools(goal)

        plan = self.generate_plan(
            goal=goal,
            agents=agents,
            tools=tools,
            insights=insights,
            past_interactions=past_interactions,
            plan=None,
        )

        result = self.run_workflow(plan, context)
        self.store_interaction(goal, plan, result, context)
        return result

    def get_past_interactions(self, goal: str) -> list[dict]:
        return self.memory_client.read(key=goal)

    def store_interaction(
        self,
        goal: str,
        plan: dict,
        result: BaseAgentOutputModel,
        context: BaseAgentInputModel | None = None,
    ) -> None:
        interaction = MemoryModel(
            **{
                "goal": goal,
                "plan": plan,
                "result": result.model_dump(),
                "context": context.model_dump(),
            }
        )
        self.memory_client.store(key=goal, interaction=interaction.model_dump())

    def get_relevant_insights(self, goal: str) -> list[InsightModel]:
        """Retrieve relevant insights from LightRAG memory for the given goal."""
        response = self.lightrag_client.get(endpoint=self.lightrag_client.endpoints.query, params={"query": goal})

        matches = response.get("matches", [])
        return [InsightModel(domain_knowledge=match["text"]) for match in matches if "text" in match]

    def get_most_relevant_agents(self, goal: str) -> list[AgentModel]:
        """This method is used to find the most useful agents for the given goal."""
        response = self.ai_registry_client.post(
            endpoint=self.ai_registry_client.endpoints.find_agents,
            json=QueryData(goal=goal).model_dump(),
        )

        if not response:
            return []

        return [AgentModel(**agent) for agent in response]

    def get_most_relevant_tools(self, goal: str) -> list[ToolModel]:
        """
        This method is used to find the most useful tools for the given goal.

        Example:

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
        """
        response = self.ai_registry_client.post(
            endpoint=self.ai_registry_client.endpoints.find_tools,
            json=GoalModel(goal=goal).model_dump(),
        )

        if not response:
            return []

        return [ToolModel(**tool) for tool in response]

    def generate_plan(
        self,
        goal: str,
        agents: Sequence[AgentModel],
        tools: Sequence[ToolModel],
        past_interactions: Sequence[MemoryModel],
        insights: Sequence[InsightModel],
        plan: dict | None = None,
    ):
        """This method is used to generate a plan for the given goal."""
        return self.agent_executor.generate_plan(
            self.prompt_builder.generate_plan_prompt(system_prompt=self.config.system_prompt),
            available_functions=tools,
            available_agents=agents,
            goal=goal,
            past_interactions=past_interactions,
            insights=insights,
            plan=plan,
        )

    def run_workflow(
        self,
        plan: dict[int, Task],
        context: BaseAgentInputModel | None = None,
    ) -> BaseAgentOutputModel:
        return self.workflow_runner.run(plan, context)

    def reconfigure(self, config: dict[str, Any]):
        pass

    async def handoff(self, endpoint: str, goal: str, plan: dict):
        """This method means that agent can't find a solution (wrong route/wrong plan/etc)
        and decide to handoff the task to another agent."""
        return requests.post(urljoin(endpoint, goal), json=plan).json()


def agent_builder(args: dict):
    return bootstrap_main(BaseAgent).bind(config=get_agent_config(**args))

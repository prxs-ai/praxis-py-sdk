import datetime
import uuid
from collections.abc import Sequence
from typing import Any
from urllib.parse import urljoin

import requests

from base_agent import abc, const
from base_agent.ai_registry import ai_registry_builder
from base_agent.bootstrap import bootstrap_main
from base_agent.config import BasicAgentConfig, get_agent_config
from base_agent.domain_knowledge import light_rag_builder
from base_agent.langchain import executor, executor_builder
from base_agent.memory import memory_builder
from base_agent.models import (
    AgentModel,
    ChatMessageModel,
    GoalModel,
    InsightModel,
    MemoryModel,
    Task,
    ToolModel,
)
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
        if isinstance(plan, dict) and plan and all(isinstance(v, Task) for v in plan.values()):
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
                "context": context.model_dump() if context else None,
            }
        )
        self.memory_client.store(key=goal, interaction=interaction.model_dump())

    def store_chat_context(
        self,
        uuid: str,
        messages: list[dict],
    ) -> None:
        normalized_messages = [msg if isinstance(msg, dict) else msg.model_dump() for msg in messages]
        self.memory_client.store(key=f"chat:{uuid}", interaction=normalized_messages)

    def get_chat_context(self, uuid: str) -> list[dict]:
        results = self.memory_client.read(key=f"chat:{uuid}").get("results")
        print(f"Fetched {len(results)} results")
        return results

    def get_relevant_insights(self, goal: str) -> list[InsightModel]:
        """Retrieve relevant insights from LightRAG memory for the given goal."""
        response = self.lightrag_client.post(
            endpoint=self.lightrag_client.endpoints.query,
            json={
                "query": goal,
                "mode": "naive",
            },
        )
        texts = response.get("texts", [])
        return [InsightModel(domain_knowledge=text["text"]) for text in texts if "text" in text]

    def store_knowledge(self, filename: str | None, content: str) -> dict:
        data = {"content": content}
        if filename:
            data["filename"] = filename

        return self.lightrag_client.post(
            endpoint=self.lightrag_client.endpoints.insert,
            json=data,
        )

    def get_most_relevant_agents(self, goal: str) -> list[AgentModel]:
        """This method is used to find the most useful agents for the given goal."""
        response = self.ai_registry_client.post(
            endpoint=self.ai_registry_client.endpoints.find_agents,
            json=GoalModel(goal=goal).model_dump(),
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
    ) -> dict[int, Task]:
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

    def chat(
        self,
        user_prompt: str,
        action: str | None,
        session_uuid: str | None = None,
    ) -> executor.ChatResponse:
        if not session_uuid:
            session_uuid = str(uuid.uuid4())

        prior_context = self.get_chat_context(session_uuid)
        chat_history = [
            ChatMessageModel(role="user", content=m.get("memory", ""), timestamp=m.get("created_at"))
            for m in prior_context
        ]

        chat_history.append(
            ChatMessageModel(
                role="user",
                content=user_prompt,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
        )

        self.store_chat_context(session_uuid, chat_history)

        # ------ Reconfigure Agent ----- #
        if action == const.Intents.CHANGE_SETTINGS:
            existing_config = str(self.config)
            print(f"Current config: {existing_config}")

            updated_config = self.agent_executor.reconfigure(
                prompt=self.prompt_builder.generate_reconfigure_prompt(
                    system_prompt=self.config.system_prompt,
                    user_prompt=user_prompt,
                    existing_config=existing_config,
                ),
                user_message=user_prompt,
                existing_config=existing_config,
                system_prompt=self.config.system_prompt,
            )

            if updated_config:
                print(f"Updated config: {updated_config}")
                self.reconfigure(updated_config)
                response = executor.ChatResponse(
                    response_text="Settings updated successfully.",
                    action=None,
                    session_uuid=session_uuid,
                )
            else:
                response = executor.ChatResponse(
                    response_text="Sorry, I couldn't parse the settings you want to change. Please try again.",
                    action=const.Intents.CHANGE_SETTINGS,
                    session_uuid=session_uuid,
                )
            chat_history.append(
                ChatMessageModel(
                    role="assistant",
                    content=response.response_text,
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
            )
            self.store_chat_context(session_uuid, chat_history)
            return response

        # ------ Add Knowledge to Knowledge Base ----- #
        if action == const.Intents.ADD_KNOWLEDGE:
            print(f"Trying to add to knowledge base: {user_prompt}")
            result: dict = self.store_knowledge(filename=None, content=user_prompt)

            # Default message
            response_text = "I failed to add information to the knowledge base."
            if result and result.get("status") and result["status"] == "success":
                response_text = "Information added to the knowledge base."

            response = executor.ChatResponse(
                response_text=response_text,
                action=None,
                session_uuid=session_uuid,
            )
            chat_history.append(
                ChatMessageModel(
                    role="assistant",
                    content=response.response_text,
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
            )
            self.store_chat_context(session_uuid, chat_history)
            return response

        # ------ Classify Intent ----- #
        if action is None:
            intent = self.agent_executor.classify_intent(
                prompt=self.prompt_builder.generate_intent_classifier_prompt(
                    system_prompt=self.config.system_prompt,
                    user_prompt=user_prompt,
                ),
                user_message=user_prompt,
                context=[m.content for m in chat_history],
            )
            if intent == const.Intents.CHANGE_SETTINGS:
                print(f"Intent: {intent}")
                response = executor.ChatResponse(
                    response_text=const.ExtraQuestions.WHICH_SETTINGS,
                    action=const.Intents.CHANGE_SETTINGS,
                    session_uuid=session_uuid,
                )
                chat_history.append(
                    ChatMessageModel(
                        role="assistant",
                        content=response.response_text,
                        timestamp=datetime.datetime.now(datetime.timezone.utc),
                    )
                )
                self.store_chat_context(session_uuid, chat_history)
                return response

            if intent == const.Intents.ADD_KNOWLEDGE:
                print(f"Intent: {intent}")
                response = executor.ChatResponse(
                    response_text=const.ExtraQuestions.WHAT_INFO,
                    action=const.Intents.ADD_KNOWLEDGE,
                    session_uuid=session_uuid,
                )
                chat_history.append(
                    ChatMessageModel(
                        role="assistant",
                        content=response.response_text,
                        timestamp=datetime.datetime.now(datetime.timezone.utc),
                    )
                )
                self.store_chat_context(session_uuid, chat_history)
                return response

        # ------ Chit Chat ----- #
        print(f"Intent: {const.Intents.CHIT_CHAT}")
        chat_context_str = "\n".join([m.content for m in chat_history[-10:]]) if chat_history else ""
        assistant_reply = self.agent_executor.chat(
            prompt=self.prompt_builder.generate_chat_prompt(
                system_prompt=self.config.system_prompt,
                user_prompt=user_prompt,
                context=chat_context_str,
            ),
            user_message=user_prompt,
            context=chat_context_str,
        )
        response = executor.ChatResponse(
            response_text=assistant_reply,
            action=const.Intents.CHIT_CHAT,
            session_uuid=session_uuid,
        )
        chat_history.append(
            ChatMessageModel(
                role="assistant",
                content=response.response_text,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
        )
        self.store_chat_context(session_uuid, chat_history)
        return response

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

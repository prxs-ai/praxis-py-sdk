import datetime
from unittest.mock import MagicMock, patch

import pytest

import base_agent.ray_entrypoint as ray_entrypoint
from base_agent.config import BasicAgentConfig
from base_agent.const import ExtraQuestions, Intents
from base_agent.models import AgentModel, InsightModel


class TestBaseAgent:
    @pytest.fixture(autouse=True)
    def setup_agent(self):
        # Patch all external dependencies at the class level for all tests
        with (
            patch.object(ray_entrypoint, "executor_builder") as mock_executor_builder,
            patch.object(ray_entrypoint, "prompt_builder") as mock_prompt_builder,
            patch.object(ray_entrypoint, "ai_registry_builder") as mock_ai_registry_builder,
            patch.object(ray_entrypoint, "light_rag_builder") as mock_lightrag_builder,
            patch.object(ray_entrypoint, "memory_builder") as mock_memory_builder,
        ):
            self.mock_executor = MagicMock()
            self.mock_prompt = MagicMock()
            self.mock_ai_registry = MagicMock()
            self.mock_lightrag = MagicMock()
            self.mock_memory = MagicMock()

            mock_executor_builder.return_value = self.mock_executor
            mock_prompt_builder.return_value = self.mock_prompt
            mock_ai_registry_builder.return_value = self.mock_ai_registry
            mock_lightrag_builder.return_value = self.mock_lightrag
            mock_memory_builder.return_value = self.mock_memory

            config = BasicAgentConfig()
            self.agent = ray_entrypoint.BaseAgent(config)
            yield

    def test_get_past_interactions(self):
        self.mock_memory.read.return_value = [{"foo": "bar"}]
        result = self.agent.get_past_interactions("some_goal")
        assert result == [{"foo": "bar"}]
        self.mock_memory.read.assert_called_with(key="some_goal")

    def test_store_interaction(self):
        goal = "my_goal"
        plan = {"step": 1}
        result = MagicMock()
        context = MagicMock()
        result.model_dump.return_value = {"result": 123}
        context.model_dump.return_value = {"foo": "bar"}

        self.agent.store_interaction(goal, plan, result, context)
        args, kwargs = self.mock_memory.store.call_args
        stored = kwargs["interaction"] if "interaction" in kwargs else args[1]
        assert stored["goal"] == goal
        assert stored["plan"] == plan
        assert stored["result"] == {"result": 123}
        assert stored["context"] == {"foo": "bar"}

    def test_get_relevant_insights(self):
        self.mock_lightrag.post.return_value = {"texts": [{"text": "insight1"}, {"text": "insight2"}]}
        insights = self.agent.get_relevant_insights("goal")
        assert isinstance(insights[0], InsightModel)
        assert insights[0].domain_knowledge == "insight1"

    def test_store_knowledge(self):
        self.mock_lightrag.post.return_value = {"status": "success"}
        result = self.agent.store_knowledge("file.txt", "content")
        assert result == {"status": "success"}
        self.mock_lightrag.post.assert_called_once()

    def test_get_most_relevant_agents(self):
        self.mock_ai_registry.post.return_value = [{"name": "agent1", "description": "desc", "version": "1.0.0"}]
        agents = self.agent.get_most_relevant_agents("goal")
        assert isinstance(agents[0], AgentModel)
        assert agents[0].name == "agent1"

    @patch("base_agent.ray_entrypoint.requests.get")
    def test_get_most_relevant_tools(self, mock_requests_get):
        agent_data = AgentModel(name="agent1", description="desc", version="1.0.0")
        self.mock_ai_registry.post.return_value = [
            {
                "name": "tool1",
                "openai_function_spec": {
                    "function": {"name": "foo", "description": "bar", "parameters": {}, "output": {}}
                },
            }
        ]
        mock_requests_get.return_value.json.return_value = {"skills": []}
        mock_requests_get.return_value.raise_for_status = MagicMock()

        tools = self.agent.get_most_relevant_tools("goal", [agent_data])
        assert isinstance(tools, list)
        assert any(t.name == "return-answer-tool" for t in tools)

    def test_generate_plan(self):
        self.mock_executor.generate_plan.return_value = "workflow"
        plan = self.agent.generate_plan("goal", [], [], [], [])
        self.mock_executor.generate_plan.assert_called_once()
        assert plan == "workflow"

    def test_chat_chitchat(self):
        self.mock_executor.classify_intent.return_value = Intents.CHIT_CHAT
        self.mock_executor.chat.return_value = "Hello!"
        self.mock_prompt.generate_intent_classifier_prompt.return_value = "intent_prompt"
        self.mock_prompt.generate_chat_prompt.return_value = "chat_prompt"

        # Make sure chat context returns empty so a new message is added
        self.mock_memory.read.return_value = {"results": []}
        self.mock_memory.store = MagicMock()

        resp = self.agent.chat("Hi!", None)
        assert resp.response_text == "Hello!"
        assert resp.action == Intents.CHIT_CHAT

    def test_chat_change_settings(self):
        self.mock_executor.classify_intent.return_value = Intents.CHANGE_SETTINGS
        self.mock_prompt.generate_intent_classifier_prompt.return_value = "intent_prompt"
        self.mock_memory.read.return_value = {"results": []}
        self.mock_memory.store = MagicMock()

        resp = self.agent.chat("Change settings", None)
        assert resp.response_text == ExtraQuestions.WHICH_SETTINGS
        assert resp.action == Intents.CHANGE_SETTINGS

    def test_chat_add_knowledge(self):
        self.mock_executor.classify_intent.return_value = Intents.ADD_KNOWLEDGE
        self.mock_prompt.generate_intent_classifier_prompt.return_value = "intent_prompt"
        self.mock_memory.read.return_value = {"results": []}
        self.mock_memory.store = MagicMock()

        resp = self.agent.chat("Add this info", None)
        assert resp.response_text == ExtraQuestions.WHAT_INFO
        assert resp.action == Intents.ADD_KNOWLEDGE

    def test_chat_action_add_knowledge_success(self):
        self.mock_memory.read.return_value = {"results": []}
        self.mock_memory.store = MagicMock()
        self.mock_lightrag.post.return_value = {"status": "success"}

        resp = self.agent.chat("Some info", Intents.ADD_KNOWLEDGE)
        assert resp.response_text == "Information added to the knowledge base."
        assert resp.action is None

    def test_chat_action_add_knowledge_fail(self):
        self.mock_memory.read.return_value = {"results": []}
        self.mock_memory.store = MagicMock()
        self.mock_lightrag.post.return_value = {"status": "error"}

        resp = self.agent.chat("Some info", Intents.ADD_KNOWLEDGE)
        assert "failed" in resp.response_text.lower()

    def test_chat_action_change_settings(self):
        self.mock_memory.read.return_value = {"results": []}
        self.mock_memory.store = MagicMock()
        self.mock_executor.reconfigure.return_value = {"foo": "bar"}
        self.mock_prompt.generate_reconfigure_prompt.return_value = "prompt"
        self.mock_prompt.generate_plan_prompt.return_value = "prompt"
        self.mock_prompt.generate_chat_prompt.return_value = "prompt"
        self.mock_prompt.generate_intent_classifier_prompt.return_value = "prompt"

        resp = self.agent.chat("Update config", Intents.CHANGE_SETTINGS)
        assert "updated" in resp.response_text.lower() or "sorry" in resp.response_text.lower()

    def test_get_chat_context(self):
        self.mock_memory.read.return_value = {"results": []}
        res = self.agent.get_chat_context("uuid1")
        assert isinstance(res, list)

    def test_store_chat_context(self):
        uuid_ = "uuid1"
        messages = [{"memory": "foo", "created_at": datetime.datetime.now()}]
        self.mock_memory.store = MagicMock()
        self.agent.store_chat_context(uuid_, messages)
        self.mock_memory.store.assert_called_once()

    def test_run_workflow(self):
        self.agent.workflow_runner = MagicMock()
        wf = MagicMock()
        ctx = MagicMock()
        self.agent.run_workflow(wf, ctx)
        self.agent.workflow_runner.run.assert_called_once_with(wf, ctx)

    @pytest.mark.asyncio
    async def test_handoff(self):
        # Patch requests.post in handoff
        with patch("base_agent.ray_entrypoint.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"result": "ok"}
            resp = await self.agent.handoff("http://some-endpoint", "goal", {"plan": 1})
            assert resp == {"result": "ok"}
            mock_post.assert_called_once()

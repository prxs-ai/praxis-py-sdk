from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from ray.serve.deployment import Deployment

from praxis_sdk.agents import abc
from praxis_sdk.agents.card import card_builder
from praxis_sdk.agents.orchestration import workflow_builder


def bootstrap_main(agent_cls: type[abc.AbstractAgent]) -> type[Deployment]:
    """Bootstrap a main agent with the necessary components to be able to run as a Ray Serve deployment."""
    from ray import serve

    runner: abc.AbstractWorkflowRunner = workflow_builder()
    card: abc.AbstractAgentCard = card_builder()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # launch some tasks on app start
        runner.start_daemon()
        runner.run_background_workflows()

        agent_instance = app.state.agent_instance
        if hasattr(agent_instance, "p2p_manager"):
            await agent_instance.p2p_manager.start()
        yield
        runner.stop_daemon()

        if hasattr(agent_instance, "p2p_manager"):
            await agent_instance.p2p_manager.shutdown()

    app = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(app)
    class Agent(agent_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            from praxis_sdk.agents.p2p.manager import get_p2p_manager

            self.p2p_manager = get_p2p_manager()
            app.state.agent_instance = self

        @property
        def workflow_runner(self):
            return runner

        @property
        def agent_card(self):
            return card

        @app.get("/card")
        async def get_card(self):
            return self.agent_card

        @app.get("/workflows")
        async def list_workflows(self, status: str | None = None):
            return await self.workflow_runner.list_workflows(status)

        @app.post("/{goal}")
        async def handle(self, goal: str, plan: dict | None = None, context: Any = None):
            return await super().handle(goal, plan, context)

    return Agent

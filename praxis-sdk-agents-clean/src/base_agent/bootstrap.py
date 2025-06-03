from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from ray.serve.deployment import Deployment

from base_agent import abc
from base_agent.card import card_builder
from base_agent.orchestration import workflow_builder
from base_agent.p2p import p2p_builder


def bootstrap_main(agent_cls: type[abc.AbstractAgent]) -> type[Deployment]:
    """Bootstrap a main agent with the necessary components to be able to run as a Ray Serve deployment."""
    from ray import serve

    runner: abc.AbstractWorkflowRunner = workflow_builder()
    card: abc.AbstractAgentCard = card_builder()
    p2p: abc.AbstractAgentP2PManager = p2p_builder()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # launch some tasks on app start
        runner.start_daemon()
        runner.run_background_workflows()

        await p2p.start()
        yield
        runner.stop_daemon()

        await p2p.shutdown()
        # handle clean up

    app = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(app)
    class Agent(agent_cls):
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

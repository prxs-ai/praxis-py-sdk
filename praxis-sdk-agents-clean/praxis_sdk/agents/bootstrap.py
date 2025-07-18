from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from ray.serve.deployment import Deployment

from praxis_sdk.agents import abc
from praxis_sdk.agents.card import card_builder
from praxis_sdk.agents.orchestration import workflow_builder
from praxis_sdk.agents.p2p import p2p_builder


def bootstrap_main(agent_cls: type[abc.AbstractAgent]) -> type[Deployment]:
    """Bootstrap a main agent with the necessary components to be able to run as a Ray Serve deployment.
    
    This function creates a Ray Serve deployment class with integrated workflow runner,
    agent card, and P2P manager components. It sets up the FastAPI application lifecycle
    and exposes standard agent endpoints.
    
    Args:
        agent_cls: The abstract agent class to bootstrap
        
    Returns:
        Ray Serve deployment class ready for deployment
    """
    from ray import serve

    workflow_runner: abc.AbstractWorkflowRunner = workflow_builder()
    agent_card: abc.AbstractAgentCard = card_builder()
    p2p_manager: abc.AbstractAgentP2PManager = p2p_builder()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # launch some tasks on app start
        workflow_runner.start_daemon()
        workflow_runner.run_background_workflows()

        agent_instance = app.state.agent_instance
        if hasattr(agent_instance, "p2p_manager"):
            await agent_instance.p2p_manager.start()
        yield
        workflow_runner.stop_daemon()

        if hasattr(agent_instance, "p2p_manager"):
            await agent_instance.p2p_manager.shutdown()

    app = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(app)
    class Agent(agent_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.p2p_manager = p2p_manager
            app.state.agent_instance = self

        @property
        def workflow_runner(self):
            return workflow_runner

        @property
        def agent_card(self):
            return agent_card

        @app.get("/card")
        async def get_card(self):
            return self.agent_card

        @app.get("/workflows")
        async def list_workflows(self, status: str | None = None):
            return await self.workflow_runner.list_workflows(status)

        @app.post("/{goal}")
        async def handle_request(self, goal: str, plan: dict | None = None, context: Any = None):
            return await super().handle(goal, plan, context)

    return Agent

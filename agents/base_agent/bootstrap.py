from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

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
    async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage the lifecycle of the FastAPI application.
        
        Args:
            fastapi_app: The FastAPI application instance
            
        Yields:
            None during application runtime
        """
        # Start workflow runner daemon and background tasks
        workflow_runner.start_daemon()
        workflow_runner.run_background_workflows()

        # Start P2P manager if available
        agent_instance = fastapi_app.state.agent_instance
        if hasattr(agent_instance, "p2p_manager") and agent_instance.p2p_manager:
            await agent_instance.p2p_manager.start()
            
        yield
        
        # Cleanup on shutdown
        workflow_runner.stop_daemon()
        if hasattr(agent_instance, "p2p_manager") and agent_instance.p2p_manager:
            await agent_instance.p2p_manager.shutdown()

    fastapi_application = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(fastapi_application)
    class BootstrappedAgent(agent_cls):
        """Ray Serve deployment wrapper for the agent class."""
        
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Initialize the bootstrapped agent with required components.
            
            Args:
                *args: Positional arguments for agent initialization
                **kwargs: Keyword arguments for agent initialization
            """
            super().__init__(*args, **kwargs)
            self.p2p_manager = p2p_manager
            fastapi_application.state.agent_instance = self

        @property
        def workflow_runner(self) -> abc.AbstractWorkflowRunner:
            """Get the workflow runner instance.
            
            Returns:
                The configured workflow runner
            """
            return workflow_runner

        @property
        def agent_card(self) -> abc.AbstractAgentCard:
            """Get the agent card instance.
            
            Returns:
                The configured agent card
            """
            return agent_card

        @fastapi_application.get("/card")
        async def get_card(self) -> abc.AbstractAgentCard:
            """Retrieve the agent card information.
            
            Returns:
                The agent card containing metadata and capabilities
            """
            return self.agent_card

        @fastapi_application.get("/workflows")
        async def list_workflows(self, status: str | None = None) -> list[dict[str, Any]]:
            """List all workflows in the workflow runner.
            
            Args:
                status: Optional status filter for workflows
                
            Returns:
                List of workflow information dictionaries
            """
            return await self.workflow_runner.list_workflows(status)

        @fastapi_application.post("/{goal}")
        async def handle_request(
            self, 
            goal: str, 
            plan: dict | None = None, 
            context: Any = None
        ) -> abc.AbstractAgentOutputModel:
            """Handle incoming requests for goal achievement.
            
            Args:
                goal: The goal to achieve
                plan: Optional existing plan to use or modify
                context: Optional input context for the agent
                
            Returns:
                The result of achieving the goal
            """
            return await super().handle(goal, plan, context)

    return BootstrappedAgent

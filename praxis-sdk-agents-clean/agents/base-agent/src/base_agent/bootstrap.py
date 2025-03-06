from contextlib import asynccontextmanager

from fastapi import FastAPI

from base_agent import abc


def bootstrap_main(agent_cls: type[abc.AbstractAgent]) -> type[abc.AbstractAgent]:
    """Bootstrap a main agent with the necessary components to be able to run as a Ray Serve deployment."""
    from ray import serve

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # launch some tasks on app start
        yield
        # handle clean up

    app = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(app)
    class Agent(agent_cls):
        pass

    # Register the handle method as a POST endpoint
    Agent.handle = app.post("/{goal}")(Agent.handle)

    return Agent

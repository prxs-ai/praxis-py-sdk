from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urljoin

import requests
from fastapi import FastAPI


class BaseAgent:
    def __init__(self, *args, **kwargs):
        pass

    def handle(self, goal: str, plan: dict | None = None):
        """This is one of the most important endpoint of MAS.
        It handles all requests made by handoff from other agents or by user."""
        pass

    def reconfigure(self, config: dict[str, Any]):
        pass

    def handoff(self, endpoint: str, goal: str, plan: dict):
        """This method means that agent can't find a solution (wrong route/wrong plan/etc)
        and decide to handoff the task to another agent. """
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

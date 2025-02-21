from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urljoin

import ray
import requests
from fastapi import FastAPI
from ray import workflow

from agent.utils import generate_request_id


class BaseAgent:
    def __init__(self, *args, **kwargs):
        pass

    def handle(self, goal: str, plan: dict | None = None):
        """This is one of the most important endpoint of MAS.
        It handles all requests made by handoff from other agents or by user."""
        request_id = generate_request_id.bind()


        return self._run_workflow(request_id, goal)

    def get_most_relevant_agents(self, goal: str):
        """This method is used to find the most useful agents for the given goal."""
        return []

    def get_most_relevant_tools(self, goal: str):
        """This method is used to find the most useful tools for the given goal."""
        return [{"name": "example-tool", "version": "0.0.5", "openai_function_spec": {
            "type": "function", "function": {
                "name": "example_tool",
                "description": "A tool that returns the string passed in as an output.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message to echo.",
                            "default": "Hello World"
                        }
                    },
                    "required": ["message"]
                },
                "output": { "type": "object", "properties": {
                    "result": { "type": "string", "description": "Returns the input string as output." }
                }}
            }
        }}]

    def generate_plan(self, goal: str):
        """This method is used to generate a plan for the given goal."""
        return {"steps": []}

    @ray.remote
    def _run_workflow(self, request_id: str, goal: str):

        agents = self.get_most_relevant_agents(goal)
        tools = self.get_most_relevant_tools(goal)


        return workflow.continuation(request_id)


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

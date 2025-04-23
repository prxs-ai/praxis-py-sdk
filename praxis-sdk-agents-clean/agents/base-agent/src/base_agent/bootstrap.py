from contextlib import asynccontextmanager

from fastapi import FastAPI
from ray.serve.deployment import Deployment

from base_agent import abc
from base_agent.workflows import workflow_builder


def bootstrap_main(agent_cls: type[abc.AbstractAgent]) -> type[Deployment]:
    """Bootstrap a main agent with the necessary components to be able to run as a Ray Serve deployment."""
    from ray import serve

    runner: abc.AbstractWorkflowRunner = workflow_builder()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # launch some tasks on app start
        runner.start()
        yield
        runner.stop()
        # handle clean up

    fastapi = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(fastapi)
    class Agent(agent_cls):
        @property
        def workflow_runner(self):
            return runner

        @fastapi.post("/{goal}")
        async def handle(self, goal: str, plan: dict | None = None):
            return await super().handle(goal, plan)

        @fastapi.get("/workflows")
        async def list_workflows(self, status: str | None = None):
            return self.workflow_runner.list_workflows(status)

    return Agent

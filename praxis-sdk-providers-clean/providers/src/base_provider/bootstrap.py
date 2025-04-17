from contextlib import asynccontextmanager
from typing import Any

from base_provider import abc
from base_provider.runner import runner_builder
from fastapi import FastAPI


def bootstrap_main(provider_cls: type[abc.AbstractDataProvider]) -> type[abc.AbstractDataProvider]:
    """Bootstrap a main provider with the necessary components to be able to run as a Ray Serve deployment."""
    from ray import serve

    runner = runner_builder()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # launch some tasks on app start
        runner.start()
        yield
        runner.stop()
        # handle clean up

    app = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(app)
    class Provider(provider_cls):

        @property
        def runner(self) -> abc.AbstractDataRunner:
            return runner

        @app.get("/v1/contract")
        async def get_contract_handler(self) -> dict[str, Any]:
            return self.contract.spec

        @app.post("/v1/query")
        async def query_handler(self, filters: dict[str, Any]) -> Any:
            return await self.query(filters)

        @app.post("/v1/subscribe")
        async def subscribe_handler(self, filters: dict[str, Any]) -> str:
            return await self.subscribe(filters)

    return Provider

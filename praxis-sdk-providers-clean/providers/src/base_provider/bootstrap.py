from contextlib import asynccontextmanager

from base_provider import abc
from fastapi import FastAPI


def bootstrap_main(provider_cls: type[abc.AbstractProvider]) -> type[abc.AbstractProvider]:
    """Bootstrap a main provider with the necessary components to be able to run as a Ray Serve deployment."""
    from ray import serve

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # launch some tasks on app start
        yield
        # handle clean up

    app = FastAPI(lifespan=lifespan)

    @serve.deployment
    @serve.ingress(app)
    class Provider(provider_cls):
        pass

    return Provider

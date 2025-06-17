from base_provider.const import EntrypointGroup
from base_provider.runner import runner_builder
from base_provider.utils import get_entrypoint

app = get_entrypoint(EntrypointGroup.APP_ENTRYPOINT).load()


if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI, APIRouter
    from ray import serve

    # Run Ray Serve in local testing mode
    handle = serve.run(app({}),
                      route_prefix='/',
                      _local_testing_mode=True)

    fastapi_app = FastAPI()
    v1_router = APIRouter(prefix="/v1")

    @v1_router.get("/contract")
    async def contract_handler():
        return handle.contract.spec.remote()

    @v1_router.post("/query")
    async def query_handler(filters: dict):
        return await handle.query.remote(filters)

    @v1_router.post("/subscribe")
    async def subscribe_handler(filters: dict) -> str:
        return await handle.subscribe.remote(filters)

    fastapi_app.include_router(v1_router)

    # Run uvicorn server
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

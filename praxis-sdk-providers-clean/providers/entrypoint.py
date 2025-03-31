from base_provider.const import EntrypointGroup
from base_provider.runner import runner_builder
from base_provider.utils import get_entrypoint

app = get_entrypoint(EntrypointGroup.APP_ENTRYPOINT).load()


if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    from ray import serve

    # Run Ray Serve in local testing mode
    handle = serve.run(app({}),
                      route_prefix='/',
                      _local_testing_mode=True)

    fastapi_app = FastAPI()

    @fastapi_app.get("/v1/contract")
    async def contract_handler():
        return handle.contract.spec.remote()

    @fastapi_app.post("/v1/query")
    async def query_handler(filters: dict):
        return await handle.query.remote(filters)

    @fastapi_app.post("/v1/subscribe")
    async def subscribe_handler(filters: dict) -> str:
        return await handle.subscribe.remote(filters)

    # Run uvicorn server
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

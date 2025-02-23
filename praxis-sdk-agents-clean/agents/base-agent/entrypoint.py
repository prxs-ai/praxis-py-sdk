from base_agent.config import get_agent_config
from base_agent.utils import get_entrypoint

app = get_entrypoint(get_agent_config().group_name).load()


if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    from ray import serve

    # Run Ray Serve in local testing mode
    handle = serve.run(app(get_agent_config().model_dump()),
                      route_prefix='/',
                      _local_testing_mode=True)

    fastapi_app = FastAPI()

    @fastapi_app.post("/{goal}")
    async def handle_request(goal: str):
        return await handle.handle.remote(goal)

    # Run uvicorn server
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

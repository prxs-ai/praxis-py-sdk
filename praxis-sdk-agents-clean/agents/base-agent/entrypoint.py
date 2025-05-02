from typing import Any

from base_agent.const import EntrypointGroup
from base_agent.models import Workflow
from base_agent.utils import get_entrypoint
from ray import serve

app = get_entrypoint(EntrypointGroup.AGENT_ENTRYPOINT).load()

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    from ray import serve

    # Run Ray Serve in local testing mode
    handle = serve.run(app({}), route_prefix="/", _local_testing_mode=True)

    fastapi_app = FastAPI()

    @fastapi_app.post("/{goal}")
    async def handle_request(goal: str, plan: Workflow | None = None, context: Any = None):
        return await handle.handle.remote(goal, plan, context)

    @fastapi_app.get("/workflows")
    async def get_workflows(status: str | None = None):
        return await handle.list_workflows.remote(status)

    # Run uvicorn server
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

from typing import Any

from base_agent.const import EntrypointGroup
from base_agent.models import ChatRequest
from base_agent.utils import get_entrypoint
from ray import serve

entrypoint = get_entrypoint(EntrypointGroup.AGENT_ENTRYPOINT)
if entrypoint is None:
    raise RuntimeError(f"No entrypoint found for group {EntrypointGroup.AGENT_ENTRYPOINT}")

app = entrypoint.load()

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    from ray import serve

    # Run Ray Serve in local testing mode
    handle = serve.run(app({}), route_prefix="/", _local_testing_mode=True)

    app = FastAPI()


    @app.post("/chat")
    async def chat_with_agent(payload: ChatRequest):
        return await handle.chat.remote(payload.message, payload.action, payload.session_uuid)


    @app.get("/card")
    async def get_card():
        return await handle.get_card.remote()

    @app.post("/{goal}")
    async def handle_request(goal: str, plan: dict | None = None, context: Any = None):
        return await handle.handle.remote(goal, plan, context)

    @app.get("/workflows")
    async def get_workflows(status: str | None = None):
        return await handle.list_workflows.remote(status)

    # Run uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=8000)

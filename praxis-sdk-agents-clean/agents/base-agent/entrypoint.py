from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint
from ray import serve

# Load the bound Serve deployment (e.g. ExampleAgent.bind(config))
app = get_entrypoint(EntrypointGroup.AGENT_ENTRYPOINT).load()

if __name__ == "__main__":
    # already exposes `/{goal}` via @app.post
    serve.run(app, route_prefix="/v1")

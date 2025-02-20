from agent.config import get_agent_config
from agent.utils import get_entry_points

config = get_agent_config()


def get_agent():
    entrypoints = get_entry_points(config.group_name)
    try:
        print(f"Loading {config.target_entrypoint} entrypoint...")
        return entrypoints[config.target_entrypoint].load()
    except KeyError:
        print(f"Entrypoint {config.target_entrypoint} not found. Loading {config.default_entrypoint} entrypoint...")
        return entrypoints[config.default_entrypoint].load()

app = get_agent()


if __name__ == "__main__":
    from ray import serve

    serve.run(app, route_prefix='/')

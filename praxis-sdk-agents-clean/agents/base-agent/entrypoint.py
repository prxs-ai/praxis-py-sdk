from agent.config import get_agent_config
from agent.utils import get_entry_point

config = get_agent_config()

app = get_entry_point(config.group_name, config.entrypoint_name).load()

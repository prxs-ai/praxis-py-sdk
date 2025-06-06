from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint

app = get_entrypoint(EntrypointGroup.AGENT_ENTRYPOINT).load()

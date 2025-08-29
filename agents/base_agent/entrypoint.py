from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.utils import get_entrypoint

app = get_entrypoint(EntrypointGroup.AGENT_ENTRYPOINT).load()

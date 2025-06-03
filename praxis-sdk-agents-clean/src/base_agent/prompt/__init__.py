from __future__ import annotations

from typing import TYPE_CHECKING

from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint

if TYPE_CHECKING:
    from base_agent.prompt.config import BasicPromptConfig


def prompt_builder():
    config: BasicPromptConfig = get_entrypoint(EntrypointGroup.AGENT_PROMPT_CONFIG_ENTRYPOINT).load()

    return get_entrypoint(EntrypointGroup.AGENT_PROMPT_ENTRYPOINT).load()(config())

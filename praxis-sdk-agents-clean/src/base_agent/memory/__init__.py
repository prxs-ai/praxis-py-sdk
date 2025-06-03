from __future__ import annotations

from typing import TYPE_CHECKING

from base_agent.const import EntrypointGroup
from base_agent.utils import get_entrypoint

if TYPE_CHECKING:
    from base_agent.prompt.config import BasicPromptConfig


def memory_builder(*args, **kwargs):
    config: BasicPromptConfig = get_entrypoint(EntrypointGroup.MEMORY_CONFIG_ENTRYPOINT).load()
    return get_entrypoint(EntrypointGroup.MEMORY_ENTRYPOINT).load()(config())

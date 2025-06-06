from __future__ import annotations

from typing import TYPE_CHECKING

from praxis_sdk.agents.const import EntrypointGroup
from praxis_sdk.agents.utils import get_entrypoint

if TYPE_CHECKING:
    from praxis_sdk.agents.prompt.config import BasicPromptConfig


def ai_registry_builder(*args, **kwargs):
    config: BasicPromptConfig = get_entrypoint(EntrypointGroup.AI_REGISTRY_CONFIG_ENTRYPOINT).load()
    return get_entrypoint(EntrypointGroup.AI_REGISTRY_ENTRYPOINT).load()(config())

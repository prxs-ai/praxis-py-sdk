from collections.abc import Sequence
from typing import Any
from urllib.parse import urljoin

import requests

from base_provider import abc
from base_provider.bootstrap import bootstrap_main
from base_provider.config import BasicProviderConfig, get_provider_config


class BaseProvider(abc.AbstractProvider):
    """Base default implementation for all data providers."""

    def __init__(self, config: BasicProviderConfig, *args, **kwargs):
        self.config = config

    # async def handle(self, goal: str, plan: dict | None = None):
    #     """This is one of the most important endpoint of MAS.
    #     It handles all requests made by handoff from other providers or by user."""

    #     providers = self.get_most_relevant_providers(goal)
    #     tools = self.get_most_relevant_tools(goal)

    #     plan = self.generate_plan(goal, providers, tools, plan)

    #     return self.run_workflow(plan)


def provider_builder(args: dict):
    return bootstrap_main(BaseProvider).bind(config=get_provider_config(**args))

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

def provider_builder(args: dict):
    return bootstrap_main(BaseProvider).bind(config=get_provider_config(**args))

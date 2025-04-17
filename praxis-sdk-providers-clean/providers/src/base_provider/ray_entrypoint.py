import hashlib
import json
from typing import Any

from base_provider import abc
from base_provider.bootstrap import bootstrap_main
from base_provider.config import BaseProviderConfig, get_provider_config
from base_provider.contract import contract_builder
from base_provider.exceptions import AsyncNotSupportedException, SyncNotSupportedException
from base_provider.processors import processors_builder
from base_provider.sinks import sinks_builder
from base_provider.sources import sources_builder
from base_provider.stream import stream_builder
from base_provider.triggers import triggers_builder
from fastapi.security import HTTPAuthorizationCredentials

from .abc import AbstractDataContract, AbstractDataProvider, AbstractDataRunner


class BaseProvider(AbstractDataProvider):
    """Base implementation of a provider supporting both sync and async modes."""

    def __init__(self, config: BaseProviderConfig):
        self.config = config
        self._contract = contract_builder()
        self.stream = stream_builder()

        self.stream.setup(
            triggers=triggers_builder(),
            sources=sources_builder(),
            processors=processors_builder(),
            sinks=sinks_builder(),
        )

        self._contract.build_spec(
            domain=self.config.domain,
            version=self.config.version,
            title=self.config.title,
            description=self.config.description,
            models=self.stream.models,
            servers=self.stream.servers,
            service_levels=self.stream.service_levels,
            supported_modes=self.stream.supported_modes,
        )

    @property
    def domain(self) -> str:
        return self.config.domain

    @property
    def version(self) -> str:
        return self.config.version

    @property
    def runner(self) -> AbstractDataRunner:
        raise NotImplementedError("Runner not implemented for BaseProvider")

    @property
    def contract(self) -> AbstractDataContract:
        return self._contract

    async def authenticate(self, credentials: HTTPAuthorizationCredentials | None = None) -> bool:
        # No-op for now, implement actual authentication logic here
        return True

    def _generate_run_hash(self, filters: dict[str, Any]) -> str:
        """Generate a unique hash for the topic based on filters."""
        filter_str = json.dumps(filters, sort_keys=True)
        return hashlib.sha256(filter_str.encode()).hexdigest()[:7]

    def _get_topic_name(self, data_type: str, topic_hash: str) -> str:
        """Generate the full topic name."""
        return f"{self.domain}.{self.version}.{data_type}.{topic_hash}"

    async def query(self, filters: dict[str, Any]) -> Any:
        """Synchronously query data based on filters."""
        if not self._contract.supports_sync:
            raise SyncNotSupportedException("Synchronous queries not supported")
        await self.authenticate()

        return await self.runner.run_once(run_id=self._generate_run_hash(filters), stream=self.stream, filters=filters)

    async def subscribe(self, filters: dict[str, Any]) -> str:
        """Subscribe to data stream and return Kafka topic."""
        if not self._contract.supports_async:
            raise AsyncNotSupportedException("Asynchronous streaming not supported")

        await self.authenticate()

        topic_hash = self._generate_run_hash(filters)
        topic_name = self._get_topic_name(abc.AsyncDataType.BATCH, topic_hash)

        await self.runner.run(run_id=topic_hash, stream=self.stream, filters=filters, topic=topic_name)

        return topic_name


def provider_builder(args: dict):
    return bootstrap_main(BaseProvider).bind(config=get_provider_config(**args))

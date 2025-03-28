import hashlib
import json
from typing import Any

from base_provider import abc
from base_provider.bootstrap import bootstrap_main
from base_provider.config import BaseProviderConfig, get_provider_config
from base_provider.contract import contract_builder
from base_provider.exceptions import AsyncNotSupportedException, SyncNotSupportedException
from base_provider.processor import processor_builder
from base_provider.sink import sinks_builder
from base_provider.source import source_builder
from base_provider.stream import stream_builder
from base_provider.trigger import trigger_builder
from fastapi.security import HTTPAuthorizationCredentials

from .abc import AbstractDataContract, AbstractDataProvider


class BaseProvider(AbstractDataProvider):
    """Base implementation of a provider supporting both sync and async modes."""

    def __init__(self, config: BaseProviderConfig):
        self.config = config
        self._contract = contract_builder()
        self._stream = stream_builder()

        sinks = self.config.sinks.split(",")
        if self._contract.supports_sync:
            if "basic" not in sinks:
                sinks.append("basic")
        if self._contract.supports_async:
            if "kafka" not in self.config.sinks:
                sinks.append("kafka")

        self._stream.setup(
            triggers=[trigger_builder()],
            source=source_builder(),
            processors=[processor_builder()],
            sinks=sinks_builder(sinks),
        )

        self._contract.build_spec(
            domain=self.config.domain,
            version=self.config.version,
            title=self.config.title,
            description=self.config.description,
            models=self._stream.models,
            servers=self._stream.servers,
            service_levels=self._stream.service_levels,
            supported_modes=self._stream.supported_modes,
        )

    @property
    def domain(self) -> str:
        return self.config.domain

    @property
    def version(self) -> str:
        return self.config.version

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
        return await self._stream.run_once(self._generate_run_hash(filters), filters=filters)

    async def subscribe(self, filters: dict[str, Any]) -> str:
        """Subscribe to data stream and return Kafka topic."""
        if not self._contract.supports_async:
            raise AsyncNotSupportedException("Asynchronous streaming not supported")

        await self.authenticate()

        topic_hash = self._generate_run_hash(filters)
        topic_name = self._get_topic_name(abc.AsyncDataType.BATCH, topic_hash)

        await self._stream.run(topic_hash, filters=filters, topic=topic_name)

        return topic_name


def provider_builder(args: dict):
    return bootstrap_main(BaseProvider).bind(config=get_provider_config(**args))

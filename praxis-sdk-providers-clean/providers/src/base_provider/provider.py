import hashlib
import json
from typing import Any

from base_provider.config import BaseProviderConfig
from base_provider.contract import contract_builder
from base_provider.exceptions import AsyncNotSupportedException, SyncNotSupportedException
from base_provider.processor import processor_builder
from base_provider.sink import sink_builder
from base_provider.source import source_builder
from fastapi.security import HTTPAuthorizationCredentials

from .abc import AbstractDataContract, AbstractDataProvider


class BaseProvider(AbstractDataProvider):
    """Base implementation of a provider supporting both sync and async modes."""

    def __init__(
        self,
        config: BaseProviderConfig
    ):
        self.config = config
        self._source = source_builder()
        self._processor = processor_builder()
        self._sink = sink_builder()

        self._contract = contract_builder()

        if self._contract.supports_async:
            pass

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

    def _generate_topic_hash(self, filters: dict[str, Any]) -> str:
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
        return await self._query_implementation(filters)

    async def subscribe(self, filters: dict[str, Any]) -> str:
        """Subscribe to data stream and return Kafka topic."""
        if not self._contract.supports_async:
            raise AsyncNotSupportedException("Asynchronous streaming not supported")
        if not self._kafka_manager:
            raise RuntimeError("Kafka manager not configured")

        await self.authenticate()

        topic_hash = self._generate_topic_hash(filters)
        topic_name = self._get_topic_name("data", topic_hash)

        # Create topic if it doesn't exist
        await self._kafka_manager.create_topic(topic_name)

        # Start streaming data to the topic based on filters
        await self._stream_implementation(filters, topic_name)

        return topic_name

    async def _query_implementation(self, filters: dict[str, Any]) -> Any:
        """Implementation of synchronous query logic."""
        raise NotImplementedError("Query implementation not provided")

    async def _stream_implementation(self, filters: dict[str, Any], topic: str) -> None:
        """Implementation of asynchronous streaming logic."""
        raise NotImplementedError("Stream implementation not provided")

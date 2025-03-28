from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Generic, TypeVar


class DataMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"


class AsyncDataType(str, Enum):
    STREAM = "stream"
    BATCH = "batch"


T = TypeVar("T")
U = TypeVar("U")


class AbstractDataContract(ABC):
    """Abstract base class for data contracts."""

    @abstractmethod
    def build_spec(self, *args, **kwargs):
        """Build the data contract."""
        pass

    @property
    @abstractmethod
    def spec(self) -> dict[str, Any]:
        """Return the data contract specification."""
        pass

    @property
    @abstractmethod
    def supports_sync(self) -> bool:
        """Whether provider supports synchronous queries."""
        pass

    @property
    @abstractmethod
    def supports_async(self) -> bool:
        """Whether provider supports asynchronous streaming."""
        pass


class AbstractDataSource(Generic[T], ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    async def fetch(self, *args, **kwargs) -> list[T]:
        """Fetch data from the source."""
        pass


class AbstractDataProcessor(Generic[T, U], ABC):
    """Abstract base class for data processors."""

    @abstractmethod
    async def process(self, data: T, filters: dict[str, Any]) -> U:
        """Process data."""
        pass


class AbstractDataSink(Generic[T], ABC):
    """Abstract base class for data sinks."""

    @property
    @abstractmethod
    def mode(self) -> DataMode:
        """Return the sink's mode."""
        pass

    @abstractmethod
    async def write(self, data: T, *args, **kwargs) -> T:
        """Push data to the sink."""
        pass


class AbstractDataProvider(ABC):
    """Abstract base class for data provider implementations."""

    @property
    @abstractmethod
    def domain(self) -> str:
        """Return the provider's domain name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the provider's version."""
        pass

    @property
    @abstractmethod
    def contract(self) -> AbstractDataContract:
        """Return the provider's data contract."""
        pass

    @abstractmethod
    async def query(self, *args, **kwargs) -> Any:
        """
        Synchronously query data based on filters.
        Raises NotImplementedError if sync mode not supported.
        """
        pass

    @abstractmethod
    async def subscribe(self, *args, **kwargs) -> Any:
        """
        Subscribe to data stream and return Kafka topic.
        Raises NotImplementedError if async mode not supported.
        """
        pass

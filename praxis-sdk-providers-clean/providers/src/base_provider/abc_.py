from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Generic, TypeVar


class DataMode(StrEnum):
    SYNC = "sync"
    ASYNC = "async"

    @classmethod
    def all(cls) -> set[str]:
        return {cls.SYNC, cls.ASYNC}


class AsyncDataType(StrEnum):
    STREAM = "stream"
    BATCH = "batch"


T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


class AbstractDataContract(ABC):
    """Abstract base class for data contracts."""

    @abstractmethod
    def build_spec(self, *args: Any, **kwargs: Any) -> AbstractDataContract:
        """Build the data contract."""
        raise NotImplementedError

    @property
    @abstractmethod
    def spec(self) -> dict[str, Any]:
        """Return the data contract specification."""
        raise NotImplementedError

    @property
    @abstractmethod
    def supports_sync(self) -> bool:
        """Whether provider supports synchronous queries."""
        raise NotImplementedError

    @property
    @abstractmethod
    def supports_async(self) -> bool:
        """Whether provider supports asynchronous streaming."""
        raise NotImplementedError


class AbstractDataTrigger(Generic[E], ABC):
    """Abstract base class for data trigger."""

    @abstractmethod
    async def trigger(self, *args: Any, **kwargs: Any) -> E:
        """Trigger data."""
        raise NotImplementedError


class AbstractDataSource(Generic[T], ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    async def fetch(self, *args: Any, **kwargs: Any) -> list[T]:
        """Fetch data from the source."""
        raise NotImplementedError


class AbstractDataProcessor(Generic[T, U], ABC):
    """Abstract base class for data processors."""

    @abstractmethod
    async def process(self, data: T, filters: dict[str, Any]) -> U:
        """Process data."""
        raise NotImplementedError


class AbstractDataSink(Generic[T], ABC):
    """Abstract base class for data sinks."""

    @property
    @abstractmethod
    def mode(self) -> DataMode:
        """Return the sink's mode."""
        raise NotImplementedError

    @abstractmethod
    async def write(self, data: T, *args: Any, **kwargs: Any) -> T:
        """Push data to the sink."""
        raise NotImplementedError


class AbstractDataStream(Generic[T, U], ABC):
    """Abstract base class for data streams."""

    @abstractmethod
    async def start(self) -> None:
        """Start all data streams."""
        raise NotImplementedError

    @abstractmethod
    async def setup(
        self,
        triggers: list[AbstractDataTrigger[E]],
        source: AbstractDataSource[T],
        processors: list[AbstractDataProcessor[Any, Any]],
        sinks: list[AbstractDataSink[U]],
    ) -> None:
        """Setup the data stream."""
        raise NotImplementedError

    @abstractmethod
    async def run_once(self, *args: Any, **kwargs: Any) -> Any:
        """Run the data pipeline."""
        raise NotImplementedError

    @property
    @abstractmethod
    def models(self) -> dict[str, Any]:
        """Return the models supported by the stream."""
        raise NotImplementedError

    @property
    @abstractmethod
    def service_levels(self) -> dict[str, Any]:
        """Return the service levels supported by the stream."""
        raise NotImplementedError

    @property
    @abstractmethod
    def servers(self) -> dict[str, Any]:
        """Return the servers supported by the stream."""
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_modes(self) -> set[DataMode]:
        """Return the supported modes."""
        raise NotImplementedError

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> None:
        """Run the data pipeline in a loop."""
        raise NotImplementedError

    @abstractmethod
    async def process_item(self, item: Any) -> Any:
        """Process a single item."""
        raise NotImplementedError

    @abstractmethod
    async def process_batch(self, batch: list[Any]) -> list[Any]:
        """Process a batch of items."""
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        """Stop all data streams."""
        raise NotImplementedError


class AbstractDataProvider(ABC):
    """Abstract base class for data provider implementations."""

    @property
    @abstractmethod
    def domain(self) -> str:
        """Return the provider's domain name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the provider's version."""
        raise NotImplementedError

    @property
    @abstractmethod
    def contract(self) -> AbstractDataContract:
        """Return the provider's data contract."""
        raise NotImplementedError

    @abstractmethod
    async def query(self, *args: Any, **kwargs: Any) -> Any:
        """
        Synchronously query data based on filters.
        Raises NotImplementedError if sync mode not supported.
        """
        raise NotImplementedError

    @abstractmethod
    async def subscribe(self, *args: Any, **kwargs: Any) -> Any:
        """
        Subscribe to data stream and return Kafka topic.
        Raises NotImplementedError if async mode not supported.
        """
        raise NotImplementedError

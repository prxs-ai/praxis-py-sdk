from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Generic, TypeVar


class DataMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"

    @classmethod
    def all(cls):
        return {cls.SYNC, cls.ASYNC}


class DataModelType(str, Enum):
    STREAM = "stream"
    BATCH = "batch"

    def __str__(self):
        return self.value


T = TypeVar("T")
E = TypeVar("E")
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


class AbstractDataTrigger(Generic[E], ABC):
    """Abstract base class for data trigger."""

    @abstractmethod
    async def trigger(self, *args, **kwargs) -> E:
        """Trigger data."""
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
    async def process(self, data: T, **filters) -> U:
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


class AbstractDataStream(Generic[T, U], ABC):
    """Abstract base class for data streams."""

    @abstractmethod
    async def setup(
        self,
        triggers: dict[str, AbstractDataTrigger[E]],
        sources: dict[str, AbstractDataSource[T]],
        processors: dict[str, AbstractDataProcessor[Any, Any]],
        sinks: dict[str, AbstractDataSink[U]],
    ) -> None:
        """Setup the data stream."""
        pass

    @property
    @abstractmethod
    def models(self) -> dict[str, Any]:
        """Return the models supported by the stream."""
        pass

    @property
    @abstractmethod
    def service_levels(self) -> dict[str, Any]:
        """Return the service levels supported by the stream."""
        pass

    @property
    @abstractmethod
    def servers(self) -> dict[str, Any]:
        """Return the servers supported by the stream."""
        pass

    @property
    @abstractmethod
    def supported_modes(self) -> set[DataMode]:
        """Return the supported modes."""
        pass

    @abstractmethod
    async def process_item(self, item: Any) -> Any:
        """Process a single item."""
        pass

    @abstractmethod
    async def fetch_batch(self, *args, **kwargs) -> list[Any]:
        """Process a batch of items."""
        pass

    @abstractmethod
    async def process_batch(self, batch: dict[str, list[Any]]) -> dict[str, Any]:
        """Process a batch of items."""
        pass

    @abstractmethod
    async def write_batch(self, batch: dict[str, list[Any]], *args, **kwargs) -> None:
        """Write a batch of items."""
        pass

class AbstractDataRunner(Generic[T], ABC):
    """Abstract base class for data runner implementations."""

    @classmethod
    @abstractmethod
    def start(cls) -> None:
        """Start all data workflows."""
        pass

    @abstractmethod
    async def run_once(self, run_id: str, stream: AbstractDataStream[T, Any], *args, **kwargs) -> Any:
        """Run the data pipeline and return a result."""
        pass

    @abstractmethod
    async def run(self, run_id: str, stream: AbstractDataStream[T, Any], *args, **kwargs) -> None:
        """Run the data pipeline in a background."""
        pass

    @classmethod
    @abstractmethod
    def stop(cls) -> None:
        """Stop all data workflows."""
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
    def runner(self) -> AbstractDataRunner:
        """Return the provider's data runner."""
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

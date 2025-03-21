from abc import ABC, abstractmethod

from base_provider.models import SubscribeRequestModel, SubscribeResponseModel


class AbstractProvider(ABC):
    """Abstract base class for data provider implementations."""

    @abstractmethod
    def subscribe(self, model: SubscribeRequestModel) -> SubscribeResponseModel:
        """Subscribe to data from the provider."""
        raise NotImplementedError

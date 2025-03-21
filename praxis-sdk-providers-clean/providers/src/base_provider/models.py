from typing import Any

from pydantic import BaseModel


class BaseProviderModel(BaseModel):
    """Base model for all provider models."""
    pass


class SubscribeRequestModel(BaseProviderModel):
    """Model for subscribe requests."""
    filters: dict[str, Any]


class SubscribeResponseModel(BaseProviderModel):
    """Model for subscribe responses."""
    kafka_topic: str

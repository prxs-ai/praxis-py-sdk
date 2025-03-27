from typing import Any

from pydantic import BaseModel


class BaseProviderModel(BaseModel):
    """Base model for all provider models."""

    pass


class BaseFilterModel(BaseModel):
    """Base model for all filter models."""
    pass


class SubscribeRequestModel(BaseProviderModel):
    """Model for subscribe requests."""

    filters: dict[str, Any]


class SubscribeResponseModel(BaseProviderModel):
    """Model for subscribe responses."""

    kafka_topic: str


class QueryRequestModel(BaseProviderModel):
    """Model for query requests."""

    filters: dict[str, Any]


class QueryResponseModel(BaseProviderModel):
    """Model for query responses."""

    data: list[dict[str, Any]]

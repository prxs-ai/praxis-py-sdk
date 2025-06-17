from typing import Any

from base_provider.abc import DataMode, DataModelType
from pydantic import BaseModel, Field


class ServerSpec(BaseModel):
    pass

class KafkaServerSpec(ServerSpec):
    # TODO: make datacontract.com compatible
    type: str
    environment: str
    location: str
    topic_template: str | None = None
    format: str = "msgpack"


class Role(BaseModel):
    name: str
    description: str


class Policy(BaseModel):
    name: str
    url: str


class DataField(BaseModel):
    type: str
    required: bool = False
    unique: bool = False
    primary_key: bool = False
    pii: bool = False


class DataModel(BaseModel):
    description: str
    type: DataModelType
    fields: dict[str, DataField]
    examples: list[str] = Field(default_factory=list)
    supported_modes: set[DataMode] = DataMode.all()


class ServiceLevel(BaseModel):
    availability: dict[str, Any]
    retention: dict[str, Any]


class ContractSpecification(BaseModel):
    data_contract_specification: str
    id: str
    info: dict[str, str]
    servers: dict[str, ServerSpec]
    roles: list[Role]
    terms: dict[str, str]
    policies: list[Policy]
    models: dict[str, DataModel]
    service_levels: ServiceLevel
    tags: list[str] = Field(default_factory=list)
    supported_modes: set[DataMode]

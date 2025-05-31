from typing import Any

from pydantic import BaseModel, Field, computed_field, field_serializer, field_validator

from base_agent.abc import (
    AbstractAgentCard,
    AbstractAgentInputModel,
    AbstractAgentOutputModel,
    AbstractAgentParamsModel,
    AbstractAgentSkill,
)
from base_agent.utils import create_pydantic_model_from_json_schema


class AgentSKill(AbstractAgentSkill):
    id: str = Field(..., description="ID of the skill")
    name: str = Field(..., description="Name of the skill")
    description: str = Field(..., description="Description of the skill")
    path: str = Field(..., description="Path to the skill")
    params_model: type[AbstractAgentParamsModel] = Field(
        ..., description="Parameters for the skill", alias="params_schema"
    )
    method: str = Field(default="POST", description="HTTP method to use for skill")
    input_model: type[AbstractAgentInputModel] = Field(
        ..., description="Input model for the skill", alias="input_schema"
    )
    output_model: type[AbstractAgentOutputModel] = Field(
        ..., description="Output model for the skill", alias="output_schema"
    )

    @field_serializer("params_model", "input_model", "output_model", when_used='always')
    def create_models(self, model: BaseModel, _info) -> dict:
        return model.model_json_schema()

    @field_validator("params_model", mode="before")
    @classmethod
    def validate_params(cls, value: Any) -> BaseModel:
        if isinstance(value, dict):
            return create_pydantic_model_from_json_schema("DynamicParamsModel", value, base_klass=AbstractAgentParamsModel)
        return value
    
    @field_validator("input_model", mode="before")
    @classmethod
    def validate_input(cls, value: Any) -> BaseModel:
        if isinstance(value, dict):
            return create_pydantic_model_from_json_schema("DynamicInputModel", value, base_klass=AbstractAgentInputModel)
        return value

    @field_validator("output_model", mode="before")
    @classmethod
    def validate_output(cls, value: Any) -> BaseModel:
        if isinstance(value, dict):
            return create_pydantic_model_from_json_schema("DynamicOutputModel", value, base_klass=AbstractAgentOutputModel)
        return value


class AgentCard(AbstractAgentCard):
    name: str = Field(..., description="Name of the agent")
    version: str = Field(..., description="Version of the agent")
    description: str = Field(..., description="Description of the agent")

    skills: list[AgentSKill] = Field(..., description="List of skills of the agent")

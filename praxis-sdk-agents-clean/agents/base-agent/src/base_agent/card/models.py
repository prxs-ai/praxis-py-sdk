from pydantic import Field, computed_field

from base_agent.abc import (
    AbstractAgentCard,
    AbstractAgentInputModel,
    AbstractAgentOutputModel,
    AbstractAgentParamsModel,
    AbstractAgentSkill,
)


class AgentSKill(AbstractAgentSkill):
    id: str = Field(..., description="ID of the skill")
    name: str = Field(..., description="Name of the skill")
    description: str = Field(..., description="Description of the skill")
    path: str = Field(..., description="Path to the skill")
    params_model: type[AbstractAgentParamsModel] = Field(..., description="Parameters for the skill", exclude=True)
    method: str = Field(default="POST", description="HTTP method to use for skill")
    input_model: type[AbstractAgentInputModel] = Field(..., description="Input model for the skill", exclude=True)
    output_model: type[AbstractAgentOutputModel] = Field(..., description="Output model for the skill", exclude=True)

    @computed_field
    @property
    def params_schema(self) -> dict:
        return self.params_model.model_json_schema()

    @computed_field
    @property
    def input_schema(self) -> dict:
        return self.input_model.model_json_schema()

    @computed_field
    @property
    def output_schema(self) -> dict:
        return self.output_model.model_json_schema()


class AgentCard(AbstractAgentCard):
    name: str = Field(..., description="Name of the agent")
    version: str = Field(..., description="Version of the agent")
    description: str = Field(..., description="Description of the agent")

    skills: list[AgentSKill] = Field(..., description="List of skills of the agent")

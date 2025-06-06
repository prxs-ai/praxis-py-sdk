import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class ToolModel(BaseModel):
    name: str
    version: str | None = None
    default_parameters: dict[str, Any] | None = Field(default_factory=dict)
    parameters_spec: dict[str, Any] | None = Field(default_factory=dict)
    openai_function_spec: dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def validate_name_and_version(cls, data: dict[str, Any]) -> dict[str, Any]:
        if "version" not in data or data["version"] is None:
            # If no version is specified, we assume the latest version
            data["name"], data["version"] = cls.parse_version_from_name(data["name"])
        return data

    @classmethod
    def parse_version_from_name(cls, name: str) -> tuple[str, str | None]:
        """Parse name and version from string in format package@version."""
        if "@" in name:
            package, version = name.split("@", 1)
            return package, version
        return name, None

    def render_pip_dependency(self) -> str:
        return f"{self.package_name}=={self.version}" if self.version else self.name

    @property
    def package_name(self) -> str:
        return self.name.replace("_", "-")

    @property
    def function_name(self) -> str:
        return self.openai_function_spec["function"]["name"]

    def render_function_spec(self) -> str:
        return f"""- {self.openai_function_spec["function"]["name"]}
    - description: {self.openai_function_spec["function"]["description"]}
    - parameters: {self.parameters_spec}
    - inputs: {self.openai_function_spec["function"]["parameters"]}
"""


class ParameterItem(BaseModel):
    name: str
    value: Any


class InputItem(BaseModel):
    name: str
    value: Any


class OutputItem(BaseModel):
    name: str


class WorkflowStep(BaseModel):
    name: str
    tool: ToolModel
    thought: str | None = None
    observation: str | None = None
    parameters: list[ParameterItem] = Field(default_factory=list)
    inputs: list[InputItem] = Field(default_factory=list)
    outputs: list[OutputItem] = Field(default_factory=list)

    @property
    def task_id(self) -> str:
        return f"{self.name}: {self.tool}"

    @field_validator("tool", mode="before")
    @classmethod
    def validate_tool(cls, v: Any) -> "ToolModel":
        if isinstance(v, str):
            return ToolModel(name=v, openai_function_spec={})
        return v

    @property
    def env_vars(self) -> dict[str, str]:
        d = {}
        if self.tool.default_parameters:
            # get default parameters
            d.update(self.tool.default_parameters)
        if "params" in d and isinstance(d["params"], dict):
            del d["params"]
            # replace with nested parameters
            # d['params'] = ",".join([f"{p.name}=\"{p.value}\"" for p in self.parameters])
            d.update({f"params__{p.name}": p.value for p in self.parameters})
        else:
            d.update({p.name: p.value for p in self.parameters})
        return d

    @property
    def args(self) -> dict[str, Any]:
        return {a.name: a.value for a in self.inputs}

    def get_thought_action_observation(self, *, include_action: bool = True, include_thought: bool = True) -> str:
        thought_action_observation = ""
        if self.thought and include_thought:
            thought_action_observation = f"Thought: {self.thought}\n"
        if include_action:
            tool_args = {inp.name: inp.value for inp in self.inputs}
            thought_action_observation += f"{self.name}({tool_args})\n"
        if self.observation is not None:
            thought_action_observation += f"Observation: {self.observation}\n"
        return thought_action_observation


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda x: f"dag-{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    thought: str | None = None
    parameters: list[Any] = Field(default_factory=list)
    steps: list[WorkflowStep]
    outputs: list[OutputItem] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    action: str | None = None
    session_uuid: str | None = None


class ChatMessageModel(BaseModel):
    role: str = Field(..., description="Sender role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime | None = Field(default_factory=datetime.utcnow, description="Message timestamp")


class ChatContextModel(BaseModel):
    uuid: str = Field(..., description="Unique chat/session UUID")
    history: list[ChatMessageModel] = Field(default_factory=list, description="Chronological chat messages")


class MemoryModel(BaseModel):
    goal: str
    plan: dict[str, Any]
    result: dict[str, Any]
    context: dict[str, Any] | None = Field(default=None, description="Used when plan is provided")


class AgentModel(BaseModel):
    name: str
    description: str
    version: str

    @computed_field
    def endpoint(self) -> str:
        # TODO(team): Change this to the most appropriate way via route mapping from ai registry  # https://github.com/project/issues/123
        return f"http://{self.name}-serve-svc.praxis:8000"
        # return "http://localhost:8000"


class GoalModel(BaseModel):
    goal: str = Field(..., description="Goal to reach")


class QueryData(BaseModel):
    query: str = Field(..., description="Query to search for")
    mode: Literal["local", "global", "hybrid", "naive", "mix"] = Field(
        default="global",
        description="Specifies the retrieval mode:\n"
        "- 'local': Focuses on context-dependent information.\n"
        "- 'global': Utilizes global knowledge.\n"
        "- 'hybrid': Combines local and global retrieval methods.\n"
        "- 'naive': Performs a basic search without advanced techniques.\n"
        "- 'mix': Integrates knowledge graph and vector retrieval."
        "  - Uses both structured (KG) and unstructured (vector) information\n"
        "  - Provides comprehensive answers by analyzing relationships and context\n"
        "  - Supports image content through HTML img tags\n"
        "  - Allows control over retrieval depth via top_k parameter",
    )


class InsightModel(BaseModel):
    domain_knowledge: str = Field(..., description="Insight from the private domain knowledge")


class HandoffParamsModel(BaseModel):
    endpoint: str = Field(..., description="Endpoint to hand off to")
    path: str = Field(default="/{goal}", description="Path to append to the endpoint")
    method: str = Field("POST", description="HTTP method to use for the request")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters to pass in the request")

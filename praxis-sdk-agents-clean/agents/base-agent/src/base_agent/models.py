from typing import Any, List, Literal, Optional
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator


class ToolModel(BaseModel):
    name: str
    version: str | None = None
    openai_function_spec: dict[str, Any]

    @model_validator(mode='before')
    def validate_name_and_version(cls, data):
        if 'version' not in data or data['version'] is None:
            # If no version is specified, we assume the latest version
            data['name'], data['version'] = cls.parse_version_from_name(data['name'])
        return data

    @classmethod
    def parse_version_from_name(cls, name: str) -> tuple[str, str | None]:
        """Parse name and version from string in format package@version."""
        if '@' in name:
            package, version = name.split('@', 1)
            return package, version
        return name, None

    def render_pip_dependency(self) -> str:
        return f"{self.package_name}=={self.version}" if self.version else self.name
    
    @property
    def package_name(self) -> str:
        return self.name.replace('_', '-')
    
    @property
    def function_name(self) -> str:
        return self.openai_function_spec["function"]["name"]

    def render_function_spec(self) -> str:
        return f"""- {self.openai_function_spec["function"]["name"]}
    - description: {self.openai_function_spec["function"]["description"]}
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
    thought: Optional[str] = None
    observation: Optional[str] = None
    parameters: List[ParameterItem] = Field(default_factory=list)
    inputs: List[InputItem] = Field(default_factory=list)
    outputs: List[OutputItem] = Field(default_factory=list)

    @property
    def task_id(self) -> str:
        return f"{self.name}: {self.tool}"
    
    @field_validator('tool', mode='before')
    def validate_tool(cls, v):
        if isinstance(v, str):
            return ToolModel(name=v, openai_function_spec={})
        return v
    
    @property
    def env_vars(self) -> dict[str, Any]:
        return {p.name: p.value for p in self.parameters}
    
    @property
    def args(self) -> dict[str, Any]:
        return {a.name: a.value for a in self.inputs}

    def get_thought_action_observation(self, include_action=True, include_thought=True) -> str:
        thought_action_observation = ""
        if self.thought and include_thought:
            thought_action_observation = f"Thought: {self.thought}\n"
        if include_action:
            tool_args = {inp.name: inp.value for inp in self.inputs}
            thought_action_observation += f"{self.name}{tool_args}\n"
        if self.observation is not None:
            thought_action_observation += f"Observation: {self.observation}\n"
        return thought_action_observation


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda x: f"dag-{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    thought: Optional[str] = None
    parameters: List[Any] = Field(default_factory=list)
    steps: List[WorkflowStep]
    outputs: List[OutputItem] = Field(default_factory=list)


class MemoryModel(BaseModel):
    goal: str
    plan: dict
    result: dict
    context: dict | None = Field(default=None, description="Used when plan is provided")


class AgentModel(BaseModel):
    name: str
    description: str
    version: str


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

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class ToolModel(BaseModel):
    """Model representing a tool that can be used by agents.
    
    Attributes:
        name: The tool name, optionally including version (e.g., 'tool@1.0.0')
        version: Tool version, extracted from name if present
        default_parameters: Default parameters for the tool
        parameters_spec: Parameter specification schema
        openai_function_spec: OpenAI function specification for the tool
    """
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
        """Generate pip dependency string for package installation."""
        return f"{self.package_name}=={self.version}" if self.version else self.package_name

    @property
    def package_name(self) -> str:
        """Generate pip dependency string for this tool.
        
        Returns:
            Pip dependency string with version if available
        """
        return f"{self.package_name}=={self.version}" if self.version else self.name

    @property
    def package_name(self) -> str:
        """Get the package name with underscores replaced by hyphens.
        
        Returns:
            Package name suitable for pip installation
        """
        return self.name.replace("_", "-")

    @property
    def function_name(self) -> str:
        """Extract function name from OpenAI function specification."""
        return self.openai_function_spec["function"]["name"]

    def render_function_spec(self) -> str:
        """Extract function name from OpenAI function specification.
        
        Returns:
            Function name from the OpenAI spec
        """
        return self.openai_function_spec["function"]["name"]

    def render_function_spec(self) -> str:
        """Render a human-readable function specification.
        
        Returns:
            Formatted string describing the function's interface
        """
        return f"""- {self.openai_function_spec["function"]["name"]}
    - description: {self.openai_function_spec["function"]["description"]}
    - parameters: {self.parameters_spec}
    - inputs: {self.openai_function_spec["function"]["parameters"]}
"""


class ParameterItem(BaseModel):
    """Represents a parameter with its name and value."""
    name: str
    value: Any


class InputItem(BaseModel):
    """Represents an input item with its name and value."""
    name: str
    value: Any


class OutputItem(BaseModel):
    """Represents an output item identifier."""
    name: str


class WorkflowStep(BaseModel):
    """Represents a single step in a workflow execution.
    
    Attributes:
        name: Human-readable name for this step
        tool: The tool to execute in this step
        thought: Optional reasoning or explanation for this step
        observation: Result or output observation from execution
        parameters: Tool-specific parameters for execution
        inputs: Input data for this step
        outputs: Expected outputs from this step
    """
    name: str
    tool: ToolModel
    thought: str | None = None
    observation: str | None = None
    parameters: list[ParameterItem] = Field(default_factory=list)
    inputs: list[InputItem] = Field(default_factory=list)
    outputs: list[OutputItem] = Field(default_factory=list)

    @property
    def task_id(self) -> str:
        """Generate a unique identifier for this workflow step.
        
        Returns:
            Formatted task identifier combining name and tool
        """
        return f"{self.name}: {self.tool}"

    @field_validator("tool", mode="before")
    @classmethod
    def validate_tool(cls, v: Any) -> "ToolModel":
        if isinstance(v, str):
            return ToolModel(name=v, openai_function_spec={})
        return v

    @property
    def env_vars(self) -> dict[str, str]:
        """Generate environment variables for tool execution.
        
        Returns:
            Dictionary of environment variables for this step
        """
        env_dict = {}
        if self.tool.default_parameters:
            # get default parameters
            env_dict.update(self.tool.default_parameters)
        if "params" in env_dict and isinstance(env_dict["params"], dict):
            del env_dict["params"]
            # replace with nested parameters
            # env_dict['params'] = ",".join([f"{p.name}=\"{p.value}\"" for p in self.parameters])
            env_dict.update({f"params__{p.name}": p.value for p in self.parameters})
        else:
            env_dict.update({p.name: p.value for p in self.parameters})
        return env_dict

    @property
    def args(self) -> dict[str, Any]:
        """Get input arguments as a dictionary.
        
        Returns:
            Dictionary mapping input names to their values
        """
        return {input_item.name: input_item.value for input_item in self.inputs}

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
    """Represents a complete workflow with multiple steps.
    
    Attributes:
        id: Unique workflow identifier (auto-generated)
        name: Human-readable workflow name
        description: Detailed description of workflow purpose
        thought: Optional reasoning or planning notes
        parameters: Global workflow parameters
        steps: Ordered list of workflow steps to execute
        outputs: Expected outputs from the complete workflow
    """
    id: str = Field(default_factory=lambda x: f"dag-{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    thought: str | None = None
    parameters: list[Any] = Field(default_factory=list)
    steps: list[WorkflowStep]
    outputs: list[OutputItem] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Represents an incoming chat request.
    
    Attributes:
        message: The user's message content
        action: Optional action to perform
        session_uuid: Optional session identifier for context
    """
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
    """Represents an agent that can be used for task delegation.
    
    Attributes:
        name: Agent name identifier
        description: Human-readable description of agent capabilities
        version: Agent version string
        peer_id: Optional P2P peer ID for direct delegation
    """
    name: str
    description: str
    version: str
    peer_id: str | None = Field(default=None, description="P2P peer ID for direct delegation")

    @computed_field
    def endpoint(self) -> str:
        """Generate the HTTP endpoint for this agent.
        
        Returns:
            HTTP endpoint URL for agent communication
            
        Note:
            TODO(team): Change this to use route mapping from AI registry
        """
        # TODO(team): Change this to the most appropriate way via route mapping from ai registry  # https://github.com/project/issues/123
        return f"http://{self.name}-serve-svc.praxis:8000"
        # return "http://localhost:8000"


class GoalModel(BaseModel):
    """Represents a goal to be achieved by an agent."""
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
    """Represents domain knowledge insights."""
    domain_knowledge: str = Field(..., description="Insight from the private domain knowledge")


class HandoffParamsModel(BaseModel):
    """Parameters for handing off tasks to other agents.
    
    Attributes:
        endpoint: Target endpoint URL for handoff
        path: URL path to append (supports templating)
        method: HTTP method for the request
        params: Additional request parameters
        target_peer_id: Optional P2P peer identifier
        goal: Optional goal to delegate
        plan: Optional execution plan to pass along
    """
    endpoint: str = Field(..., description="Endpoint to hand off to")
    path: str = Field(default="/{goal}", description="Path to append to the endpoint")
    method: str = Field("POST", description="HTTP method to use for the request")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters to pass in the request")
    target_peer_id: str | None = Field(default=None, description="Target peer ID for P2P delegation")
    goal: str | None = Field(default=None, description="Goal to delegate")
    plan: dict[str, Any] | None = Field(default=None, description="Optional plan to execute")

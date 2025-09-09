"""
Execution Contracts and Data Models for Dagger Engine

Python equivalent of Go's internal/contracts/execution.go
Defines the interfaces and data structures for tool execution.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import asyncio


class ExecutionEngine(ABC):
    """
    Abstract base class for execution engines.
    Python equivalent of Go's ExecutionEngine interface.
    """
    
    @abstractmethod
    async def execute(
        self, 
        contract: 'ToolContract', 
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a tool with the given contract and arguments.
        
        Args:
            contract: Tool execution configuration
            args: Dynamic arguments for the tool
            context: Optional execution context
            
        Returns:
            Execution result as string
            
        Raises:
            ExecutionError: If execution fails
        """
        pass

    async def validate_contract(self, contract: 'ToolContract') -> bool:
        """
        Validate if this engine can execute the given contract.
        
        Args:
            contract: Tool contract to validate
            
        Returns:
            True if contract is valid for this engine
        """
        return True

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Get capabilities supported by this engine.
        
        Returns:
            Dictionary of capabilities
        """
        return {}

    async def cleanup(self):
        """
        Cleanup resources used by the engine.
        """
        pass


class EngineType(str, Enum):
    """Engine types supported by the system."""
    DAGGER = "dagger"
    LOCAL = "local"
    REMOTE_MCP = "remote-mcp"


class DaggerEngineSpec(BaseModel):
    """
    Dagger engine specification.
    Equivalent to Go's EngineSpec for Dagger.
    """
    image: str = Field(..., description="Docker image to use")
    command: List[str] = Field(..., description="Command to execute")
    mounts: Dict[str, str] = Field(default_factory=dict, description="Host-to-container mount mapping")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    env_passthrough: List[str] = Field(default_factory=list, description="Host env vars to pass through")
    working_dir: Optional[str] = Field(None, description="Working directory in container")
    timeout: int = Field(default=300, description="Execution timeout in seconds")
    memory_limit: Optional[str] = Field(None, description="Memory limit (e.g., '512m')")
    cpu_limit: Optional[float] = Field(None, description="CPU limit (e.g., 1.5)")
    network: Optional[str] = Field(None, description="Network mode")
    privileged: bool = Field(default=False, description="Run in privileged mode")
    
    @validator('image')
    def validate_image(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Image must be a non-empty string")
        return v
    
    @validator('command')
    def validate_command(cls, v):
        if not v or not all(isinstance(cmd, str) for cmd in v):
            raise ValueError("Command must be a list of strings")
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v


class LocalEngineSpec(BaseModel):
    """
    Local execution engine specification.
    """
    command: List[str] = Field(..., description="Command to execute")
    shell: bool = Field(default=False, description="Execute command in shell")
    cwd: Optional[str] = Field(None, description="Working directory")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    timeout: int = Field(default=300, description="Execution timeout in seconds")
    capture_output: bool = Field(default=True, description="Capture stdout/stderr")
    
    @validator('command')
    def validate_command(cls, v):
        if not v:
            raise ValueError("Command cannot be empty")
        return v


class RemoteMCPEngineSpec(BaseModel):
    """
    Remote MCP engine specification.
    """
    address: str = Field(..., description="Remote MCP server address")
    timeout: int = Field(default=300, description="Request timeout in seconds")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    auth_token: Optional[str] = Field(None, description="Authentication token")
    
    @validator('address')
    def validate_address(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Address must be a non-empty string")
        return v


class ToolParameter(BaseModel):
    """
    Parameter definition for a tool.
    """
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, number, boolean, etc.)")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any = Field(default=None, description="Default value if not provided")


class ToolContract(BaseModel):
    """
    Tool execution contract.
    Python equivalent of Go's ToolContract.
    """
    engine: EngineType = Field(..., description="Execution engine type")
    name: str = Field(..., description="Tool name")
    engine_spec: Dict[str, Any] = Field(..., description="Engine-specific configuration")
    parameters: List[Union[ToolParameter, Dict[str, Any]]] = Field(default_factory=list, description="Tool parameters")
    description: Optional[str] = Field(None, description="Tool description")
    version: Optional[str] = Field(None, description="Tool version")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Name must be a non-empty string")
        return v
    
    def get_typed_spec(self) -> Union[DaggerEngineSpec, LocalEngineSpec, RemoteMCPEngineSpec]:
        """
        Get the engine spec as a typed object.
        
        Returns:
            Typed engine specification
            
        Raises:
            ValueError: If engine type is unknown or spec is invalid
        """
        if self.engine == EngineType.DAGGER:
            return DaggerEngineSpec(**self.engine_spec)
        elif self.engine == EngineType.LOCAL:
            return LocalEngineSpec(**self.engine_spec)
        elif self.engine == EngineType.REMOTE_MCP:
            return RemoteMCPEngineSpec(**self.engine_spec)
        else:
            raise ValueError(f"Unknown engine type: {self.engine}")
    
    @staticmethod
    def create_dagger_tool(
        name: str,
        image: str,
        command: List[str],
        mounts: Dict[str, str] = None,
        env: Dict[str, str] = None,
        env_passthrough: List[str] = None,
        working_dir: str = None,
        timeout: int = 300,
        description: str = None,
        **kwargs
    ) -> 'ToolContract':
        """Create a Dagger tool contract."""
        spec = {
            "image": image,
            "command": command,
            "mounts": mounts or {},
            "env": env or {},
            "env_passthrough": env_passthrough or [],
            "working_dir": working_dir,
            "timeout": timeout,
        }
        
        return ToolContract(
            engine=EngineType.DAGGER,
            name=name,
            engine_spec=spec,
            description=description
        )
    
    @staticmethod
    def create_local_tool(
        name: str,
        command: List[str],
        working_dir: str = None,
        env: Dict[str, str] = None,
        env_passthrough: List[str] = None,
        timeout: int = 300,
        description: str = None,
        shell: bool = False,
        capture_output: bool = True,
        **kwargs
    ) -> 'ToolContract':
        """Create a local tool contract."""
        spec = {
            "command": command,
            "shell": shell,
            "cwd": working_dir,
            "env": env or {},
            "timeout": timeout,
            "capture_output": capture_output,
        }
        
        return ToolContract(
            engine=EngineType.LOCAL,
            name=name,
            engine_spec=spec,
            description=description
        )


class ExecutionResult(BaseModel):
    """
    Result of tool execution.
    """
    success: bool = Field(..., description="Whether execution was successful")
    output: str = Field(default="", description="Execution output")
    error: Optional[str] = Field(None, description="Error message if failed")
    exit_code: Optional[int] = Field(None, description="Process exit code")
    duration: float = Field(..., description="Execution duration in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @staticmethod
    def error_result(
        error: str,
        exit_code: Optional[int] = None,
        output: str = "",
        duration: float = 0.0,
        metadata: Dict[str, Any] = None
    ) -> 'ExecutionResult':
        """Create an error result."""
        return ExecutionResult(
            success=False,
            output=output,
            error=error,
            exit_code=exit_code,
            duration=duration,
            metadata=metadata or {}
        )


class ExecutionError(Exception):
    """
    Exception raised when tool execution fails.
    """
    def __init__(self, message: str, exit_code: Optional[int] = None, output: Optional[str] = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.output = output


class ValidationError(Exception):
    """
    Exception raised when contract validation fails.
    """
    pass


class EngineRegistry:
    """
    Registry for execution engines.
    Manages multiple engine instances and provides engine selection.
    """
    
    def __init__(self):
        self._engines: Dict[str, ExecutionEngine] = {}
        self._default_engine: Optional[str] = None
    
    def register(self, name: str, engine: ExecutionEngine, is_default: bool = False):
        """
        Register an execution engine.
        
        Args:
            name: Engine name
            engine: Engine instance
            is_default: Whether this is the default engine
        """
        self._engines[name] = engine
        if is_default or not self._default_engine:
            self._default_engine = name
    
    def get(self, name: Optional[str] = None) -> ExecutionEngine:
        """
        Get an execution engine by name.
        
        Args:
            name: Engine name, uses default if None
            
        Returns:
            ExecutionEngine instance
            
        Raises:
            KeyError: If engine not found
        """
        engine_name = name or self._default_engine
        if not engine_name:
            raise KeyError("No engines registered")
        if engine_name not in self._engines:
            raise KeyError(f"Engine '{engine_name}' not found")
        return self._engines[engine_name]
    
    def list_engines(self) -> List[str]:
        """
        Get list of registered engine names.
        
        Returns:
            List of engine names
        """
        return list(self._engines.keys())
    
    def get_by_type(self, engine_type: EngineType) -> ExecutionEngine:
        """
        Get an execution engine by type.
        
        Args:
            engine_type: Type of engine to get
            
        Returns:
            ExecutionEngine instance
            
        Raises:
            KeyError: If no engine of the specified type is found
        """
        return self.get(engine_type.value)
    
    async def cleanup_all(self):
        """
        Cleanup all registered engines.
        """
        cleanup_tasks = [engine.cleanup() for engine in self._engines.values()]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
"""Execution Engine Module

Python implementation of execution engines for tool execution in containerized
and local environments. Provides compatibility with Go's Dagger Engine.
"""

from .contracts import (
    DaggerEngineSpec,
    EngineRegistry,
    EngineType,
    ExecutionEngine,
    ExecutionError,
    ExecutionResult,
    LocalEngineSpec,
    RemoteMCPEngineSpec,
    ToolContract,
    ValidationError,
)
from .engine import (
    DaggerExecutionEngine,
    DockerSDKExecutionEngine,
    LocalExecutionEngine,
    RemoteMCPEngine,
    create_dagger_engine,
    create_docker_sdk_engine,
    create_local_engine,
    create_remote_engine,
    is_docker_available,
    test_dagger_availability,
)

__all__ = [
    # Contracts and interfaces
    "ExecutionEngine",
    "ToolContract",
    "ExecutionResult",
    "ExecutionError",
    "ValidationError",
    "EngineType",
    "DaggerEngineSpec",
    "LocalEngineSpec",
    "RemoteMCPEngineSpec",
    "EngineRegistry",
    # Engine implementations
    "DaggerExecutionEngine",
    "LocalExecutionEngine",
    "DockerSDKExecutionEngine",
    "RemoteMCPEngine",
    # Factory functions
    "create_dagger_engine",
    "create_local_engine",
    "create_docker_sdk_engine",
    "create_remote_engine",
    "test_docker_availability",
    "test_dagger_availability",
]

"""A2A (Agent-to-Agent) Protocol Implementation

This module provides a complete implementation of the A2A protocol specification
from https://a2a-protocol.org with JSON-RPC 2.0 compliance.

Key components:
- models: Pydantic models for A2A protocol messages and structures
- task_manager: Task lifecycle management with event integration
- protocol: JSON-RPC message handling and method routing

Usage:
    from praxis_sdk.a2a import TaskManager, A2AProtocolHandler
    from praxis_sdk.a2a.models import create_task, create_user_message
"""

from .models import (
    # Agent card models
    A2AAgentCard,
    A2ACapabilities,
    # Error codes
    A2AErrorCode,
    A2AFile,
    A2AProvider,
    A2ASkill,
    Artifact,
    # JSON-RPC models
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    MessageRole,
    # Parameter models
    MessageSendParams,
    Part,
    PartKind,
    RPCError,
    # Core A2A models
    Task,
    TasksGetParams,
    TasksListParams,
    TaskState,
    TaskStatus,
    create_artifact,
    create_data_part,
    create_default_capabilities,
    create_file_part,
    create_jsonrpc_error_response,
    create_jsonrpc_response,
    create_message,
    create_praxis_skills,
    create_rpc_error,
    # Helper functions
    create_task,
    create_text_part,
)
from .protocol import (
    A2AMessageBuilder,
    A2AProtocolError,
    A2AProtocolHandler,
    get_task_status,
    list_agent_tasks,
    submit_user_message,
)
from .task_manager import (
    TaskExecutionTimeout,
    TaskManager,
    complete_task_with_text_response,
    create_user_task,
    fail_task_with_error,
)

__all__ = [
    # Models
    "Task",
    "TaskState",
    "TaskStatus",
    "Message",
    "MessageRole",
    "Part",
    "PartKind",
    "A2AFile",
    "Artifact",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "RPCError",
    "A2AAgentCard",
    "A2ASkill",
    "A2ACapabilities",
    "A2AProvider",
    "MessageSendParams",
    "TasksGetParams",
    "TasksListParams",
    "A2AErrorCode",
    # Task Manager
    "TaskManager",
    "TaskExecutionTimeout",
    # Protocol Handler
    "A2AProtocolHandler",
    "A2AProtocolError",
    "A2AMessageBuilder",
    # Helper functions
    "create_task",
    "create_message",
    "create_text_part",
    "create_file_part",
    "create_data_part",
    "create_artifact",
    "create_rpc_error",
    "create_jsonrpc_response",
    "create_jsonrpc_error_response",
    "create_default_capabilities",
    "create_praxis_skills",
    "create_user_task",
    "complete_task_with_text_response",
    "fail_task_with_error",
    "submit_user_message",
    "get_task_status",
    "list_agent_tasks",
]

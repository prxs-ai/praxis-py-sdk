"""Pydantic Models for API Request/Response Validation.

Comprehensive model definitions for all API endpoints with proper validation,
documentation, and error handling support.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, ValidationInfo, field_validator

from praxis_sdk.a2a.models import A2AAgentCard, Message, Task, TaskState

# Enums for API validation


class APIErrorCode(str, Enum):
    """API error codes."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    SERVICE_UNAVAILABLE = "service_unavailable"


class ExecutionStatus(str, Enum):
    """Command execution status."""

    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolExecutionEngine(str, Enum):
    """Tool execution engines."""

    DAGGER = "dagger"
    MCP = "mcp"
    P2P = "p2p"
    BUILTIN = "builtin"
    LOCAL = "local"


class WebSocketEventType(str, Enum):
    """WebSocket event types for client communication."""

    DSL_PROGRESS = "dslProgress"
    DSL_RESULT = "dslResult"
    WORKFLOW_START = "workflowStart"
    WORKFLOW_PROGRESS = "workflowProgress"
    WORKFLOW_COMPLETE = "workflowComplete"
    WORKFLOW_ERROR = "workflowError"
    NODE_STATUS_UPDATE = "nodeStatusUpdate"
    CHAT_MESSAGE = "chatMessage"
    TOOL_RESULT = "tool_result"
    TASK_UPDATE = "taskUpdate"
    EVENT_STREAM = "eventStream"
    ERROR = "error"
    SYSTEM = "system"


# Base Models


class APIResponse(BaseModel):
    """Base API response model."""

    success: bool = True
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str | None = None


class APIError(BaseModel):
    """API error response model."""

    success: bool = False
    error_code: APIErrorCode
    message: str
    details: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str | None = None


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int = Field(ge=0, description="Total number of items")
    count: int = Field(ge=0, description="Number of items in current page")
    offset: int = Field(ge=0, description="Offset from start")
    limit: int = Field(ge=1, le=1000, description="Maximum items per page")
    has_next: bool = Field(description="Whether there are more items")
    has_prev: bool = Field(description="Whether there are previous items")


# Request Models


class ExecuteDSLRequest(BaseModel):
    """Legacy DSL execution request."""

    dsl: str = Field(min_length=1, description="DSL command to execute")
    context_id: str | None = Field(None, description="Context ID for command execution")
    timeout: int | None = Field(
        300, ge=1, le=3600, description="Execution timeout in seconds"
    )

    @field_validator("dsl")
    @classmethod
    def validate_dsl(cls, v):
        """Validate DSL command."""
        if not v.strip():
            raise ValueError("DSL command cannot be empty")
        return v.strip()


class CreateTaskRequest(BaseModel):
    """Task creation request."""

    message: Message
    priority: int | None = Field(
        5, ge=1, le=10, description="Task priority (1=highest, 10=lowest)"
    )
    timeout: int | None = Field(
        300, ge=1, le=3600, description="Task timeout in seconds"
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Additional task metadata"
    )


class TaskQueryParams(BaseModel):
    """Task query parameters."""

    state: TaskState | None = Field(None, description="Filter by task state")
    context_id: str | None = Field(None, description="Filter by context ID")
    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of tasks to return"
    )
    offset: int = Field(0, ge=0, description="Number of tasks to skip")
    sort_by: str | None = Field("created_at", description="Sort field")
    sort_order: str | None = Field(
        "desc", pattern="^(asc|desc)$", description="Sort order"
    )


class ToolInvokeRequest(BaseModel):
    """Tool invocation request."""

    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    context_id: str | None = Field(None, description="Context ID for tool execution")
    timeout: int | None = Field(
        300, ge=1, le=3600, description="Tool timeout in seconds"
    )
    engine: ToolExecutionEngine | None = Field(
        None, description="Preferred execution engine"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class WebSocketSubscribeRequest(BaseModel):
    """WebSocket event subscription request."""

    event_types: list[str] = Field(description="List of event types to subscribe to")
    filter_criteria: dict[str, Any] | None = Field(
        None, description="Additional filter criteria"
    )


class AgentCardUpdateRequest(BaseModel):
    """Agent card update request."""

    name: str | None = Field(None, min_length=1, description="Agent name")
    description: str | None = Field(None, description="Agent description")
    url: HttpUrl | None = Field(None, description="Agent endpoint URL")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


# Response Models


class ExecuteDSLResponse(APIResponse):
    """DSL execution response."""

    task_id: str = Field(description="Created task ID")
    status: ExecutionStatus = Field(description="Current execution status")
    estimated_duration: int | None = Field(
        None, description="Estimated execution time in seconds"
    )


class TaskResponse(APIResponse):
    """Single task response."""

    task: Task = Field(description="Task details")


class TaskListResponse(APIResponse):
    """Task list response."""

    tasks: list[Task] = Field(description="List of tasks")
    pagination: PaginationMeta = Field(description="Pagination metadata")


class ToolInfo(BaseModel):
    """Tool information model."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameter schema"
    )
    enabled: bool = Field(True, description="Whether tool is enabled")
    engine: ToolExecutionEngine = Field(
        ToolExecutionEngine.BUILTIN, description="Execution engine"
    )
    timeout: int = Field(300, ge=1, le=3600, description="Default timeout in seconds")
    metadata: dict[str, Any] | None = Field(
        None, description="Additional tool metadata"
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "filename": {"type": "string", "required": True},
                    "content": {"type": "string", "required": True},
                },
                "enabled": True,
                "engine": "builtin",
                "timeout": 300,
            }
        }


class ToolsListResponse(APIResponse):
    """Tools list response."""

    tools: list[ToolInfo] = Field(description="Available tools")
    categories: dict[str, list[str]] | None = Field(None, description="Tool categories")
    total_enabled: int = Field(description="Number of enabled tools")


class ToolInvokeResponse(APIResponse):
    """Tool invocation response."""

    task_id: str = Field(description="Created task ID for tool execution")
    tool_name: str = Field(description="Invoked tool name")
    status: ExecutionStatus = Field(description="Current execution status")
    engine: ToolExecutionEngine = Field(description="Execution engine used")
    estimated_duration: int | None = Field(None, description="Estimated execution time")


class HealthResponse(APIResponse):
    """Health check response."""

    status: str = Field("healthy", description="Service status")
    version: str = Field(description="Service version")
    agent_name: str = Field(description="Agent name")
    uptime_seconds: float = Field(ge=0, description="Service uptime")
    components: dict[str, str] = Field(description="Component health status")
    system_info: dict[str, Any] | None = Field(None, description="System information")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "status": "healthy",
                "version": "1.0.0",
                "agent_name": "praxis-python-agent",
                "uptime_seconds": 3600.5,
                "components": {
                    "event_bus": "healthy",
                    "p2p_service": "healthy",
                    "websocket_manager": "healthy",
                    "task_manager": "healthy",
                },
            }
        }


class AgentCardResponse(APIResponse):
    """Agent card response."""

    card: A2AAgentCard = Field(description="Agent capability card")


class P2PPeersResponse(APIResponse):
    """P2P peers response."""

    peers: list[dict[str, Any]] = Field(description="Connected P2P peers")
    total: int = Field(ge=0, description="Total number of peers")
    connected: int = Field(ge=0, description="Number of connected peers")


class P2PCardsResponse(APIResponse):
    """P2P cards response."""

    cards: dict[str, A2AAgentCard] = Field(description="Peer agent cards")
    total: int = Field(ge=0, description="Total number of cards")


class StatisticsResponse(APIResponse):
    """System statistics response."""

    api_gateway: dict[str, Any] = Field(description="API gateway statistics")
    request_handlers: dict[str, Any] = Field(description="Request handler statistics")
    websocket_manager: dict[str, Any] = Field(
        description="WebSocket manager statistics"
    )
    event_bus: dict[str, Any] = Field(description="Event bus statistics")
    p2p_service: dict[str, Any] | None = Field(
        None, description="P2P service statistics"
    )
    system: dict[str, Any] = Field(description="System statistics")


# WebSocket Models


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""

    type: str = Field(description="Message type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Message payload")
    id: str = Field(default_factory=lambda: str(uuid4()), description="Message ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    correlation_id: str | None = Field(None, description="Correlation ID")

    class Config:
        schema_extra = {
            "example": {
                "type": "DSL_COMMAND",
                "payload": {"command": "write file test.txt"},
                "id": "msg-123",
                "timestamp": "2024-01-01T12:00:00Z",
                "correlation_id": "task-456",
            }
        }


class WebSocketEvent(BaseModel):
    """WebSocket event structure."""

    event_type: WebSocketEventType = Field(description="Event type")
    data: dict[str, Any] = Field(description="Event data")
    metadata: dict[str, Any] | None = Field(None, description="Event metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )


class WebSocketError(BaseModel):
    """WebSocket error message."""

    error_code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: dict[str, Any] | None = Field(None, description="Error details")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )


# Workflow Models (for frontend compatibility)


class WorkflowNode(BaseModel):
    """Workflow node definition."""

    id: str = Field(description="Node ID")
    type: str = Field(description="Node type")
    position: dict[str, float] = Field(description="Node position")
    data: dict[str, Any] = Field(description="Node data")


class WorkflowEdge(BaseModel):
    """Workflow edge definition."""

    id: str = Field(description="Edge ID")
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    data: dict[str, Any] | None = Field(None, description="Edge data")


class WorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    id: str = Field(description="Workflow ID")
    name: str = Field(description="Workflow name")
    nodes: list[WorkflowNode] = Field(description="Workflow nodes")
    edges: list[WorkflowEdge] = Field(description="Workflow edges")
    metadata: dict[str, Any] | None = Field(None, description="Workflow metadata")


class ExecuteWorkflowRequest(BaseModel):
    """Workflow execution request."""

    workflow: WorkflowDefinition = Field(description="Workflow to execute")
    context_id: str | None = Field(None, description="Execution context ID")
    timeout: int | None = Field(
        600, ge=1, le=3600, description="Workflow timeout in seconds"
    )


class WorkflowExecutionResponse(APIResponse):
    """Workflow execution response."""

    workflow_id: str = Field(description="Workflow execution ID")
    status: ExecutionStatus = Field(description="Execution status")
    estimated_duration: int | None = Field(None, description="Estimated execution time")


# Chat Models (for UI compatibility)


class ChatMessage(BaseModel):
    """Chat message model."""

    content: str = Field(description="Message content")
    sender: str = Field(description="Message sender (user/assistant/system)")
    message_type: str = Field("text", description="Message type")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    metadata: dict[str, Any] | None = Field(None, description="Message metadata")


class ChatResponse(APIResponse):
    """Chat response model."""

    message: ChatMessage = Field(description="Response message")
    context_id: str | None = Field(None, description="Chat context ID")


# Validation Utilities


class RequestValidator:
    """Request validation utilities."""

    @staticmethod
    def validate_task_id(task_id: str) -> str:
        """Validate task ID format."""
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")
        return task_id.strip()

    @staticmethod
    def validate_tool_name(tool_name: str) -> str:
        """Validate tool name format."""
        if not tool_name or not tool_name.strip():
            raise ValueError("Tool name cannot be empty")
        # Check for valid characters
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", tool_name):
            raise ValueError(
                "Tool name can only contain letters, numbers, underscores, and hyphens"
            )
        return tool_name.strip()

    @staticmethod
    def validate_context_id(context_id: str | None) -> str | None:
        """Validate context ID format."""
        if context_id is None:
            return None
        if not context_id.strip():
            return None
        return context_id.strip()

    @staticmethod
    def validate_pagination(limit: int, offset: int) -> tuple[int, int]:
        """Validate pagination parameters."""
        if limit < 1 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        return limit, offset


# Error Response Builders


def build_error_response(
    error_code: APIErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> APIError:
    """Build standardized error response."""
    return APIError(
        error_code=error_code, message=message, details=details, request_id=request_id
    )


def build_validation_error(errors: list[dict[str, Any]]) -> APIError:
    """Build validation error response."""
    return build_error_response(
        APIErrorCode.VALIDATION_ERROR,
        "Request validation failed",
        {"validation_errors": errors},
    )


def build_not_found_error(resource: str, identifier: str) -> APIError:
    """Build not found error response."""
    return build_error_response(
        APIErrorCode.NOT_FOUND,
        f"{resource} not found",
        {"resource": resource, "identifier": identifier},
    )


def build_server_error(message: str = "Internal server error") -> APIError:
    """Build server error response."""
    return build_error_response(APIErrorCode.SERVER_ERROR, message)

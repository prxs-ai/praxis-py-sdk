"""FastAPI-based API Gateway for Praxis Python SDK.

Provides comprehensive HTTP and WebSocket endpoints for agent interaction,
task management, and real-time event streaming with full A2A protocol support.
"""

import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import trio
import trio_asyncio
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

from praxis_sdk.a2a.models import (
    A2AAgentCard,
    A2AErrorCode,
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    MessageRole,
    Part,
    PartKind,
    RPCError,
    Task,
    TaskState,
    create_jsonrpc_error_response,
    create_jsonrpc_response,
    create_message,
    create_rpc_error,
    create_task,
    create_text_part,
)
from praxis_sdk.bus import Event, EventFilter, EventType, event_bus
from praxis_sdk.config import load_config

# API Request/Response Models


class ExecuteRequest(BaseModel):
    """Legacy DSL execution request."""

    dsl: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    agent: str
    version: str
    uptime_seconds: float = 0.0


class TaskListResponse(BaseModel):
    """Task list response."""

    tasks: list[Task]
    total: int
    offset: int
    limit: int


class ToolInfo(BaseModel):
    """Tool information."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ToolsListResponse(BaseModel):
    """Tools list response."""

    tools: list[ToolInfo]


class ToolInvokeRequest(BaseModel):
    """Tool invocation request."""

    parameters: dict[str, Any] = Field(default_factory=dict)
    context_id: str | None = None


class ToolInvokeResponse(BaseModel):
    """Tool invocation response."""

    task_id: str
    status: str = "submitted"
    message: str = "Tool execution started"


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None


class APIGateway:
    """FastAPI-based API Gateway for Praxis Python SDK.

    Handles HTTP endpoints, WebSocket connections, and integration
    with the event bus and A2A task management system.
    """

    def __init__(self):
        self.config = load_config()
        self.app = FastAPI(
            title="Praxis Agent API",
            description="REST API for Praxis Agent interactions",
            version="1.0.0",
            docs_url="/docs" if self.config.api.docs_enabled else None,
            redoc_url="/redoc" if self.config.api.docs_enabled else None,
        )

        # Task storage (in-memory for now, should be persistent in production)
        self.tasks: dict[str, Task] = {}
        self.active_websockets: dict[str, WebSocket] = {}

        # Agent capabilities
        self.agent_card: A2AAgentCard | None = None
        self.available_tools: list[ToolInfo] = []

        self._setup_middleware()
        self._setup_routes()
        self._setup_event_handlers()

    def _setup_middleware(self):
        """Setup FastAPI middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.api.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                agent=self.config.agents[0].name
                if self.config.agents
                else "praxis-agent",
                version="1.0.0",
            )

        @self.app.get("/agent/card", response_model=A2AAgentCard)
        async def get_agent_card():
            """Get agent capability card."""
            if not self.agent_card:
                raise HTTPException(status_code=503, detail="Agent card not available")
            return self.agent_card

        @self.app.post("/agent/execute")
        async def execute_command(request: ExecuteRequest | JSONRPCRequest):
            """Execute DSL command or A2A JSON-RPC request.
            Supports both legacy DSL format and A2A JSON-RPC format.
            """
            try:
                if isinstance(request, JSONRPCRequest):
                    return await self._handle_jsonrpc_request(request)
                return await self._handle_legacy_dsl(request.dsl)
            except Exception as e:
                logger.error(f"Error executing command: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/tasks/{task_id}", response_model=Task)
        async def get_task(task_id: str):
            """Get task by ID."""
            task = self.tasks.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return task

        @self.app.get("/tasks", response_model=TaskListResponse)
        async def list_tasks(
            state: TaskState | None = None,
            limit: int = Query(default=100, ge=1, le=1000),
            offset: int = Query(default=0, ge=0),
        ):
            """List tasks with optional filtering."""
            filtered_tasks = list(self.tasks.values())

            if state:
                filtered_tasks = [t for t in filtered_tasks if t.status.state == state]

            total = len(filtered_tasks)
            filtered_tasks = filtered_tasks[offset : offset + limit]

            return TaskListResponse(
                tasks=filtered_tasks, total=total, offset=offset, limit=limit
            )

        @self.app.post("/tasks")
        async def create_task_endpoint(message: Message):
            """Create a new task from a message."""
            task = create_task(initial_message=message)
            self.tasks[task.id] = task

            # Publish task creation event
            await event_bus.publish_data(
                EventType.TASK_CREATED,
                {"task_id": task.id, "task": task.dict()},
                source="api_gateway",
            )

            return task

        @self.app.get("/tools", response_model=ToolsListResponse)
        async def list_tools():
            """List available tools."""
            return ToolsListResponse(tools=self.available_tools)

        @self.app.post("/tools/{tool_name}/invoke", response_model=ToolInvokeResponse)
        async def invoke_tool(tool_name: str, request: ToolInvokeRequest):
            """Invoke a specific tool."""
            # Check if tool exists
            tool = next((t for t in self.available_tools if t.name == tool_name), None)
            if not tool:
                raise HTTPException(
                    status_code=404, detail=f"Tool '{tool_name}' not found"
                )

            if not tool.enabled:
                raise HTTPException(
                    status_code=400, detail=f"Tool '{tool_name}' is disabled"
                )

            # Create task for tool invocation
            message = create_message(
                role=MessageRole.USER,
                parts=[create_text_part(f"Invoke tool: {tool_name}")],
                context_id=request.context_id,
            )

            task = create_task(initial_message=message, context_id=request.context_id)
            self.tasks[task.id] = task

            # Publish tool invocation event
            await event_bus.publish_data(
                EventType.P2P_TOOL_REQUEST,
                {
                    "task_id": task.id,
                    "tool_name": tool_name,
                    "parameters": request.parameters,
                },
                source="api_gateway",
                correlation_id=task.id,
            )

            return ToolInvokeResponse(
                task_id=task.id,
                status="submitted",
                message=f"Tool '{tool_name}' execution started",
            )

        @self.app.websocket("/ws/events")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time event streaming."""
            await self._handle_websocket_connection(websocket)

    def _setup_event_handlers(self):
        """Setup event bus handlers for the API gateway."""

        async def handle_task_status_update(event: Event):
            """Handle task status updates."""
            if event.type in [
                EventType.TASK_STARTED,
                EventType.TASK_COMPLETED,
                EventType.TASK_FAILED,
            ]:
                task_id = event.data.get("task_id")
                if task_id and task_id in self.tasks:
                    # Update task status based on event
                    task = self.tasks[task_id]
                    if event.type == EventType.TASK_STARTED:
                        task.status.state = TaskState.WORKING
                    elif event.type == EventType.TASK_COMPLETED:
                        task.status.state = TaskState.COMPLETED
                    elif event.type == EventType.TASK_FAILED:
                        task.status.state = TaskState.FAILED

                    # Update timestamp
                    from datetime import datetime

                    task.status.timestamp = datetime.utcnow().isoformat() + "Z"

        # Subscribe to relevant events
        event_bus.subscribe(EventType.TASK_STARTED, handle_task_status_update)
        event_bus.subscribe(EventType.TASK_COMPLETED, handle_task_status_update)
        event_bus.subscribe(EventType.TASK_FAILED, handle_task_status_update)

    async def _handle_jsonrpc_request(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle A2A JSON-RPC request."""
        try:
            if request.method == "message/send":
                return await self._handle_message_send(request)
            if request.method == "tasks/get":
                return await self._handle_tasks_get(request)
            if request.method == "tasks/list":
                return await self._handle_tasks_list(request)
            error = create_rpc_error(
                A2AErrorCode.METHOD_NOT_FOUND, f"Method '{request.method}' not found"
            )
            return create_jsonrpc_error_response(request.id, error)

        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {e}")
            error = create_rpc_error(
                A2AErrorCode.INTERNAL_ERROR, "Internal server error", data=str(e)
            )
            return create_jsonrpc_error_response(request.id, error)

    async def _handle_message_send(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle message/send A2A method."""
        params = request.params or {}
        message_data = params.get("message", {})

        try:
            message = Message(**message_data)
            task = create_task(initial_message=message)
            self.tasks[task.id] = task

            # Publish DSL command event for processing
            await event_bus.publish_data(
                EventType.DSL_COMMAND_RECEIVED,
                {
                    "task_id": task.id,
                    "message": message.dict(),
                    "command": " ".join(
                        [
                            part.text or ""
                            for part in message.parts
                            if part.kind == PartKind.TEXT
                        ]
                    ),
                },
                source="api_gateway",
                correlation_id=task.id,
            )

            return create_jsonrpc_response(request.id, task.dict())

        except Exception as e:
            error = create_rpc_error(
                A2AErrorCode.INVALID_PARAMS, f"Invalid message parameters: {e}"
            )
            return create_jsonrpc_error_response(request.id, error)

    async def _handle_tasks_get(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle tasks/get A2A method."""
        params = request.params or {}
        task_id = params.get("id")

        if not task_id:
            error = create_rpc_error(
                A2AErrorCode.INVALID_PARAMS, "Missing required parameter: id"
            )
            return create_jsonrpc_error_response(request.id, error)

        task = self.tasks.get(task_id)
        if not task:
            error = create_rpc_error(
                A2AErrorCode.TASK_NOT_FOUND, f"Task not found: {task_id}"
            )
            return create_jsonrpc_error_response(request.id, error)

        return create_jsonrpc_response(request.id, task.dict())

    async def _handle_tasks_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle tasks/list A2A method."""
        params = request.params or {}
        state = params.get("state")
        limit = params.get("limit", 100)
        offset = params.get("offset", 0)

        filtered_tasks = list(self.tasks.values())

        if state:
            try:
                state_enum = TaskState(state)
                filtered_tasks = [
                    t for t in filtered_tasks if t.status.state == state_enum
                ]
            except ValueError:
                error = create_rpc_error(
                    A2AErrorCode.INVALID_PARAMS, f"Invalid state value: {state}"
                )
                return create_jsonrpc_error_response(request.id, error)

        total = len(filtered_tasks)
        filtered_tasks = filtered_tasks[offset : offset + limit]

        result = {
            "tasks": [task.dict() for task in filtered_tasks],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

        return create_jsonrpc_response(request.id, result)

    async def _handle_legacy_dsl(self, dsl_command: str) -> dict[str, Any]:
        """Handle legacy DSL command format."""
        # Create a message from DSL command
        message = create_message(
            role=MessageRole.USER, parts=[create_text_part(dsl_command)]
        )

        task = create_task(initial_message=message)
        self.tasks[task.id] = task

        # Publish DSL command event
        await event_bus.publish_data(
            EventType.DSL_COMMAND_RECEIVED,
            {"task_id": task.id, "command": dsl_command, "legacy_format": True},
            source="api_gateway",
            correlation_id=task.id,
        )

        return {
            "status": "submitted",
            "task_id": task.id,
            "message": "DSL command submitted for processing",
        }

    async def _handle_websocket_connection(self, websocket: WebSocket):
        """Handle WebSocket connection for real-time event streaming."""
        await websocket.accept()
        connection_id = str(uuid4())

        logger.info(f"WebSocket client connected: {connection_id}")

        # Add to active connections
        self.active_websockets[connection_id] = websocket

        # Create event filter for this connection (can be customized based on client needs)
        event_filter = EventFilter(
            event_types={
                EventType.DSL_COMMAND_PROGRESS,
                EventType.DSL_COMMAND_COMPLETED,
                EventType.TASK_STARTED,
                EventType.TASK_PROGRESS,
                EventType.TASK_COMPLETED,
                EventType.TASK_FAILED,
                EventType.WORKFLOW_STARTED,
                EventType.WORKFLOW_PROGRESS,
                EventType.WORKFLOW_COMPLETED,
                EventType.P2P_TOOL_RESPONSE,
            }
        )

        # Setup event streaming
        send_channel, receive_channel = trio.open_memory_channel(100)
        event_bus.websocket_manager.add_connection(
            connection_id, send_channel, event_filter
        )

        async def send_events():
            """Send events to WebSocket client."""
            try:
                async with receive_channel:
                    async for event in receive_channel:
                        message = WebSocketMessage(
                            type=event.type.value,
                            payload=event.data,
                            id=event.metadata.event_id,
                        )
                        await websocket.send_text(message.json())
            except Exception as e:
                logger.error(f"Error sending events to WebSocket: {e}")

        async def receive_messages():
            """Receive messages from WebSocket client."""
            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        message = json.loads(data)
                        await self._handle_websocket_message(connection_id, message)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON received from WebSocket: {data}")
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
            except Exception as e:
                logger.error(f"Error receiving WebSocket messages: {e}")

        try:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(trio_asyncio.aio_as_trio(send_events))
                nursery.start_soon(trio_asyncio.aio_as_trio(receive_messages))
        finally:
            # Cleanup
            self.active_websockets.pop(connection_id, None)
            event_bus.websocket_manager.remove_connection(connection_id)
            send_channel.close()
            logger.info(f"WebSocket connection cleanup completed: {connection_id}")

    async def _handle_websocket_message(
        self, connection_id: str, message: dict[str, Any]
    ):
        """Handle message received from WebSocket client."""
        try:
            msg_type = message.get("type")
            payload = message.get("payload", {})

            if msg_type == "DSL_COMMAND":
                command = payload.get("command", "")
                await self._handle_legacy_dsl(command)

            elif msg_type == "EXECUTE_WORKFLOW":
                workflow_id = payload.get("workflowId")
                # Handle workflow execution
                await event_bus.publish_data(
                    EventType.WORKFLOW_STARTED,
                    {
                        "workflow_id": workflow_id,
                        "nodes": payload.get("nodes", []),
                        "edges": payload.get("edges", []),
                    },
                    source="api_gateway",
                    correlation_id=workflow_id,
                )

            elif msg_type == "CHAT_MESSAGE":
                content = payload.get("content", "")
                sender = payload.get("sender", "user")

                # Handle chat message as DSL command
                if sender == "user":
                    await self._handle_legacy_dsl(content)

            else:
                logger.warning(f"Unknown WebSocket message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    def set_agent_card(self, agent_card: A2AAgentCard):
        """Set agent capability card."""
        self.agent_card = agent_card
        logger.info(f"Agent card updated: {agent_card.name}")

    def set_available_tools(self, tools: list[ToolInfo]):
        """Set available tools list."""
        self.available_tools = tools
        logger.info(f"Available tools updated: {len(tools)} tools")

    def get_stats(self) -> dict[str, Any]:
        """Get API gateway statistics."""
        return {
            "active_websockets": len(self.active_websockets),
            "total_tasks": len(self.tasks),
            "available_tools": len(self.available_tools),
            "task_states": {
                state.value: sum(
                    1 for task in self.tasks.values() if task.status.state == state
                )
                for state in TaskState
            },
        }


# Global API gateway instance
api_gateway = APIGateway()

# FastAPI app instance for external use
app = api_gateway.app

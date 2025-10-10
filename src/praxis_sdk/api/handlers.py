"""HTTP Request Handlers for Praxis Python SDK API Gateway.

Provides comprehensive request handling, validation, and business logic
for all API endpoints with full integration to A2A protocol and P2P services.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
import time

from fastapi import BackgroundTasks, Depends, HTTPException, Query
from loguru import logger

from praxis_sdk.a2a.models import (
    A2AAgentCard,
    A2AErrorCode,
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    MessageRole,
    MessageSendParams,
    Part,
    PartKind,
    RPCError,
    Task,
    TasksCancelParams,
    TasksGetParams,
    TasksListParams,
    TaskState,
    TaskStatus,
    create_jsonrpc_error_response,
    create_jsonrpc_response,
    create_message,
    create_rpc_error,
    create_task,
    create_text_part,
)
from praxis_sdk.a2a.task_manager import TaskManagerError
from praxis_sdk.api.gateway import ToolInfo
from praxis_sdk.bus import EventType, event_bus
from praxis_sdk.config import load_config


class RequestHandlers:
    """HTTP request handlers for all API endpoints.

    Provides business logic, validation, and integration with the underlying
    Praxis systems including A2A protocol, P2P services, and task management.
    """

    def __init__(self, agent=None):
        self.config = load_config()
        self.tasks: dict[str, Task] = {}
        self.agent_card: A2AAgentCard | None = None
        self.available_tools: list[ToolInfo] = []
        self.agent = agent  # Reference to PraxisAgent for DSL orchestration

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "dsl_commands": 0,
            "jsonrpc_requests": 0,
            "tool_invocations": 0,
            "task_creations": 0,
        }

    async def handle_health_check(self) -> dict[str, Any]:
        """Handle health check requests (Go-compatible shape)."""
        import time

        start_time = time.time()

        self.stats["total_requests"] += 1
        self.stats["successful_requests"] += 1

        agent_name = None
        agent_version = None

        if self.agent:
            agent_name = getattr(self.agent, "agent_name", None)
            agent_version = getattr(self.agent, "agent_version", None)

        if not agent_name:
            agent_name = (
                self.config.agents[0].name if self.config.agents else "praxis-agent"
            )

        if not agent_version:
            agent_version = os.getenv("AGENT_VERSION", "1.0.0")

        # Record health check metrics
        if self.agent and hasattr(self.agent, 'metrics_collector'):
            duration = time.time() - start_time
            self.agent.metrics_collector.record_health_check("healthy", duration)

        return {
            "status": "healthy",
            "agent": agent_name,
            "version": agent_version,
        }

    async def handle_get_agent_card(self) -> A2AAgentCard:
        """Handle agent card retrieval."""
        start_time = time.time()

        self.stats["total_requests"] += 1

        if not self.agent_card:
            self.stats["failed_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("GET", "/agent/card", 503, duration)

            raise HTTPException(status_code=503, detail="Agent card not available")

        self.stats["successful_requests"] += 1

        # Record metrics
        if self.agent and hasattr(self.agent, 'metrics_collector'):
            duration = time.time() - start_time
            self.agent.metrics_collector.record_http_request("GET", "/agent/card", 200, duration)

        return self.agent_card

    async def handle_execute_command(
        self,
        request: dict[str, Any] | JSONRPCRequest,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any] | JSONRPCResponse:
        """Handle command execution requests.
        Supports both legacy DSL format and A2A JSON-RPC format.
        """
        start_time = time.time()

        self.stats["total_requests"] += 1

        try:
            # Detect request format
            if isinstance(request, dict):
                if "jsonrpc" in request:
                    # A2A JSON-RPC format
                    jsonrpc_request = JSONRPCRequest(**request)
                    result = await self._handle_jsonrpc_request(
                        jsonrpc_request, background_tasks
                    )

                    # Record metrics
                    if self.agent and hasattr(self.agent, 'metrics_collector'):
                        duration = time.time() - start_time
                        self.agent.metrics_collector.record_http_request("POST", "/execute", 200, duration)

                    return result
                if "dsl" in request:
                    # Legacy DSL format
                    result = await self._handle_legacy_dsl_request(
                        request["dsl"], background_tasks
                    )

                    # Record metrics
                    if self.agent and hasattr(self.agent, 'metrics_collector'):
                        duration = time.time() - start_time
                        self.agent.metrics_collector.record_http_request("POST", "/execute", 200, duration)

                    return result

                # Record metrics for bad request
                if self.agent and hasattr(self.agent, 'metrics_collector'):
                    duration = time.time() - start_time
                    self.agent.metrics_collector.record_http_request("POST", "/execute", 400, duration)

                raise HTTPException(status_code=400, detail="Invalid request format")
            if isinstance(request, JSONRPCRequest):
                result = await self._handle_jsonrpc_request(request, background_tasks)

                # Record metrics
                if self.agent and hasattr(self.agent, 'metrics_collector'):
                    duration = time.time() - start_time
                    self.agent.metrics_collector.record_http_request("POST", "/execute", 200, duration)

                return result

            # Record metrics for unsupported format
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("POST", "/execute", 400, duration)

            raise HTTPException(status_code=400, detail="Unsupported request format")

        except HTTPException:
            self.stats["failed_requests"] += 1
            raise
        except Exception as e:
            self.stats["failed_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("POST", "/execute", 500, duration)

            logger.error(f"Error executing command: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _handle_jsonrpc_request(
        self, request: JSONRPCRequest, background_tasks: BackgroundTasks
    ) -> JSONRPCResponse:
        """Handle A2A JSON-RPC requests."""
        self.stats["jsonrpc_requests"] += 1

        try:
            # Structured A2A HTTP log
            try:
                params = request.params if isinstance(request.params, dict) else {}
                p = json.dumps(params, ensure_ascii=False)[:512]
            except Exception:
                p = str(request.params)[:256]
            logger.info(
                f"A2A HTTP REQUEST id={request.id} method={request.method} params={p}"
            )
            if request.method == "message/send":
                return await self._handle_message_send(request, background_tasks)
            if request.method == "tasks/get":
                return await self._handle_tasks_get(request)
            if request.method == "tasks/list":
                return await self._handle_tasks_list(request)
            if request.method == "tasks/cancel":
                return await self._handle_tasks_cancel(request)
            if request.method == "agent/getAuthenticatedExtendedCard":
                return await self._handle_get_authenticated_card(request)

            error = create_rpc_error(
                A2AErrorCode.METHOD_NOT_FOUND, f"Method '{request.method}' not found"
            )
            resp = create_jsonrpc_error_response(request.id, error)
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method={request.method} status=error code={error.code}"
            )
            return resp

        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {e}")
            error = create_rpc_error(
                A2AErrorCode.INTERNAL_ERROR, "Internal server error", data=str(e)
            )
            resp = create_jsonrpc_error_response(request.id, error)
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method={request.method} status=error code={A2AErrorCode.INTERNAL_ERROR}"
            )
            return resp

    async def _handle_message_send(
        self, request: JSONRPCRequest, background_tasks: BackgroundTasks
    ) -> JSONRPCResponse:
        """Handle message/send A2A method."""
        try:
            logger.info(f"A2A HTTP REQUEST id={request.id} method=message/send")
            params = MessageSendParams(**(request.params or {}))
            message = params.message

            # Create task from message
            task = create_task(initial_message=message)
            self.tasks[task.id] = task
            self.stats["task_creations"] += 1

            # Extract command text from message parts
            command_parts = [
                part.text
                for part in message.parts
                if part.kind == PartKind.TEXT and part.text
            ]
            command_text = " ".join(command_parts)

            # Process command asynchronously
            background_tasks.add_task(
                self._process_command_async, task.id, command_text, message.context_id
            )

            # Publish task creation event
            await event_bus.publish_data(
                EventType.TASK_CREATED,
                {
                    "task_id": task.id,
                    "context_id": task.context_id,
                    "command": command_text,
                    "method": "message/send",
                },
                source="request_handlers",
                correlation_id=task.id,
            )

            self.stats["successful_requests"] += 1
            resp = create_jsonrpc_response(request.id, task.dict())
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method=message/send status=ok task_id={task.id}"
            )
            return resp

        except Exception as e:
            error = create_rpc_error(
                A2AErrorCode.INVALID_PARAMS, f"Invalid message parameters: {e}"
            )
            resp = create_jsonrpc_error_response(request.id, error)
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method=message/send status=error code={error.code}"
            )
            return resp

    async def _handle_tasks_get(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle tasks/get A2A method."""
        try:
            logger.info(f"A2A HTTP REQUEST id={request.id} method=tasks/get")
            params = TasksGetParams(**(request.params or {}))
            task_id = params.id

            task = self.tasks.get(task_id)
            if not task:
                error = create_rpc_error(
                    A2AErrorCode.TASK_NOT_FOUND, f"Task not found: {task_id}"
                )
                return create_jsonrpc_error_response(request.id, error)

            self.stats["successful_requests"] += 1
            resp = create_jsonrpc_response(request.id, task.dict())
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method=tasks/get status=ok task_id={task_id}"
            )
            return resp

        except Exception as e:
            error = create_rpc_error(
                A2AErrorCode.INVALID_PARAMS, f"Invalid parameters: {e}"
            )
            resp = create_jsonrpc_error_response(request.id, error)
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method=tasks/get status=error code={error.code}"
            )
            return resp

    async def _handle_tasks_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle tasks/list A2A method."""
        try:
            logger.info(f"A2A HTTP REQUEST id={request.id} method=tasks/list")
            params = TasksListParams(**(request.params or {}))

            filtered_tasks = list(self.tasks.values())

            # Filter by state if specified
            if params.state:
                filtered_tasks = [
                    t for t in filtered_tasks if t.status.state == params.state
                ]

            # Apply pagination
            total = len(filtered_tasks)
            filtered_tasks = filtered_tasks[
                params.offset : params.offset + params.limit
            ]

            result = {
                "tasks": [task.dict() for task in filtered_tasks],
                "total": total,
                "offset": params.offset,
                "limit": params.limit,
            }

            self.stats["successful_requests"] += 1
            resp = create_jsonrpc_response(request.id, result)
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method=tasks/list status=ok count={len(result['tasks'])}"
            )
            return resp

        except Exception as e:
            error = create_rpc_error(
                A2AErrorCode.INVALID_PARAMS, f"Invalid parameters: {e}"
            )
            resp = create_jsonrpc_error_response(request.id, error)
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method=tasks/list status=error code={error.code}"
            )
            return resp

    async def _handle_tasks_cancel(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle tasks/cancel A2A method."""
        try:
            logger.info(f"A2A HTTP REQUEST id={request.id} method=tasks/cancel")
            params = TasksCancelParams(**(request.params or {}))

            cancelled_task: Task | None = None

            if self.agent and hasattr(self.agent, "task_manager"):
                try:
                    cancelled_task = await self.agent.task_manager.cancel_task(
                        params.id
                    )
                except TaskManagerError as tme:
                    rpc_err = tme.rpc_error
                    error = create_rpc_error(
                        rpc_err.code, rpc_err.message, rpc_err.data
                    )
                    return create_jsonrpc_error_response(request.id, error)
                except RPCError as rpc_err:
                    error = create_rpc_error(
                        rpc_err.code, rpc_err.message, rpc_err.data
                    )
                    return create_jsonrpc_error_response(request.id, error)

            if cancelled_task is None:
                task = self.tasks.get(params.id)
                if not task:
                    error = create_rpc_error(
                        A2AErrorCode.TASK_NOT_FOUND, f"Task not found: {params.id}"
                    )
                    return create_jsonrpc_error_response(request.id, error)

                task.status.state = TaskState.CANCELED
                task.status.timestamp = datetime.utcnow().isoformat() + "Z"
                cancelled_task = task

            self.tasks[cancelled_task.id] = cancelled_task

            await event_bus.publish_data(
                EventType.TASK_CANCELLED,
                {
                    "task_id": cancelled_task.id,
                    "status": cancelled_task.status.dict(),
                },
                source="request_handlers",
                correlation_id=cancelled_task.id,
            )

            self.stats["successful_requests"] += 1
            return create_jsonrpc_response(request.id, cancelled_task.dict())

        except Exception as e:
            error = create_rpc_error(
                A2AErrorCode.INVALID_PARAMS, f"Invalid tasks/cancel parameters: {e}"
            )
            resp = create_jsonrpc_error_response(request.id, error)
            logger.info(
                f"A2A HTTP RESPONSE id={request.id} method=tasks/cancel status=error code={error.code}"
            )
            return resp

    async def _handle_get_authenticated_card(
        self, request: JSONRPCRequest
    ) -> JSONRPCResponse:
        """Return authenticated agent card."""
        try:
            if not self.agent:
                raise ValueError("Agent context not attached")
            card = self.agent.get_authenticated_agent_card()
            return create_jsonrpc_response(request.id, card)
        except Exception as e:
            error = create_rpc_error(
                A2AErrorCode.INTERNAL_ERROR, f"Failed to fetch authenticated card: {e}"
            )
            return create_jsonrpc_error_response(request.id, error)

    async def _handle_legacy_dsl_request(
        self, dsl_command: str, background_tasks: BackgroundTasks
    ) -> dict[str, Any]:
        """Handle legacy DSL command requests by converting to A2A JSON-RPC."""
        self.stats["dsl_commands"] += 1

        try:
            message = create_message(
                role=MessageRole.USER, parts=[create_text_part(dsl_command)]
            )

            jsonrpc_request = JSONRPCRequest(
                id=str(uuid4()),
                method="message/send",
                params={"message": message.model_dump(by_alias=True)},
            )

            response = await self._handle_message_send(
                jsonrpc_request, background_tasks
            )

            await event_bus.publish_data(
                EventType.DSL_COMMAND_RECEIVED,
                {
                    "task_id": response.result.get("id") if response.result else None,
                    "command": dsl_command,
                    "legacy_format": True,
                },
                source="request_handlers",
                correlation_id=response.result.get("id") if response.result else None,
            )

            return response.model_dump(by_alias=True)

        except Exception as e:
            logger.error(f"Error handling legacy DSL request: {e}")
            raise

    async def handle_get_task(self, task_id: str) -> Task:
        """Handle single task retrieval."""
        start_time = time.time()

        self.stats["total_requests"] += 1

        task = self.tasks.get(task_id)
        if not task:
            self.stats["failed_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("GET", f"/tasks/{task_id}", 404, duration)

            raise HTTPException(status_code=404, detail="Task not found")

        self.stats["successful_requests"] += 1

        # Record metrics
        if self.agent and hasattr(self.agent, 'metrics_collector'):
            duration = time.time() - start_time
            self.agent.metrics_collector.record_http_request("GET", f"/tasks/{task_id}", 200, duration)

        return task

    async def handle_list_tasks(
        self,
        state: TaskState | None = None,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        """Handle task list requests."""
        start_time = time.time()

        self.stats["total_requests"] += 1

        try:
            filtered_tasks = list(self.tasks.values())

            # Filter by state if specified
            if state:
                filtered_tasks = [t for t in filtered_tasks if t.status.state == state]

            # Sort by creation time (newest first)
            filtered_tasks.sort(key=lambda t: t.status.timestamp, reverse=True)

            # Apply pagination
            total = len(filtered_tasks)
            paginated_tasks = filtered_tasks[offset : offset + limit]

            self.stats["successful_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("GET", "/tasks", 200, duration)

            return {
                "tasks": [task.dict() for task in paginated_tasks],
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < total,
            }

        except Exception as e:
            self.stats["failed_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("GET", "/tasks", 500, duration)

            logger.error(f"Error listing tasks: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_create_task(
        self, message: Message, background_tasks: BackgroundTasks
    ) -> Task:
        """Handle task creation requests."""
        start_time = time.time()

        self.stats["total_requests"] += 1
        self.stats["task_creations"] += 1

        try:
            # Create task from message
            task = create_task(initial_message=message)
            self.tasks[task.id] = task

            # Extract command text
            command_parts = [
                part.text
                for part in message.parts
                if part.kind == PartKind.TEXT and part.text
            ]
            command_text = " ".join(command_parts)

            # Process command asynchronously
            background_tasks.add_task(
                self._process_command_async, task.id, command_text, task.context_id
            )

            # Publish task creation event
            await event_bus.publish_data(
                EventType.TASK_CREATED,
                {
                    "task_id": task.id,
                    "context_id": task.context_id,
                    "command": command_text,
                },
                source="request_handlers",
                correlation_id=task.id,
            )

            self.stats["successful_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("POST", "/tasks", 200, duration)
                self.agent.metrics_collector.record_task_event("received", "message", "api")

            return task

        except Exception as e:
            self.stats["failed_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("POST", "/tasks", 500, duration)

            logger.error(f"Error creating task: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_list_tools(self) -> dict[str, Any]:
        """Handle tools list requests."""
        start_time = time.time()

        self.stats["total_requests"] += 1
        self.stats["successful_requests"] += 1

        # Record metrics
        if self.agent and hasattr(self.agent, 'metrics_collector'):
            duration = time.time() - start_time
            self.agent.metrics_collector.record_http_request("GET", "/tools", 200, duration)

        return {
            "tools": [tool.dict() for tool in self.available_tools],
            "total": len(self.available_tools),
            "enabled": len([t for t in self.available_tools if t.enabled]),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    async def handle_invoke_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        context_id: str | None = None,
        background_tasks: BackgroundTasks = None,
    ) -> dict[str, Any]:
        """Handle tool invocation requests."""
        start_time = time.time()

        self.stats["total_requests"] += 1
        self.stats["tool_invocations"] += 1

        try:
            # Check if tool exists
            tool = next((t for t in self.available_tools if t.name == tool_name), None)
            if not tool:
                self.stats["failed_requests"] += 1

                # Record metrics
                if self.agent and hasattr(self.agent, 'metrics_collector'):
                    duration = time.time() - start_time
                    self.agent.metrics_collector.record_http_request("POST", f"/tools/{tool_name}/invoke", 404, duration)

                raise HTTPException(
                    status_code=404, detail=f"Tool '{tool_name}' not found"
                )

            if not tool.enabled:
                self.stats["failed_requests"] += 1

                # Record metrics
                if self.agent and hasattr(self.agent, 'metrics_collector'):
                    duration = time.time() - start_time
                    self.agent.metrics_collector.record_http_request("POST", f"/tools/{tool_name}/invoke", 400, duration)

                raise HTTPException(
                    status_code=400, detail=f"Tool '{tool_name}' is disabled"
                )

            # Create task for tool invocation
            message = create_message(
                role=MessageRole.USER,
                parts=[create_text_part(f"Invoke tool: {tool_name}")],
                context_id=context_id,
            )

            task = create_task(initial_message=message, context_id=context_id)
            self.tasks[task.id] = task

            # Start tool execution asynchronously
            if background_tasks:
                background_tasks.add_task(
                    self._execute_tool_async, task.id, tool_name, parameters
                )

            # Publish tool invocation event
            await event_bus.publish_data(
                EventType.P2P_TOOL_REQUEST,
                {
                    "task_id": task.id,
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "context_id": context_id,
                },
                source="request_handlers",
                correlation_id=task.id,
            )

            self.stats["successful_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("POST", f"/tools/{tool_name}/invoke", 200, duration)

            return {
                "task_id": task.id,
                "status": "submitted",
                "message": f"Tool '{tool_name}' execution started",
                "tool_name": tool_name,
                "parameters": parameters,
            }

        except HTTPException:
            raise
        except Exception as e:
            self.stats["failed_requests"] += 1

            # Record metrics
            if self.agent and hasattr(self.agent, 'metrics_collector'):
                duration = time.time() - start_time
                self.agent.metrics_collector.record_http_request("POST", f"/tools/{tool_name}/invoke", 500, duration)

            logger.error(f"Error invoking tool '{tool_name}': {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _process_command_async(
        self, task_id: str, command: str, context_id: str | None = None
    ):
        """Process command asynchronously using DSL Orchestrator with LLM planning.
        This is the core method that handles natural language → LLM → tool execution → P2P coordination.
        """
        try:
            # Update task status to working
            task = self.tasks.get(task_id)
            if task:
                task.status.state = TaskState.WORKING
                task.status.timestamp = datetime.utcnow().isoformat() + "Z"

            # Publish task started event
            await event_bus.publish_data(
                EventType.TASK_STARTED,
                {"task_id": task_id, "command": command, "context_id": context_id},
                source="request_handlers",
                correlation_id=task_id,
            )

            # Publish DSL processing event
            await event_bus.publish_data(
                EventType.DSL_COMMAND_PROGRESS,
                {
                    "task_id": task_id,
                    "stage": "analyzing",
                    "message": "LLM analyzing command and planning execution",
                    "command": command,
                },
                source="request_handlers",
                correlation_id=task_id,
            )

            # REAL DSL ORCHESTRATION WITH LLM
            if self.agent and hasattr(self.agent, "dsl_orchestrator"):
                logger.info(
                    f"Processing command through DSL Orchestrator: {command[:100]}..."
                )

                # Build context for execution
                execution_context = {
                    "task_id": task_id,
                    "context_id": context_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "user_id": "api_user",
                    "session_id": context_id or task_id,
                }

                # Execute command through DSL orchestrator (this uses LLM for planning)
                result = await self.agent.dsl_orchestrator.execute_command(
                    command, execution_context
                )

                # Update task with real results
                if task:
                    if result.get("success", False):
                        task.status.state = TaskState.COMPLETED
                        task.status.message = (
                            "Command executed successfully via LLM orchestration"
                        )
                    else:
                        task.status.state = TaskState.FAILED
                        task.status.message = result.get(
                            "error", "Command execution failed"
                        )

                    task.status.timestamp = datetime.utcnow().isoformat() + "Z"

                # Publish completion event with real results
                await event_bus.publish_data(
                    EventType.TASK_COMPLETED,
                    {
                        "task_id": task_id,
                        "result": result,
                        "execution_method": "llm_orchestration",
                    },
                    source="request_handlers",
                    correlation_id=task_id,
                )

                logger.info(
                    f"Command completed via DSL Orchestrator: success={result.get('success', False)}"
                )

            else:
                # NO FALLBACK - System must work correctly or fail clearly
                error_msg = f"DSL orchestrator not available - cannot execute command: {command}"
                logger.error(error_msg)

                if task:
                    task.status.state = TaskState.FAILED
                    task.status.timestamp = datetime.utcnow().isoformat() + "Z"

                result = {"success": False, "error": error_msg, "task_id": task_id}

                await event_bus.publish_data(
                    EventType.TASK_COMPLETED,
                    {
                        "task_id": task_id,
                        "result": result,
                        "execution_method": "failed_no_orchestrator",
                    },
                    source="request_handlers",
                    correlation_id=task_id,
                )

        except Exception as e:
            logger.error(f"Error processing command for task {task_id}: {e}")

            # Update task status to failed
            task = self.tasks.get(task_id)
            if task:
                task.status.state = TaskState.FAILED
                task.status.message = str(e)
                task.status.timestamp = datetime.utcnow().isoformat() + "Z"

            # Publish failure event
            await event_bus.publish_data(
                EventType.TASK_FAILED,
                {"task_id": task_id, "error": str(e)},
                source="request_handlers",
                correlation_id=task_id,
            )

    async def _execute_tool_async(
        self, task_id: str, tool_name: str, parameters: dict[str, Any]
    ):
        """Execute tool asynchronously."""
        try:
            # Update task status
            task = self.tasks.get(task_id)
            if task:
                task.status.state = TaskState.WORKING
                task.status.timestamp = datetime.utcnow().isoformat() + "Z"

            # Publish tool execution start
            await event_bus.publish_data(
                EventType.TASK_STARTED,
                {"task_id": task_id, "tool_name": tool_name, "parameters": parameters},
                source="request_handlers",
                correlation_id=task_id,
            )

            # Simulate tool execution (in real implementation, this would route to P2P or local execution)
            await asyncio.sleep(2)

            # Complete tool execution
            if task:
                task.status.state = TaskState.COMPLETED
                task.status.timestamp = datetime.utcnow().isoformat() + "Z"

            # Publish tool response
            await event_bus.publish_data(
                EventType.P2P_TOOL_RESPONSE,
                {
                    "task_id": task_id,
                    "tool_name": tool_name,
                    "result": {
                        "status": "success",
                        "output": f"Tool {tool_name} executed successfully",
                    },
                },
                source="request_handlers",
                correlation_id=task_id,
            )

        except Exception as e:
            logger.error(f"Error executing tool {tool_name} for task {task_id}: {e}")

            # Update task status to failed
            task = self.tasks.get(task_id)
            if task:
                task.status.state = TaskState.FAILED
                task.status.timestamp = datetime.utcnow().isoformat() + "Z"

            # Publish failure event
            await event_bus.publish_data(
                EventType.TASK_FAILED,
                {"task_id": task_id, "tool_name": tool_name, "error": str(e)},
                source="request_handlers",
                correlation_id=task_id,
            )

    def set_agent_card(self, agent_card: A2AAgentCard):
        """Set the agent capability card."""
        self.agent_card = agent_card
        logger.info(f"Agent card updated: {agent_card.name}")

    def set_available_tools(self, tools: list[ToolInfo]):
        """Set the list of available tools."""
        self.available_tools = tools
        logger.info(f"Available tools updated: {len(tools)} tools")

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[Task]:
        """Get all tasks."""
        return list(self.tasks.values())

    def get_stats(self) -> dict[str, Any]:
        """Get handler statistics."""
        return {
            **self.stats,
            "task_states": {
                state.value: sum(
                    1 for task in self.tasks.values() if task.status.state == state
                )
                for state in TaskState
            },
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0
                else 0.0
            ),
            "error_rate": (
                self.stats["failed_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0
                else 0.0
            ),
        }


# Global request handlers instance (will be initialized in server.py)
request_handlers: RequestHandlers | None = None


def initialize_request_handlers(agent=None) -> RequestHandlers:
    """Initialize request handlers with agent reference for DSL orchestration."""
    global request_handlers
    request_handlers = RequestHandlers(agent=agent)
    return request_handlers


def get_request_handlers() -> RequestHandlers:
    """Get the initialized request handlers instance."""
    if request_handlers is None:
        raise RuntimeError(
            "Request handlers not initialized. Call initialize_request_handlers() first."
        )
    return request_handlers

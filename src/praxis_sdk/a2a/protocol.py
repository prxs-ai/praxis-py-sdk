"""A2A Protocol Handler

Implements the A2A (Agent-to-Agent) protocol with full JSON-RPC 2.0 compliance.
Handles task submission, status tracking, agent capability exchange, and
structured error handling according to the A2A specification.
"""

import json
from typing import Any, Dict, List, Optional, Union

import trio
from loguru import logger

from ..bus import EventBus, EventType, event_bus
from .models import (
    A2AAgentCard,
    A2AErrorCode,
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    MessageRole,
    MessageSendParams,
    RPCError,
    Task,
    TasksCancelParams,
    TasksGetParams,
    TasksListParams,
    TaskState,
    create_jsonrpc_error_response,
    create_jsonrpc_response,
    create_message,
    create_rpc_error,
    create_task,
    create_text_part,
)
from .task_manager import TaskManager, TaskManagerError


class A2AProtocolError(Exception):
    """Base exception for A2A protocol errors."""

    def __init__(self, code: int, message: str, data: Any | None = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"A2A Error {code}: {message}")


class A2AProtocolHandler:
    """Handles A2A protocol messages with full JSON-RPC 2.0 compliance.

    Supported methods:
    - message/send: Send a message and create/update a task
    - tasks/get: Retrieve a specific task by ID
    - tasks/list: List tasks with optional filtering
    - capabilities/get: Get agent capabilities
    - agent/card: Get agent card information
    """

    def __init__(
        self,
        task_manager: TaskManager,
        agent_card: A2AAgentCard,
        event_bus: EventBus | None = None,
        card_provider: Any | None = None,
    ):
        self.task_manager = task_manager
        self.agent_card = agent_card
        self.event_bus = event_bus or event_bus
        self._card_provider = card_provider

        # Method handlers
        self._method_handlers = {
            "message/send": self._handle_message_send,
            "tasks/get": self._handle_tasks_get,
            "tasks/list": self._handle_tasks_list,
            "tasks/cancel": self._handle_tasks_cancel,
            "capabilities/get": self._handle_capabilities_get,
            "agent/card": self._handle_agent_card,
            "agent/getAuthenticatedExtendedCard": self._handle_agent_authenticated_card,
            "agent/status": self._handle_agent_status,
        }

        logger.info("A2A Protocol Handler initialized")

    def set_agent_card(self, card: A2AAgentCard) -> None:
        """Update the agent card served by protocol handler."""
        self.agent_card = card

    async def handle_request(
        self, request_data: str | dict[str, Any]
    ) -> JSONRPCResponse:
        """Handle an incoming A2A JSON-RPC request.

        Args:
            request_data: JSON-RPC request as string or dict

        Returns:
            JSON-RPC response

        """
        try:
            # Parse request if it's a string
            if isinstance(request_data, str):
                try:
                    request_dict = json.loads(request_data)
                except json.JSONDecodeError as e:
                    return create_jsonrpc_error_response(
                        None,
                        create_rpc_error(
                            A2AErrorCode.PARSE_ERROR, f"Invalid JSON: {e}"
                        ),
                    )
            else:
                request_dict = request_data

            # Validate JSON-RPC request structure
            try:
                request = JSONRPCRequest(**request_dict)
            except Exception as e:
                return create_jsonrpc_error_response(
                    request_dict.get("id"),
                    create_rpc_error(
                        A2AErrorCode.INVALID_PARAMS, f"Invalid request format: {e}"
                    ),
                )

            # Structured request log
            try:
                log_params = request.params if isinstance(request.params, dict) else {}
                trunc_params = json.dumps(log_params)[:512]
            except Exception:
                trunc_params = str(request.params)[:256]
            logger.info(
                f"A2A REQUEST id={request.id} method={request.method} params={trunc_params}"
            )

            # Publish request received event
            await self.event_bus.publish_data(
                EventType.DSL_COMMAND_RECEIVED,
                {
                    "method": request.method,
                    "params": request.params,
                    "request_id": request.id,
                },
                source="a2a_protocol",
            )

            # Route to appropriate handler
            if request.method not in self._method_handlers:
                return create_jsonrpc_error_response(
                    request.id,
                    create_rpc_error(
                        A2AErrorCode.METHOD_NOT_FOUND,
                        f"Method '{request.method}' not found",
                    ),
                )

            handler = self._method_handlers[request.method]

            try:
                result = await handler(request.params or {})

                # Publish success event
                await self.event_bus.publish_data(
                    EventType.DSL_COMMAND_COMPLETED,
                    {
                        "method": request.method,
                        "request_id": request.id,
                        "success": True,
                    },
                    source="a2a_protocol",
                )

                logger.info(
                    f"A2A RESPONSE id={request.id} method={request.method} status=ok"
                )
                return create_jsonrpc_response(request.id, result)

            except A2AProtocolError as e:
                logger.error(f"A2A Protocol Error in {request.method}: {e}")

                # Publish error event
                await self.event_bus.publish_data(
                    EventType.DSL_COMMAND_COMPLETED,
                    {
                        "method": request.method,
                        "request_id": request.id,
                        "success": False,
                        "error": e.message,
                    },
                    source="a2a_protocol",
                )

                logger.info(
                    f"A2A RESPONSE id={request.id} method={request.method} status=error code={e.code}"
                )
                return create_jsonrpc_error_response(
                    request.id, create_rpc_error(e.code, e.message, e.data)
                )

            except Exception as e:
                logger.error(f"Unexpected error in {request.method}: {e}")

                # Publish error event
                await self.event_bus.publish_data(
                    EventType.DSL_COMMAND_COMPLETED,
                    {
                        "method": request.method,
                        "request_id": request.id,
                        "success": False,
                        "error": str(e),
                    },
                    source="a2a_protocol",
                )

                logger.info(
                    f"A2A RESPONSE id={request.id} method={request.method} status=error code={A2AErrorCode.INTERNAL_ERROR}"
                )
                return create_jsonrpc_error_response(
                    request.id,
                    create_rpc_error(
                        A2AErrorCode.INTERNAL_ERROR, "Internal server error"
                    ),
                )

        except Exception as e:
            logger.error(f"Critical error handling A2A request: {e}")
            return create_jsonrpc_error_response(
                None,
                create_rpc_error(A2AErrorCode.INTERNAL_ERROR, "Critical server error"),
            )

    async def _handle_message_send(self, params: dict[str, Any]) -> Task:
        """Handle message/send method.

        Creates a new task from a user message or adds to existing task.
        """
        try:
            # Validate parameters
            message_params = MessageSendParams(**params)
            message = message_params.message

            # Check if this is for an existing task
            if message.task_id:
                # Add message to existing task
                existing_task = await self.task_manager.get_task(message.task_id)
                if not existing_task:
                    raise A2AProtocolError(
                        A2AErrorCode.TASK_NOT_FOUND,
                        f"Task '{message.task_id}' not found",
                    )

                # Add message to history
                await self.task_manager.add_message_to_history(message.task_id, message)

                # If task was in input-required state, move to working
                if existing_task.status.state == TaskState.INPUT_REQUIRED:
                    await self.task_manager.update_task_status(
                        message.task_id, TaskState.WORKING
                    )

                return existing_task
            # Create new task
            task = await self.task_manager.create_task(
                message, context_id=message.context_id
            )

            logger.info(f"Created new task {task.id} from message/send")
            return task

        except Exception as e:
            if isinstance(e, A2AProtocolError):
                raise
            raise A2AProtocolError(
                A2AErrorCode.INVALID_PARAMS, f"Invalid message/send parameters: {e}"
            )

    async def _handle_tasks_get(self, params: dict[str, Any]) -> Task:
        """Handle tasks/get method.

        Retrieves a specific task by ID.
        """
        try:
            # Validate parameters
            get_params = TasksGetParams(**params)

            task = await self.task_manager.get_task(get_params.id)
            if not task:
                raise A2AProtocolError(
                    A2AErrorCode.TASK_NOT_FOUND, f"Task '{get_params.id}' not found"
                )

            return task

        except Exception as e:
            if isinstance(e, A2AProtocolError):
                raise
            raise A2AProtocolError(
                A2AErrorCode.INVALID_PARAMS, f"Invalid tasks/get parameters: {e}"
            )

    async def _handle_tasks_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tasks/list method.

        Lists tasks with optional filtering and pagination.
        """
        try:
            # Validate parameters
            list_params = TasksListParams(**params)

            tasks = await self.task_manager.list_tasks(
                state=list_params.state,
                limit=list_params.limit,
                offset=list_params.offset,
            )

            # Get total count for pagination info
            all_tasks = await self.task_manager.list_tasks()
            total_count = len(all_tasks)

            # Filter for state-specific count if needed
            if list_params.state:
                state_tasks = [
                    t for t in all_tasks if t.status.state == list_params.state
                ]
                filtered_count = len(state_tasks)
            else:
                filtered_count = total_count

            return {
                "tasks": [task.dict() for task in tasks],
                "pagination": {
                    "total": filtered_count,
                    "limit": list_params.limit,
                    "offset": list_params.offset,
                    "has_more": list_params.offset + len(tasks) < filtered_count,
                },
            }

        except Exception as e:
            if isinstance(e, A2AProtocolError):
                raise
            raise A2AProtocolError(
                A2AErrorCode.INVALID_PARAMS, f"Invalid tasks/list parameters: {e}"
            )

    async def _handle_tasks_cancel(self, params: dict[str, Any]) -> Task:
        """Handle tasks/cancel method."""
        try:
            cancel_params = TasksCancelParams(**params)
            task = await self.task_manager.cancel_task(cancel_params.id)
            return task
        except TaskManagerError as tme:
            rpc_err = tme.rpc_error
            raise A2AProtocolError(rpc_err.code, rpc_err.message, rpc_err.data)
        except RPCError as e:
            raise A2AProtocolError(e.code, e.message, e.data)
        except Exception as e:
            if isinstance(e, A2AProtocolError):
                raise
            raise A2AProtocolError(
                A2AErrorCode.INVALID_PARAMS, f"Invalid tasks/cancel parameters: {e}"
            )

    async def _handle_capabilities_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle capabilities/get method.

        Returns agent capabilities.
        """
        return {
            "capabilities": self.agent_card.capabilities.dict(),
            "skills": [skill.dict() for skill in self.agent_card.skills],
            "supported_transports": self.agent_card.supported_transports,
            "protocol_version": self.agent_card.protocol_version,
        }

    async def _handle_agent_card(self, params: dict[str, Any]) -> A2AAgentCard:
        """Handle agent/card method.

        Returns the complete agent card.
        """
        return self.agent_card

    async def _handle_agent_authenticated_card(
        self, params: dict[str, Any]
    ) -> A2AAgentCard:
        """Handle agent/getAuthenticatedExtendedCard method."""
        if self._card_provider:
            card = self._card_provider()
            if card:
                self.agent_card = card
                return card

        if not self.agent_card:
            raise A2AProtocolError(
                A2AErrorCode.INTERNAL_ERROR, "A2A card not initialized"
            )

        return self.agent_card

    async def _handle_agent_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle agent/status method.

        Returns agent status and statistics.
        """
        task_counts = await self.task_manager.get_task_count_by_state()

        return {
            "agent": {
                "name": self.agent_card.name,
                "version": self.agent_card.version,
                "status": "running",
            },
            "tasks": {
                "counts_by_state": {
                    state.value: count for state, count in task_counts.items()
                },
                **self.task_manager.get_stats(),
            },
            "uptime_seconds": 0,  # TODO: Track actual uptime
            "timestamp": trio.current_time(),
        }

    def get_supported_methods(self) -> list[str]:
        """Get list of supported A2A methods."""
        return list(self._method_handlers.keys())


class A2AMessageBuilder:
    """Helper class for building A2A messages and responses."""

    @staticmethod
    def create_user_message(text: str, context_id: str | None = None) -> Message:
        """Create a user message with text content."""
        parts = [create_text_part(text)]
        return create_message(MessageRole.USER, parts, context_id=context_id)

    @staticmethod
    def create_agent_response(text: str, task_id: str, context_id: str) -> Message:
        """Create an agent response message."""
        parts = [create_text_part(text)]
        return create_message(
            MessageRole.AGENT, parts, task_id=task_id, context_id=context_id
        )

    @staticmethod
    def create_message_send_request(
        message: Message, request_id: str | int
    ) -> JSONRPCRequest:
        """Create a message/send JSON-RPC request."""
        return JSONRPCRequest(
            id=request_id, method="message/send", params={"message": message.dict()}
        )

    @staticmethod
    def create_tasks_get_request(task_id: str, request_id: str | int) -> JSONRPCRequest:
        """Create a tasks/get JSON-RPC request."""
        return JSONRPCRequest(id=request_id, method="tasks/get", params={"id": task_id})

    @staticmethod
    def create_tasks_list_request(
        state: TaskState | None = None,
        limit: int = 100,
        offset: int = 0,
        request_id: str | int = 1,
    ) -> JSONRPCRequest:
        """Create a tasks/list JSON-RPC request."""
        params = {
            "limit": limit,
            "offset": offset,
        }

        if state:
            params["state"] = state.value

        return JSONRPCRequest(id=request_id, method="tasks/list", params=params)


# Utility functions for common A2A operations


async def submit_user_message(
    protocol_handler: A2AProtocolHandler,
    message_text: str,
    context_id: str | None = None,
) -> Task:
    """Submit a user message and create a task.

    This is a convenience function that creates a user message and submits it
    via the A2A protocol handler.
    """
    message = A2AMessageBuilder.create_user_message(message_text, context_id)

    request = A2AMessageBuilder.create_message_send_request(message, "user-submit")
    response = await protocol_handler.handle_request(request.dict())

    if response.error:
        raise A2AProtocolError(
            response.error.code, response.error.message, response.error.data
        )

    # Parse task from response
    return Task(**response.result)


async def get_task_status(protocol_handler: A2AProtocolHandler, task_id: str) -> Task:
    """Get the current status of a task.

    This is a convenience function for retrieving task status via A2A protocol.
    """
    request = A2AMessageBuilder.create_tasks_get_request(task_id, "status-check")
    response = await protocol_handler.handle_request(request.dict())

    if response.error:
        raise A2AProtocolError(
            response.error.code, response.error.message, response.error.data
        )

    return Task(**response.result)


async def list_agent_tasks(
    protocol_handler: A2AProtocolHandler,
    state: TaskState | None = None,
    limit: int = 100,
) -> list[Task]:
    """List tasks from the agent.

    This is a convenience function for listing tasks via A2A protocol.
    """
    request = A2AMessageBuilder.create_tasks_list_request(state, limit, 0, "list-tasks")
    response = await protocol_handler.handle_request(request.dict())

    if response.error:
        raise A2AProtocolError(
            response.error.code, response.error.message, response.error.data
        )

    tasks_data = response.result["tasks"]
    return [Task(**task_data) for task_data in tasks_data]

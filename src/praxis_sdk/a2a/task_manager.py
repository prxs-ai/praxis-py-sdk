"""A2A Task Manager

Manages the complete lifecycle of A2A tasks including creation, status updates,
artifact generation, and event publishing. Integrates with the Praxis event bus
for real-time status updates and WebSocket streaming.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import trio
from loguru import logger

from ..bus import EventBus, EventType, event_bus
from .models import (
    A2AErrorCode,
    Artifact,
    Message,
    MessageRole,
    Part,
    RPCError,
    Task,
    TaskState,
    TaskStatus,
    create_artifact,
    create_message,
    create_rpc_error,
    create_task,
    create_text_part,
)

TERMINAL_STATES: set[TaskState] = {
    TaskState.COMPLETED,
    TaskState.FAILED,
    TaskState.CANCELED,
    TaskState.REJECTED,
}


class TaskExecutionTimeout(Exception):
    """Raised when task execution exceeds timeout."""


class TaskManagerError(Exception):
    """Wrap A2A RPC errors produced by the task manager."""

    def __init__(self, rpc_error: RPCError):
        self.rpc_error = rpc_error
        super().__init__(rpc_error.message)


class TaskManager:
    """Manages A2A task lifecycle with full event integration.

    Features:
    - Task creation and lifecycle management
    - Status transition validation
    - Event publishing for all state changes
    - Artifact generation and management
    - Cleanup of completed tasks
    - Timeout handling
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        default_timeout: int = 300,  # 5 minutes
        cleanup_interval: int = 3600,  # 1 hour
        max_history_size: int = 1000,
    ):
        self.event_bus = event_bus or event_bus
        self.default_timeout = default_timeout
        self.cleanup_interval = cleanup_interval
        self.max_history_size = max_history_size

        # Task storage
        self._tasks: dict[str, Task] = {}
        self._task_timeouts: dict[str, float] = {}

        # Synchronization (asyncio lock to avoid re-entrant trio lock issues in mixed contexts)
        self._lock = asyncio.Lock()

        # Background cleanup task
        self._cleanup_task: trio.lowlevel.Task | None = None
        self._running = False

        # Statistics
        self.stats = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "tasks_timeout": 0,
            "artifacts_created": 0,
            "cleanup_runs": 0,
        }

        logger.info("A2A TaskManager initialized")

    async def start(self, nursery: trio.Nursery) -> None:
        """Start the task manager with background cleanup."""
        if self._running:
            return

        self._running = True

        # Start background cleanup task
        nursery.start_task(self._cleanup_loop)

        logger.info("TaskManager started with background cleanup")

    async def stop(self) -> None:
        """Stop the task manager."""
        self._running = False
        logger.info("TaskManager stopped")

    async def create_task(
        self,
        initial_message: Message,
        context_id: str | None = None,
        timeout: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task from an initial message.

        Args:
            initial_message: The initial user message
            context_id: Optional context ID for grouping related tasks
            timeout: Task timeout in seconds (default: self.default_timeout)
            metadata: Additional task metadata

        Returns:
            Created task in 'submitted' state

        """
        async with self._lock:
            # Create task with proper IDs
            task = create_task(context_id, initial_message)

            if metadata:
                task.metadata = metadata

            # Set timeout
            task_timeout = timeout or self.default_timeout
            self._task_timeouts[task.id] = time.time() + task_timeout

            # Store task
            self._tasks[task.id] = task
            self.stats["tasks_created"] += 1

            logger.info(f"[TaskID: {task.id}] Task created in 'submitted' state")

            # Publish event
            await self.event_bus.publish_data(
                EventType.TASK_CREATED,
                {
                    "task_id": task.id,
                    "context_id": task.context_id,
                    "task": task.dict(),
                    "timeout": task_timeout,
                },
                source="task_manager",
            )

            return task

    async def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def list_tasks(
        self,
        state: TaskState | None = None,
        context_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks with optional filtering.

        Args:
            state: Filter by task state
            context_id: Filter by context ID
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            List of matching tasks

        """
        async with self._lock:
            tasks = list(self._tasks.values())

            # Apply filters
            if state:
                tasks = [t for t in tasks if t.status.state == state]

            if context_id:
                tasks = [t for t in tasks if t.context_id == context_id]

            # Sort by creation time (most recent first)
            tasks.sort(key=lambda t: t.status.timestamp, reverse=True)

            # Apply pagination
            return tasks[offset : offset + limit]

    async def update_task_status(
        self,
        task_id: str,
        new_state: TaskState,
        agent_message: Message | None = None,
        error_details: str | None = None,
    ) -> bool:
        """Update task status with validation.

        Args:
            task_id: Task ID to update
            new_state: New task state
            agent_message: Optional agent response message
            error_details: Error details for failed states

        Returns:
            True if update was successful, False otherwise

        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(
                    f"[TaskID: {task_id}] Attempted to update non-existent task"
                )
                return False

            old_state = task.status.state

            # Validate state transition
            if not self._is_valid_transition(old_state, new_state):
                logger.error(
                    f"[TaskID: {task_id}] Invalid state transition: {old_state} -> {new_state}"
                )
                return False

            # Update status
            task.status.state = new_state
            task.status.timestamp = datetime.utcnow().isoformat() + "Z"

            if agent_message:
                task.status.message = agent_message
                # Ensure message has correct IDs
                agent_message.task_id = task_id
                agent_message.context_id = task.context_id
                task.history.append(agent_message)

            # Update statistics
            if new_state == TaskState.COMPLETED:
                self.stats["tasks_completed"] += 1
            elif new_state == TaskState.FAILED:
                self.stats["tasks_failed"] += 1
            elif new_state == TaskState.CANCELED:
                self.stats["tasks_cancelled"] += 1

            logger.info(
                f"[TaskID: {task_id}] Status updated: {old_state} -> {new_state}"
            )

            # Publish event
            await self.event_bus.publish_data(
                EventType.TASK_PROGRESS,
                {
                    "task_id": task_id,
                    "old_state": old_state,
                    "new_state": new_state,
                    "status": task.status.dict(),
                    "error_details": error_details,
                },
                source="task_manager",
            )

            # Publish completion event if task is done
            if new_state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED]:
                event_type = (
                    EventType.TASK_COMPLETED
                    if new_state == TaskState.COMPLETED
                    else EventType.TASK_FAILED
                    if new_state == TaskState.FAILED
                    else EventType.TASK_CANCELLED
                )
                await self.event_bus.publish_data(
                    event_type,
                    {
                        "task_id": task_id,
                        "task": task.dict(),
                        "error_details": error_details,
                    },
                    source="task_manager",
                )

            return True

    async def cancel_task(self, task_id: str, reason: str | None = None) -> Task:
        """Cancel a task if it is not in a terminal state."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise TaskManagerError(
                    create_rpc_error(
                        A2AErrorCode.TASK_NOT_FOUND, f"Task not found: {task_id}"
                    )
                )

            if task.status.state in TERMINAL_STATES:
                raise TaskManagerError(
                    create_rpc_error(
                        A2AErrorCode.TASK_NOT_CANCELABLE,
                        f"Task {task_id} is already in terminal state {task.status.state.value}",
                    )
                )

            context_id = task.context_id

        cancel_message: Message | None = None
        if reason:
            cancel_message = create_message(
                MessageRole.AGENT,
                [create_text_part(reason)],
                task_id=task_id,
                context_id=context_id,
            )

        await self.update_task_status(
            task_id, TaskState.CANCELED, cancel_message, reason
        )

        async with self._lock:
            self._task_timeouts.pop(task_id, None)
            return self._tasks[task_id]

    async def add_artifact(
        self,
        task_id: str,
        name: str,
        parts: list[Part],
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact | None:
        """Add an artifact to a task.

        Args:
            task_id: Task ID to add artifact to
            name: Artifact name
            parts: Artifact content parts
            description: Optional artifact description
            metadata: Additional artifact metadata

        Returns:
            Created artifact or None if task not found

        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(
                    f"[TaskID: {task_id}] Attempted to add artifact to non-existent task"
                )
                return None

            artifact = create_artifact(name, parts, description, metadata)
            task.artifacts.append(artifact)
            self.stats["artifacts_created"] += 1

            logger.info(
                f"[TaskID: {task_id}] Artifact '{name}' added (ID: {artifact.artifact_id})"
            )

            # Publish event
            await self.event_bus.publish_data(
                EventType.TASK_PROGRESS,
                {
                    "task_id": task_id,
                    "artifact": artifact.dict(),
                    "type": "artifact_added",
                },
                source="task_manager",
            )

            return artifact

    async def add_message_to_history(self, task_id: str, message: Message) -> bool:
        """Add a message to task history."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(
                    f"[TaskID: {task_id}] Attempted to add message to non-existent task"
                )
                return False

            # Ensure message has correct IDs
            message.task_id = task_id
            message.context_id = task.context_id

            task.history.append(message)

            # Limit history size
            if len(task.history) > self.max_history_size:
                task.history = task.history[-self.max_history_size :]
                logger.debug(
                    f"[TaskID: {task_id}] Trimmed history to {self.max_history_size} messages"
                )

            logger.debug(
                f"[TaskID: {task_id}] Message '{message.message_id}' added to history"
            )

            return True

    async def get_task_count_by_state(self) -> dict[TaskState, int]:
        """Get count of tasks by state."""
        async with self._lock:
            counts = {state: 0 for state in TaskState}

            for task in self._tasks.values():
                counts[task.status.state] += 1

            return counts

    async def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """Clean up completed/failed tasks older than specified time.

        Args:
            older_than_hours: Remove tasks completed more than this many hours ago

        Returns:
            Number of tasks cleaned up

        """
        async with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
            cutoff_timestamp = cutoff_time.isoformat() + "Z"

            tasks_to_remove = []

            for task_id, task in self._tasks.items():
                if task.status.state in [TaskState.COMPLETED, TaskState.FAILED]:
                    if task.status.timestamp < cutoff_timestamp:
                        tasks_to_remove.append(task_id)

            # Remove tasks
            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                self._task_timeouts.pop(task_id, None)

            cleaned_count = len(tasks_to_remove)
            if cleaned_count > 0:
                logger.info(
                    f"Cleaned up {cleaned_count} completed tasks older than {older_than_hours}h"
                )
                self.stats["cleanup_runs"] += 1

            return cleaned_count

    async def check_timeouts(self) -> int:
        """Check for timed out tasks and mark them as failed.

        Returns:
            Number of tasks that timed out

        """
        async with self._lock:
            current_time = time.time()
            timed_out_tasks = []

            for task_id, timeout_time in self._task_timeouts.items():
                if current_time > timeout_time:
                    task = self._tasks.get(task_id)
                    if task and task.status.state in [
                        TaskState.SUBMITTED,
                        TaskState.WORKING,
                    ]:
                        timed_out_tasks.append(task_id)

            # Mark timed out tasks as failed
            for task_id in timed_out_tasks:
                timeout_message = create_message(
                    MessageRole.AGENT,
                    [create_text_part("Task execution timed out")],
                    task_id=task_id,
                )

                await self.update_task_status(
                    task_id, TaskState.FAILED, timeout_message, "Task execution timeout"
                )

                # Remove from timeout tracking
                self._task_timeouts.pop(task_id, None)
                self.stats["tasks_timeout"] += 1

                logger.warning(
                    f"[TaskID: {task_id}] Task timed out and marked as failed"
                )

            return len(timed_out_tasks)

    def get_stats(self) -> dict[str, Any]:
        """Get task manager statistics."""
        return {
            **self.stats,
            "active_tasks": len(self._tasks),
            "tracked_timeouts": len(self._task_timeouts),
            "running": self._running,
        }

    def _is_valid_transition(self, from_state: TaskState, to_state: TaskState) -> bool:
        """Validate task state transitions."""
        # Valid transitions according to A2A specification
        valid_transitions = {
            TaskState.SUBMITTED: [
                TaskState.WORKING,
                TaskState.INPUT_REQUIRED,
                TaskState.AUTH_REQUIRED,
                TaskState.REJECTED,
                TaskState.CANCELED,
                TaskState.FAILED,
            ],
            TaskState.WORKING: [
                TaskState.COMPLETED,
                TaskState.FAILED,
                TaskState.INPUT_REQUIRED,
                TaskState.AUTH_REQUIRED,
                TaskState.CANCELED,
            ],
            TaskState.INPUT_REQUIRED: [
                TaskState.WORKING,
                TaskState.FAILED,
                TaskState.CANCELED,
            ],
            TaskState.AUTH_REQUIRED: [
                TaskState.WORKING,
                TaskState.FAILED,
                TaskState.CANCELED,
            ],
            TaskState.UNKNOWN: [
                TaskState.WORKING,
                TaskState.FAILED,
                TaskState.CANCELED,
            ],
            TaskState.COMPLETED: [],  # Terminal state
            TaskState.FAILED: [],  # Terminal state
            TaskState.CANCELED: [],  # Terminal state
            TaskState.REJECTED: [],  # Terminal state
        }

        return to_state in valid_transitions.get(from_state, [])

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        try:
            while self._running:
                # Check for timeouts
                timeout_count = await self.check_timeouts()
                if timeout_count > 0:
                    logger.info(f"Processed {timeout_count} timed out tasks")

                # Cleanup old completed tasks
                cleaned_count = await self.cleanup_completed_tasks()

                # Sleep until next cleanup
                await trio.sleep(self.cleanup_interval)

        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
        finally:
            logger.info("Task manager cleanup loop stopped")


# Utility functions for creating common task patterns


async def create_user_task(
    user_message_text: str,
    task_manager: TaskManager,
    context_id: str | None = None,
    timeout: int | None = None,
) -> Task:
    """Create a task from a user message string."""
    parts = [create_text_part(user_message_text)]
    message = create_message(MessageRole.USER, parts)

    return await task_manager.create_task(
        message, context_id=context_id, timeout=timeout
    )


async def complete_task_with_text_response(
    task_manager: TaskManager,
    task_id: str,
    response_text: str,
    artifact_name: str | None = None,
) -> bool:
    """Complete a task with a text response and optional artifact."""
    # Create agent response message
    response_parts = [create_text_part(response_text)]
    agent_message = create_message(MessageRole.AGENT, response_parts)

    # Add artifact if name provided
    if artifact_name:
        await task_manager.add_artifact(
            task_id,
            artifact_name,
            [create_text_part(response_text)],
            description="Task completion response",
        )

    # Mark task as completed
    return await task_manager.update_task_status(
        task_id, TaskState.COMPLETED, agent_message
    )


async def fail_task_with_error(
    task_manager: TaskManager,
    task_id: str,
    error_message: str,
    error_details: str | None = None,
) -> bool:
    """Fail a task with an error message."""
    error_parts = [create_text_part(f"Error: {error_message}")]
    agent_message = create_message(MessageRole.AGENT, error_parts)

    return await task_manager.update_task_status(
        task_id, TaskState.FAILED, agent_message, error_details or error_message
    )

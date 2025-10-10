"""Trio-based event bus system for inter-component communication."""

import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

import trio
from loguru import logger


class EventType(Enum):
    """Event types for the Praxis agent system."""

    # Agent lifecycle events
    AGENT_STARTING = "agent.starting"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPING = "agent.stopping"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"

    # P2P events
    P2P_PEER_DISCOVERED = "p2p.peer_discovered"
    P2P_PEER_CONNECTED = "p2p.peer_connected"
    P2P_PEER_DISCONNECTED = "p2p.peer_disconnected"
    P2P_CARD_EXCHANGE = "p2p.card_exchange"
    P2P_TOOL_REQUEST = "p2p.tool_request"
    P2P_TOOL_RESPONSE = "p2p.tool_response"

    # Task execution events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # DSL/Workflow events
    DSL_COMMAND_RECEIVED = "dsl.command_received"
    DSL_COMMAND_PROGRESS = "dsl.command_progress"
    DSL_COMMAND_COMPLETED = "dsl.command_completed"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_PROGRESS = "workflow.progress"
    WORKFLOW_COMPLETED = "workflow.completed"
    NODE_STATUS_UPDATE = "workflow.node_status_update"

    # Tool execution events
    TOOL_EXECUTED = "tool.executed"
    TOOL_STARTING = "tool.starting"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # WebSocket events
    WS_CLIENT_CONNECTED = "ws.client_connected"
    WS_CLIENT_DISCONNECTED = "ws.client_disconnected"
    WS_MESSAGE_RECEIVED = "ws.message_received"
    WS_MESSAGE_SENT = "ws.message_sent"

    # Log events
    LOG_ENTRY = "log.entry"
    LOG_STREAM = "log.stream"

    # System events
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"


@dataclass
class EventMetadata:
    """Metadata for events."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str | None = None
    source: str | None = None
    tags: set[str] = field(default_factory=set)


@dataclass
class Event:
    """Base event class."""

    type: EventType
    data: dict[str, Any]
    metadata: EventMetadata = field(default_factory=EventMetadata)


class EventFilter:
    """Filter events based on type, source, and tags."""

    def __init__(
        self,
        event_types: set[EventType] | None = None,
        source_patterns: set[str] | None = None,
        required_tags: set[str] | None = None,
        excluded_tags: set[str] | None = None,
    ):
        self.event_types = event_types or set()
        self.source_patterns = source_patterns or set()
        self.required_tags = required_tags or set()
        self.excluded_tags = excluded_tags or set()

    def matches(self, event: Event) -> bool:
        """Check if event matches filter criteria."""
        # Check event type
        if self.event_types and event.type not in self.event_types:
            return False

        # Check source patterns
        if self.source_patterns and event.metadata.source:
            if not any(
                pattern in event.metadata.source for pattern in self.source_patterns
            ):
                return False

        # Check required tags
        if self.required_tags and not self.required_tags.issubset(event.metadata.tags):
            return False

        # Check excluded tags
        if self.excluded_tags and self.excluded_tags.intersection(event.metadata.tags):
            return False

        return True


class WebSocketManager:
    """Manages WebSocket connections for event streaming."""

    def __init__(self):
        self.connections: dict[str, trio.MemorySendChannel] = {}
        self.filters: dict[str, EventFilter] = {}

    def add_connection(
        self,
        connection_id: str,
        send_channel: trio.MemorySendChannel,
        event_filter: EventFilter | None = None,
    ) -> None:
        """Add a WebSocket connection."""
        self.connections[connection_id] = send_channel
        if event_filter:
            self.filters[connection_id] = event_filter

    def remove_connection(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        self.connections.pop(connection_id, None)
        self.filters.pop(connection_id, None)

    async def broadcast_event(self, event: Event) -> None:
        """Broadcast event to all matching WebSocket connections."""
        for connection_id, send_channel in self.connections.items():
            event_filter = self.filters.get(connection_id)

            if event_filter and not event_filter.matches(event):
                continue

            try:
                await send_channel.send(event)
            except trio.BrokenResourceError:
                # Connection closed, remove it
                self.remove_connection(connection_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")


HandlerType = Union[Callable[[Event], None], Callable[[Event], Awaitable[None]]]


class EventBus:
    """Trio-based event bus for inter-component communication."""

    def __init__(self, buffer_size: int = 1000, max_concurrent_handlers: int = 100):
        self.buffer_size = buffer_size
        self.max_concurrent_handlers = max_concurrent_handlers

        # Event handling
        self._handlers: dict[EventType, list[weakref.ReferenceType]] = {}
        self._global_handlers: list[weakref.ReferenceType] = []

        # Managers
        self.websocket_manager = WebSocketManager()

        # Trio channels for event processing
        self._send_channel: trio.MemorySendChannel | None = None
        self._receive_channel: trio.MemoryReceiveChannel | None = None

        # Control
        self._running = False
        self._nursery: trio.Nursery | None = None
        self._semaphore: trio.Semaphore | None = None

        # Statistics
        self.stats = {
            "events_published": 0,
            "events_processed": 0,
            "handler_errors": 0,
            "active_handlers": 0,
        }

    async def start(self, nursery: trio.Nursery | None = None) -> None:
        """Start the event bus."""
        if self._running:
            return

        if nursery is None:
            # Asyncio mode - create minimal event handling without trio dependencies
            self._running = True
            logger.info("Event bus started in asyncio mode")
            return

        # Trio mode (original implementation)
        self._nursery = nursery
        self._semaphore = trio.Semaphore(self.max_concurrent_handlers)
        self._send_channel, self._receive_channel = trio.open_memory_channel(
            self.buffer_size
        )

        # Start event processing task
        nursery.start_task(self._process_events)

        self._running = True
        logger.info("Event bus started in trio mode")

    async def stop(self) -> None:
        """Stop the event bus."""
        if not self._running:
            return

        self._running = False

        if self._send_channel:
            self._send_channel.close()

        logger.info("Event bus stopped")

    def subscribe(
        self, event_type: EventType, handler: HandlerType, weak_ref: bool = True
    ) -> None:
        """Subscribe to specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        if weak_ref:
            ref = (
                weakref.ref(handler)
                if hasattr(handler, "__self__")
                else lambda: handler
            )
            self._handlers[event_type].append(ref)
        else:
            self._handlers[event_type].append(lambda: handler)

        self.stats["active_handlers"] += 1

    def subscribe_all(self, handler: HandlerType, weak_ref: bool = True) -> None:
        """Subscribe to all events."""
        if weak_ref:
            ref = (
                weakref.ref(handler)
                if hasattr(handler, "__self__")
                else lambda: handler
            )
            self._global_handlers.append(ref)
        else:
            self._global_handlers.append(lambda: handler)

        self.stats["active_handlers"] += 1

    async def publish(self, event: Event) -> None:
        """Publish an event."""
        if not self._running:
            logger.warning("Event bus not running, dropping event")
            return

        self.stats["events_published"] += 1

        # In asyncio mode, just log events for now
        if not self._send_channel:
            logger.debug(
                f"Event published: {event.type.value} from {event.metadata.source}"
            )
            return

        # Trio mode - use channels
        try:
            await self._send_channel.send(event)
        except trio.WouldBlock:
            logger.warning(f"Event bus buffer full, dropping event: {event.type}")
        except Exception as e:
            logger.error(f"Error publishing event: {e}")

    async def publish_data(
        self,
        event_type: EventType,
        data: dict[str, Any],
        source: str | None = None,
        correlation_id: str | None = None,
        tags: set[str] | None = None,
    ) -> None:
        """Publish event with data."""
        metadata = EventMetadata(
            source=source, correlation_id=correlation_id, tags=tags or set()
        )
        event = Event(type=event_type, data=data, metadata=metadata)
        await self.publish(event)

    async def _process_events(self) -> None:
        """Process events from the channel."""
        try:
            async with self._receive_channel:
                async for event in self._receive_channel:
                    if not self._nursery:
                        continue

                    # Process event in separate task to avoid blocking
                    self._nursery.start_task(self._handle_event, event)
        except Exception as e:
            logger.error(f"Error in event processing loop: {e}")

    async def _handle_event(self, event: Event) -> None:
        """Handle a single event."""
        async with self._semaphore:
            self.stats["events_processed"] += 1

            # Collect all handlers
            handlers = []

            # Type-specific handlers
            if event.type in self._handlers:
                handlers.extend(self._handlers[event.type])

            # Global handlers
            handlers.extend(self._global_handlers)

            # Clean up dead references and execute handlers
            for handler_ref in handlers:
                handler = handler_ref()
                if handler is None:
                    continue  # Dead reference, skip

                try:
                    if callable(handler):
                        result = handler(event)
                        if hasattr(result, "__await__"):
                            await result
                except Exception as e:
                    self.stats["handler_errors"] += 1
                    logger.error(f"Error in event handler: {e}")

            # Broadcast to WebSocket connections
            await self.websocket_manager.broadcast_event(event)

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self.stats,
            "websocket_connections": len(self.websocket_manager.connections),
            "running": self._running,
        }


# Global event bus instance
event_bus = EventBus()

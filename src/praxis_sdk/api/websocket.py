"""
WebSocket Manager for Praxis Python SDK.

Provides comprehensive WebSocket connection management, event streaming,
and real-time communication capabilities with trio_asyncio integration.
"""

import json
import trio
import trio_asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Union, Callable, Awaitable
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel, Field

from praxis_sdk.bus import Event, EventType, EventFilter, event_bus
from praxis_sdk.a2a.models import Task, Message


class ConnectionState(Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MessageType(Enum):
    """WebSocket message types."""
    # Client to server
    DSL_COMMAND = "DSL_COMMAND"
    EXECUTE_WORKFLOW = "EXECUTE_WORKFLOW"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    SUBSCRIBE_EVENTS = "SUBSCRIBE_EVENTS"
    UNSUBSCRIBE_EVENTS = "UNSUBSCRIBE_EVENTS"
    PING = "PING"
    
    # Server to client
    DSL_PROGRESS = "dslProgress"
    DSL_RESULT = "dslResult"
    WORKFLOW_START = "workflowStart"
    WORKFLOW_PROGRESS = "workflowProgress"
    WORKFLOW_COMPLETE = "workflowComplete"
    WORKFLOW_ERROR = "workflowError"
    NODE_STATUS_UPDATE = "nodeStatusUpdate"
    CHAT_RESPONSE = "chatMessage"
    TOOL_RESULT = "tool_result"
    EVENT_STREAM = "eventStream"
    PONG = "PONG"
    ERROR = "error"


@dataclass
class WebSocketConnection:
    """WebSocket connection information."""
    
    id: str
    websocket: WebSocket
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: Optional[datetime] = None
    event_filter: Optional[EventFilter] = None
    subscribed_events: Set[EventType] = field(default_factory=set)
    send_channel: Optional[trio.MemorySendChannel] = None
    receive_channel: Optional[trio.MemoryReceiveChannel] = None
    user_id: Optional[str] = None
    session_data: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    error_count: int = 0


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""
    
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


class WebSocketManager:
    """
    Comprehensive WebSocket connection manager with event streaming.
    
    Features:
    - Connection lifecycle management
    - Event filtering and subscription
    - Real-time event broadcasting
    - Message routing and handling
    - Connection health monitoring
    - Trio-asyncio integration
    """
    
    def __init__(self, max_connections: int = 100, heartbeat_interval: int = 30):
        self.max_connections = max_connections
        self.heartbeat_interval = heartbeat_interval
        
        # Connection management
        self.connections: Dict[str, WebSocketConnection] = {}
        self.connection_handlers: Dict[MessageType, Callable] = {}
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "broadcast_count": 0,
            "errors": 0,
        }
        
        # Control
        self._running = False
        self._nursery: Optional[trio.Nursery] = None
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup message handlers for different message types."""
        
        self.connection_handlers = {
            MessageType.DSL_COMMAND: self._handle_dsl_command,
            MessageType.EXECUTE_WORKFLOW: self._handle_execute_workflow,
            MessageType.CHAT_MESSAGE: self._handle_chat_message,
            MessageType.SUBSCRIBE_EVENTS: self._handle_subscribe_events,
            MessageType.UNSUBSCRIBE_EVENTS: self._handle_unsubscribe_events,
            MessageType.PING: self._handle_ping,
        }
    
    async def start(self, nursery: trio.Nursery):
        """Start the WebSocket manager."""
        self._nursery = nursery
        self._running = True
        
        # Start background tasks
        nursery.start_soon(self._heartbeat_monitor)
        nursery.start_soon(self._connection_cleanup)
        
        logger.info("WebSocket manager started")
    
    async def stop(self):
        """Stop the WebSocket manager."""
        self._running = False
        
        # Close all connections
        for connection in list(self.connections.values()):
            await self._disconnect_client(connection.id, reason="Server shutdown")
        
        logger.info("WebSocket manager stopped")
    
    async def handle_connection(self, websocket: WebSocket) -> str:
        """
        Handle new WebSocket connection.
        Returns connection ID.
        """
        if len(self.connections) >= self.max_connections:
            await websocket.close(code=1008, reason="Maximum connections reached")
            raise ConnectionError("Maximum connections reached")
        
        connection_id = str(uuid4())
        
        try:
            await websocket.accept()
            
            # Create connection object
            connection = WebSocketConnection(
                id=connection_id,
                websocket=websocket,
                state=ConnectionState.CONNECTED
            )
            
            # Setup event streaming channels
            send_channel, receive_channel = trio.open_memory_channel(100)
            connection.send_channel = send_channel
            connection.receive_channel = receive_channel
            
            # Register connection
            self.connections[connection_id] = connection
            self.stats["total_connections"] += 1
            self.stats["active_connections"] += 1
            
            # Add to event bus WebSocket manager
            default_filter = EventFilter(
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
                    EventType.P2P_TOOL_RESPONSE
                }
            )
            event_bus.websocket_manager.add_connection(connection_id, send_channel, default_filter)
            
            logger.info(f"WebSocket client connected: {connection_id}")
            
            # Send welcome message
            await self.send_message(connection_id, WebSocketMessage(
                type=MessageType.CHAT_RESPONSE.value,
                payload={
                    "content": "Connected to Praxis Agent",
                    "sender": "system",
                    "type": "system"
                }
            ))
            
            return connection_id
            
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {e}")
            if connection_id in self.connections:
                await self._disconnect_client(connection_id, reason=f"Connection error: {e}")
            raise
    
    async def handle_client_messages(self, connection_id: str):
        """Handle messages from a WebSocket client."""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        try:
            while connection.state == ConnectionState.CONNECTED:
                # Receive message from client
                data = await connection.websocket.receive_text()
                connection.message_count += 1
                self.stats["messages_received"] += 1
                
                try:
                    message_data = json.loads(data)
                    message = WebSocketMessage(**message_data)
                    
                    # Handle message
                    await self._route_message(connection_id, message)
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Invalid message from {connection_id}: {e}")
                    await self._send_error(connection_id, f"Invalid message format: {e}")
                    connection.error_count += 1
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {connection_id}")
            await self._disconnect_client(connection_id, reason="Client disconnected")
        except Exception as e:
            logger.error(f"Error handling messages from {connection_id}: {e}")
            await self._disconnect_client(connection_id, reason=f"Message handling error: {e}")
    
    async def handle_event_streaming(self, connection_id: str):
        """Handle event streaming to a WebSocket client."""
        connection = self.connections.get(connection_id)
        if not connection or not connection.receive_channel:
            return
        
        try:
            async with connection.receive_channel:
                async for event in connection.receive_channel:
                    if connection.state != ConnectionState.CONNECTED:
                        break
                    
                    # Transform event to frontend-compatible format
                    frontend_message = self._transform_event_for_frontend(event)
                    if frontend_message:
                        await self._send_message_direct(connection, frontend_message)
                    
        except Exception as e:
            logger.error(f"Error streaming events to {connection_id}: {e}")
    
    def _transform_event_for_frontend(self, event: Event) -> Optional[WebSocketMessage]:
        """Transform backend events to frontend-compatible WebSocket messages."""
        try:
            # Map backend event types to frontend message types (exact match with websocket-client.ts)
            frontend_type_map = {
                EventType.DSL_COMMAND_PROGRESS: "dslProgress",
                EventType.DSL_COMMAND_RESULT: "dslResult",
                EventType.TASK_STARTED: "workflowStart", 
                EventType.TASK_PROGRESS: "workflowProgress",
                EventType.TASK_COMPLETED: "workflowComplete",
                EventType.TASK_FAILED: "workflowError",
                EventType.NODE_STATUS_UPDATE: "nodeStatusUpdate",
                EventType.WORKFLOW_STARTED: "workflowStart",
                EventType.WORKFLOW_PROGRESS: "workflowProgress",
                EventType.WORKFLOW_COMPLETED: "workflowComplete",
                EventType.WORKFLOW_FAILED: "workflowError",
                EventType.CHAT_MESSAGE_RECEIVED: "chatMessage",
                EventType.TOOL_EXECUTION_STARTED: "toolInvocation",
                EventType.TOOL_EXECUTION_COMPLETED: "tool_result",
                EventType.P2P_TOOL_RESPONSE: "tool_result"
            }
            
            frontend_type = frontend_type_map.get(event.type)
            if not frontend_type:
                # For unknown events, use generic event stream
                frontend_type = "eventStream"
            
            # Handle special transformations for specific event types
            if event.type in [EventType.DSL_COMMAND_PROGRESS]:
                return self._create_dsl_progress_message(event, frontend_type)
            elif event.type in [EventType.DSL_COMMAND_RESULT]:
                return self._create_dsl_result_message(event, frontend_type)
            elif event.type in [EventType.TASK_STARTED, EventType.WORKFLOW_STARTED]:
                return self._create_workflow_start_message(event, frontend_type)
            elif event.type in [EventType.TASK_PROGRESS, EventType.WORKFLOW_PROGRESS]:
                return self._create_workflow_progress_message(event, frontend_type)
            elif event.type in [EventType.TASK_COMPLETED, EventType.WORKFLOW_COMPLETED]:
                return self._create_workflow_complete_message(event, frontend_type)
            elif event.type in [EventType.TASK_FAILED, EventType.WORKFLOW_FAILED]:
                return self._create_workflow_error_message(event, frontend_type)
            elif event.type in [EventType.NODE_STATUS_UPDATE]:
                return self._create_node_status_update_message(event, frontend_type)
            elif event.type in [EventType.CHAT_MESSAGE_RECEIVED]:
                return self._create_chat_message(event, frontend_type)
            elif event.type in [EventType.TOOL_EXECUTION_COMPLETED, EventType.P2P_TOOL_RESPONSE]:
                return self._create_tool_result_message(event, frontend_type)
            else:
                # Generic event transformation
                return WebSocketMessage(
                    type=frontend_type,
                    payload=event.data or {},
                    timestamp=event.metadata.timestamp,
                    correlation_id=event.metadata.correlation_id
                )
                
        except Exception as e:
            logger.error(f"Error transforming event for frontend: {e}")
            return None
    
    def _create_dsl_progress_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create DSL progress message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "stage": data.get("stage", "analyzing"),
                "message": data.get("message", "Processing DSL command..."),
                "details": data
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    def _create_dsl_result_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create DSL result message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "success": data.get("success", True),
                "command": data.get("command", ""),
                "matchedAgents": data.get("matched_agents", []),
                "requiredMCPTools": data.get("required_tools", []),
                "workflowSuggestion": data.get("workflow", {}),
                "processTime": data.get("process_time", 0)
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    def _create_workflow_start_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create workflow start message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "workflowId": data.get("workflow_id", ""),
                "executionId": data.get("execution_id", ""),
                "nodes": data.get("nodes", []),
                "edges": data.get("edges", []),
                "metadata": data.get("metadata", {}),
                "startTime": event.metadata.timestamp.isoformat() + "Z"
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    def _create_workflow_progress_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create workflow progress message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "workflowId": data.get("workflow_id", ""),
                "executionId": data.get("execution_id", ""),
                "nodeId": data.get("node_id", ""),
                "status": data.get("status", "running"),
                "progress": data.get("progress", 0),
                "message": data.get("message", "Processing..."),
                "timestamp": event.metadata.timestamp.isoformat() + "Z"
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    def _create_workflow_complete_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create workflow completion message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "workflowId": data.get("workflow_id", ""),
                "executionId": data.get("execution_id", ""),
                "message": data.get("message", "Workflow completed successfully"),
                "results": data.get("results", ""),
                "duration": data.get("duration", 0),
                "timestamp": event.metadata.timestamp.isoformat() + "Z"
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    def _create_workflow_error_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create workflow error message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "workflowId": data.get("workflow_id", ""),
                "executionId": data.get("execution_id", ""),
                "nodeId": data.get("node_id"),
                "error": data.get("error", "Workflow execution failed"),
                "timestamp": event.metadata.timestamp.isoformat() + "Z"
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    def _create_node_status_update_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create node status update message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "workflowId": data.get("workflow_id", ""),
                "nodeId": data.get("node_id", ""),
                "status": data.get("status", "idle"),
                "timestamp": event.metadata.timestamp.isoformat() + "Z"
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    def _create_chat_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create chat message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "content": data.get("content", ""),
                "sender": data.get("sender", "assistant"),
                "type": data.get("message_type", "text"),
                "metadata": data.get("metadata")
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    def _create_tool_result_message(self, event: Event, message_type: str) -> WebSocketMessage:
        """Create tool result message for frontend."""
        data = event.data or {}
        return WebSocketMessage(
            type=message_type,
            payload={
                "toolName": data.get("tool_name", ""),
                "status": data.get("status", "completed"),
                "result": data.get("result"),
                "error": data.get("error"),
                "metadata": data.get("metadata")
            },
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id
        )
    
    async def send_message(self, connection_id: str, message: WebSocketMessage):
        """Send message to specific connection."""
        connection = self.connections.get(connection_id)
        if not connection:
            logger.warning(f"Connection not found: {connection_id}")
            return False
        
        return await self._send_message_direct(connection, message)
    
    async def broadcast_message(self, message: WebSocketMessage, filter_func: Optional[Callable[[WebSocketConnection], bool]] = None):
        """Broadcast message to all or filtered connections."""
        self.stats["broadcast_count"] += 1
        
        tasks = []
        for connection in self.connections.values():
            if filter_func and not filter_func(connection):
                continue
                
            if connection.state == ConnectionState.CONNECTED:
                tasks.append(self._send_message_direct(connection, message))
        
        if tasks:
            await trio_asyncio.aio_as_trio(lambda: trio.lowlevel.current_trio_token().run_sync_in_context_of(
                lambda: [t for t in tasks]
            ))()
    
    async def _send_message_direct(self, connection: WebSocketConnection, message: WebSocketMessage) -> bool:
        """Send message directly to connection in frontend-compatible format."""
        try:
            # Transform to frontend format: {type: string, payload: any, timestamp?: string, id?: string}
            frontend_message = {
                "type": message.type,
                "payload": message.payload,
                "timestamp": message.timestamp.isoformat() + "Z" if hasattr(message.timestamp, 'isoformat') else message.timestamp,
                "id": message.id
            }
            
            # Add correlation_id if present
            if message.correlation_id:
                frontend_message["correlation_id"] = message.correlation_id
            
            await connection.websocket.send_text(json.dumps(frontend_message))
            self.stats["messages_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Error sending message to {connection.id}: {e}")
            connection.error_count += 1
            self.stats["errors"] += 1
            
            # Disconnect on send errors
            await self._disconnect_client(connection.id, reason=f"Send error: {e}")
            return False
    
    async def _route_message(self, connection_id: str, message: WebSocketMessage):
        """Route message to appropriate handler."""
        try:
            message_type = MessageType(message.type)
            handler = self.connection_handlers.get(message_type)
            
            if handler:
                await handler(connection_id, message)
            else:
                logger.warning(f"No handler for message type: {message.type}")
                await self._send_error(connection_id, f"Unknown message type: {message.type}")
                
        except ValueError:
            logger.error(f"Invalid message type: {message.type}")
            await self._send_error(connection_id, f"Invalid message type: {message.type}")
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            await self._send_error(connection_id, f"Message routing error: {e}")
    
    async def _handle_dsl_command(self, connection_id: str, message: WebSocketMessage):
        """Handle DSL command message."""
        command = message.payload.get("command", "")
        
        await event_bus.publish_data(
            EventType.DSL_COMMAND_RECEIVED,
            {
                "command": command,
                "connection_id": connection_id,
                "websocket_source": True
            },
            source="websocket_manager",
            correlation_id=message.id
        )
    
    async def _handle_execute_workflow(self, connection_id: str, message: WebSocketMessage):
        """Handle workflow execution message."""
        workflow_id = message.payload.get("workflowId", str(uuid4()))
        nodes = message.payload.get("nodes", [])
        edges = message.payload.get("edges", [])
        
        await event_bus.publish_data(
            EventType.WORKFLOW_STARTED,
            {
                "workflow_id": workflow_id,
                "nodes": nodes,
                "edges": edges,
                "connection_id": connection_id
            },
            source="websocket_manager",
            correlation_id=workflow_id
        )
    
    async def _handle_chat_message(self, connection_id: str, message: WebSocketMessage):
        """Handle chat message."""
        content = message.payload.get("content", "")
        sender = message.payload.get("sender", "user")
        
        # Treat user chat messages as DSL commands
        if sender == "user":
            await self._handle_dsl_command(connection_id, WebSocketMessage(
                type=MessageType.DSL_COMMAND.value,
                payload={"command": content},
                correlation_id=message.id
            ))
    
    async def _handle_subscribe_events(self, connection_id: str, message: WebSocketMessage):
        """Handle event subscription request."""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        event_types = message.payload.get("event_types", [])
        
        try:
            # Parse event types
            subscription_events = {EventType(et) for et in event_types}
            connection.subscribed_events.update(subscription_events)
            
            # Update event filter
            connection.event_filter = EventFilter(event_types=connection.subscribed_events)
            
            # Update event bus subscription
            if connection.send_channel:
                event_bus.websocket_manager.add_connection(
                    connection_id, 
                    connection.send_channel, 
                    connection.event_filter
                )
            
            await self.send_message(connection_id, WebSocketMessage(
                type=MessageType.CHAT_RESPONSE.value,
                payload={
                    "content": f"Subscribed to {len(subscription_events)} event types",
                    "sender": "system",
                    "type": "system"
                }
            ))
            
        except ValueError as e:
            await self._send_error(connection_id, f"Invalid event types: {e}")
    
    async def _handle_unsubscribe_events(self, connection_id: str, message: WebSocketMessage):
        """Handle event unsubscription request."""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        event_types = message.payload.get("event_types", [])
        
        try:
            # Parse and remove event types
            unsubscribe_events = {EventType(et) for et in event_types}
            connection.subscribed_events -= unsubscribe_events
            
            # Update event filter
            connection.event_filter = EventFilter(event_types=connection.subscribed_events)
            
            # Update event bus subscription
            if connection.send_channel:
                event_bus.websocket_manager.add_connection(
                    connection_id, 
                    connection.send_channel, 
                    connection.event_filter
                )
            
            await self.send_message(connection_id, WebSocketMessage(
                type=MessageType.CHAT_RESPONSE.value,
                payload={
                    "content": f"Unsubscribed from {len(unsubscribe_events)} event types",
                    "sender": "system",
                    "type": "system"
                }
            ))
            
        except ValueError as e:
            await self._send_error(connection_id, f"Invalid event types: {e}")
    
    async def _handle_ping(self, connection_id: str, message: WebSocketMessage):
        """Handle ping message."""
        connection = self.connections.get(connection_id)
        if connection:
            connection.last_ping = datetime.utcnow()
        
        await self.send_message(connection_id, WebSocketMessage(
            type=MessageType.PONG.value,
            payload={"timestamp": datetime.utcnow().isoformat() + "Z"},
            correlation_id=message.id
        ))
    
    async def _send_error(self, connection_id: str, error_message: str):
        """Send error message to connection."""
        await self.send_message(connection_id, WebSocketMessage(
            type=MessageType.ERROR.value,
            payload={
                "message": error_message,
                "code": "WEBSOCKET_ERROR",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ))
    
    async def _disconnect_client(self, connection_id: str, reason: str = "Unknown"):
        """Disconnect and cleanup client connection."""
        connection = self.connections.pop(connection_id, None)
        if not connection:
            return
        
        try:
            connection.state = ConnectionState.DISCONNECTING
            
            # Close WebSocket
            if connection.websocket:
                await connection.websocket.close(reason=reason)
            
            # Close channels
            if connection.send_channel:
                connection.send_channel.close()
            
            # Remove from event bus
            event_bus.websocket_manager.remove_connection(connection_id)
            
            connection.state = ConnectionState.DISCONNECTED
            self.stats["active_connections"] = max(0, self.stats["active_connections"] - 1)
            
            logger.info(f"WebSocket client disconnected: {connection_id} (reason: {reason})")
            
        except Exception as e:
            logger.error(f"Error disconnecting client {connection_id}: {e}")
            connection.state = ConnectionState.ERROR
    
    async def _heartbeat_monitor(self):
        """Monitor connection health with periodic heartbeats."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                
                # Check for stale connections
                stale_connections = []
                for connection in self.connections.values():
                    if connection.last_ping:
                        time_since_ping = (current_time - connection.last_ping).total_seconds()
                        if time_since_ping > self.heartbeat_interval * 3:  # 3x heartbeat interval
                            stale_connections.append(connection.id)
                
                # Disconnect stale connections
                for connection_id in stale_connections:
                    await self._disconnect_client(connection_id, reason="Heartbeat timeout")
                
                # Wait for next check
                await trio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await trio.sleep(5)  # Brief pause on error
    
    async def _connection_cleanup(self):
        """Periodic cleanup of dead connections."""
        while self._running:
            try:
                dead_connections = []
                
                for connection in self.connections.values():
                    if connection.state in [ConnectionState.DISCONNECTED, ConnectionState.ERROR]:
                        dead_connections.append(connection.id)
                    elif connection.error_count > 10:  # Too many errors
                        dead_connections.append(connection.id)
                
                # Remove dead connections
                for connection_id in dead_connections:
                    await self._disconnect_client(connection_id, reason="Connection cleanup")
                
                # Wait for next cleanup
                await trio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")
                await trio.sleep(10)
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a connection."""
        connection = self.connections.get(connection_id)
        if not connection:
            return None
        
        return {
            "id": connection.id,
            "state": connection.state.value,
            "connected_at": connection.connected_at.isoformat(),
            "last_ping": connection.last_ping.isoformat() if connection.last_ping else None,
            "message_count": connection.message_count,
            "error_count": connection.error_count,
            "subscribed_events": [et.value for et in connection.subscribed_events],
            "user_id": connection.user_id,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            **self.stats,
            "connection_states": {
                state.value: sum(1 for conn in self.connections.values() if conn.state == state)
                for state in ConnectionState
            },
            "total_errors": sum(conn.error_count for conn in self.connections.values()),
            "average_messages_per_connection": (
                sum(conn.message_count for conn in self.connections.values()) / len(self.connections)
                if self.connections else 0
            ),
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
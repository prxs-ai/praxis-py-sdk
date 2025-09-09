"""
Example usage of the trio-based event bus system.

This demonstrates how to integrate the event bus with various components
of the Praxis SDK including P2P services, WebSocket handlers, and task management.
"""

import trio
import json
from typing import Any
from praxis_sdk.bus import (
    EventBus, EventType, Event, EventFilter, EventMetadata,
    get_event_bus, publish, subscribe, EventBusManager
)


class AgentComponent:
    """Example agent component using the event bus."""
    
    def __init__(self, name: str):
        self.name = name
        self.event_bus = get_event_bus()
        self.subscriptions = []
        
    async def start(self):
        """Start the component and subscribe to relevant events."""
        print(f"Starting {self.name}")
        
        # Subscribe to system events
        sub_id = self.event_bus.subscribe(
            EventType.SYSTEM_SHUTDOWN,
            self.handle_shutdown
        )
        self.subscriptions.append(sub_id)
        
        # Subscribe to task events with filter
        task_filter = EventFilter(
            event_types={EventType.TASK_CREATED, EventType.TASK_COMPLETED},
            tags={"component": self.name}
        )
        sub_id = self.event_bus.subscribe(
            [EventType.TASK_CREATED, EventType.TASK_COMPLETED],
            self.handle_task_event,
            event_filter=task_filter
        )
        self.subscriptions.append(sub_id)
        
        # Publish component started event
        metadata = EventMetadata(source=self.name, tags={"component": "agent"})
        await self.event_bus.publish(
            EventType.AGENT_STARTED,
            {"component": self.name},
            metadata=metadata
        )
    
    async def handle_shutdown(self, event_type: str, payload: Any):
        """Handle system shutdown event."""
        print(f"{self.name}: Received shutdown signal")
        await self.stop()
    
    async def handle_task_event(self, event_type: str, payload: Any):
        """Handle task-related events."""
        print(f"{self.name}: Task event {event_type} - {payload}")
    
    async def stop(self):
        """Stop the component and cleanup subscriptions."""
        print(f"Stopping {self.name}")
        
        # Unsubscribe from all events
        for sub_id in self.subscriptions:
            self.event_bus.unsubscribe(sub_id)
        
        # Publish component stopped event
        metadata = EventMetadata(source=self.name)
        await self.event_bus.publish(
            EventType.AGENT_STOPPED,
            {"component": self.name},
            metadata=metadata
        )


class P2PServiceMock:
    """Mock P2P service demonstrating event bus integration."""
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self.peers = {}
        
    async def start(self):
        """Start P2P service."""
        # Subscribe to P2P events
        self.event_bus.subscribe(
            EventType.P2P_TOOL_REQUEST,
            self.handle_tool_request
        )
        
        # Simulate peer discovery
        await trio.sleep(1)
        await self.simulate_peer_discovery()
        
    async def simulate_peer_discovery(self):
        """Simulate discovering a peer."""
        peer_id = "QmExample123"
        peer_info = {
            "peer_id": peer_id,
            "address": "/ip4/192.168.1.100/tcp/4001",
            "agent_name": "praxis-agent-2"
        }
        
        self.peers[peer_id] = peer_info
        
        # Publish peer discovered event
        metadata = EventMetadata(source="p2p_service", tags={"peer": peer_id})
        await self.event_bus.publish(
            EventType.P2P_PEER_DISCOVERED,
            peer_info,
            metadata=metadata
        )
        
        # Simulate connection
        await trio.sleep(0.5)
        await self.event_bus.publish(
            EventType.P2P_PEER_CONNECTED,
            {"peer_id": peer_id, "connection_time": "2024-01-01T10:00:00Z"},
            metadata=metadata
        )
        
        # Simulate card exchange
        card_data = {
            "peer_id": peer_id,
            "agent_card": {
                "name": "praxis-agent-2",
                "version": "1.0.0",
                "tools": ["write_file", "read_file"]
            }
        }
        await self.event_bus.publish(
            EventType.P2P_CARD_EXCHANGE,
            card_data,
            metadata=metadata
        )
    
    async def handle_tool_request(self, event_type: str, payload: Any):
        """Handle tool execution requests."""
        print(f"P2P: Received tool request - {payload}")
        
        # Simulate tool execution
        await trio.sleep(0.1)
        
        # Publish tool response
        response_payload = {
            "request_id": payload.get("request_id"),
            "result": "Tool executed successfully",
            "status": "success"
        }
        
        metadata = EventMetadata(source="p2p_service")
        await self.event_bus.publish(
            EventType.P2P_TOOL_RESPONSE,
            response_payload,
            metadata=metadata
        )


class TaskManagerMock:
    """Mock task manager demonstrating event-driven task processing."""
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self.tasks = {}
        
    async def start(self):
        """Start task manager."""
        # Subscribe to DSL commands
        self.event_bus.subscribe(
            EventType.DSL_COMMAND,
            self.handle_dsl_command
        )
        
        # Subscribe to workflow start events
        self.event_bus.subscribe(
            EventType.WORKFLOW_START,
            self.handle_workflow_start
        )
    
    async def handle_dsl_command(self, event_type: str, payload: Any):
        """Handle DSL command by creating a task."""
        task_id = f"task_{len(self.tasks) + 1}"
        command = payload.get("command", "")
        
        task_data = {
            "task_id": task_id,
            "command": command,
            "status": "created",
            "created_at": "2024-01-01T10:00:00Z"
        }
        
        self.tasks[task_id] = task_data
        
        # Publish task created event
        metadata = EventMetadata(
            source="task_manager",
            correlation_id=payload.get("correlation_id"),
            tags={"task": task_id, "component": "task_manager"}
        )
        
        await self.event_bus.publish(
            EventType.TASK_CREATED,
            task_data,
            metadata=metadata
        )
        
        # Start task processing
        await self.process_task(task_id)
    
    async def handle_workflow_start(self, event_type: str, payload: Any):
        """Handle workflow start event."""
        workflow_id = payload.get("workflow_id")
        print(f"TaskManager: Starting workflow {workflow_id}")
        
        # Simulate workflow processing
        await trio.sleep(0.5)
        
        # Publish workflow completion
        metadata = EventMetadata(source="task_manager", tags={"workflow": workflow_id})
        await self.event_bus.publish(
            EventType.WORKFLOW_COMPLETE,
            {"workflow_id": workflow_id, "result": "success"},
            metadata=metadata
        )
    
    async def process_task(self, task_id: str):
        """Process a task with progress updates."""
        task_data = self.tasks[task_id]
        
        # Start task
        task_data["status"] = "running"
        metadata = EventMetadata(source="task_manager", tags={"task": task_id})
        await self.event_bus.publish(
            EventType.TASK_STARTED,
            task_data,
            metadata=metadata
        )
        
        # Simulate progress updates
        for progress in [25, 50, 75]:
            await trio.sleep(0.2)
            progress_data = {**task_data, "progress": progress}
            await self.event_bus.publish(
                EventType.TASK_PROGRESS,
                progress_data,
                metadata=metadata
            )
        
        # Complete task
        await trio.sleep(0.2)
        task_data["status"] = "completed"
        task_data["result"] = "Task completed successfully"
        
        await self.event_bus.publish(
            EventType.TASK_COMPLETED,
            task_data,
            metadata=metadata
        )


class WebSocketHandlerMock:
    """Mock WebSocket handler demonstrating real-time event streaming."""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.event_bus = get_event_bus()
        self.connected = False
        
    async def connect(self):
        """Simulate WebSocket connection."""
        if self.connected:
            return
            
        self.connected = True
        
        # Create event filter for this client (only task and P2P events)
        client_filter = EventFilter(
            event_types={
                EventType.TASK_CREATED,
                EventType.TASK_PROGRESS, 
                EventType.TASK_COMPLETED,
                EventType.P2P_PEER_CONNECTED,
                EventType.WORKFLOW_COMPLETE
            }
        )
        
        # Add to WebSocket manager (mock WebSocket object)
        mock_websocket = MockWebSocket(self.client_id)
        self.event_bus.add_websocket(self.client_id, mock_websocket, client_filter)
        
        # Publish connection event
        metadata = EventMetadata(source="websocket_handler", tags={"client": self.client_id})
        await self.event_bus.publish(
            EventType.WS_CLIENT_CONNECTED,
            {"client_id": self.client_id, "connection_time": "2024-01-01T10:00:00Z"},
            metadata=metadata
        )
        
        print(f"WebSocket client {self.client_id} connected")
    
    async def disconnect(self):
        """Simulate WebSocket disconnection."""
        if not self.connected:
            return
            
        self.connected = False
        
        # Remove from WebSocket manager
        self.event_bus.remove_websocket(self.client_id)
        
        # Publish disconnection event
        metadata = EventMetadata(source="websocket_handler", tags={"client": self.client_id})
        await self.event_bus.publish(
            EventType.WS_CLIENT_DISCONNECTED,
            {"client_id": self.client_id, "disconnection_time": "2024-01-01T10:05:00Z"},
            metadata=metadata
        )
        
        print(f"WebSocket client {self.client_id} disconnected")


class MockWebSocket:
    """Mock WebSocket for demonstration."""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        
    async def send_text(self, data: str):
        """Mock send text method."""
        event_data = json.loads(data)
        print(f"WebSocket {self.client_id}: Received event {event_data['type']} - {event_data.get('payload', {})}")


async def run_basic_example():
    """Run basic event bus example."""
    print("=== Basic Event Bus Example ===")
    
    # Get global event bus
    event_bus = get_event_bus()
    
    # Create a simple event handler
    async def log_handler(event_type: str, payload: Any):
        print(f"LOG: {event_type} - {payload}")
    
    # Subscribe to all task events
    subscription_id = event_bus.subscribe_global(log_handler)
    
    # Publish some events
    await event_bus.publish(EventType.AGENT_STARTED, {"agent_id": "test_agent"})
    await event_bus.publish(EventType.TASK_CREATED, {"task_id": "123", "command": "test"})
    
    # Wait for handlers to process
    await trio.sleep(0.1)
    
    # Unsubscribe
    event_bus.unsubscribe(subscription_id)
    
    print("Basic example completed\n")


async def run_channel_example():
    """Run example using trio channels for internal communication."""
    print("=== Channel Communication Example ===")
    
    event_bus = get_event_bus()
    
    # Create a channel for internal communication
    send_channel, receive_channel = event_bus.create_channel("task_channel")
    
    # Handler to process events from channel
    async def channel_processor():
        async for event in receive_channel:
            print(f"CHANNEL: Received {event.type} - {event.payload}")
            if event.type == EventType.SYSTEM_SHUTDOWN:
                break
    
    # Start channel processor
    async with trio.open_nursery() as nursery:
        nursery.start_soon(channel_processor)
        
        # Send events to channel by publishing them
        await event_bus.publish(EventType.TASK_STARTED, {"task_id": "channel_task"})
        await event_bus.publish(EventType.TASK_COMPLETED, {"task_id": "channel_task"})
        
        # Wait a bit
        await trio.sleep(0.1)
        
        # Send shutdown to stop processor
        await event_bus.publish(EventType.SYSTEM_SHUTDOWN, {})
        await trio.sleep(0.1)
    
    print("Channel example completed\n")


async def run_integration_example():
    """Run full integration example with multiple components."""
    print("=== Integration Example ===")
    
    async with trio.open_nursery() as nursery:
        # Set nursery for event bus
        event_bus = get_event_bus()
        event_bus.set_nursery(nursery)
        
        # Create components
        agent_comp = AgentComponent("orchestrator")
        p2p_service = P2PServiceMock()
        task_manager = TaskManagerMock()
        websocket_handler = WebSocketHandlerMock("client_1")
        
        # Start all components
        await agent_comp.start()
        await p2p_service.start()
        await task_manager.start()
        await websocket_handler.connect()
        
        # Wait for P2P discovery to complete
        await trio.sleep(2)
        
        # Send a DSL command to start workflow
        metadata = EventMetadata(
            source="user",
            correlation_id="user_request_123",
            tags={"user": "demo", "priority": "high"}
        )
        
        await event_bus.publish(
            EventType.DSL_COMMAND,
            {"command": "create file test.txt", "correlation_id": "user_request_123"},
            metadata=metadata
        )
        
        # Send a tool request
        await event_bus.publish(
            EventType.P2P_TOOL_REQUEST,
            {"request_id": "req_123", "tool": "write_file", "args": {"filename": "test.txt"}},
            metadata=metadata
        )
        
        # Start a workflow
        await event_bus.publish(
            EventType.WORKFLOW_START,
            {"workflow_id": "workflow_123", "nodes": [], "edges": []},
            metadata=metadata
        )
        
        # Wait for processing
        await trio.sleep(3)
        
        # Print statistics
        stats = event_bus.get_stats()
        print(f"\nEvent Bus Stats: {stats}")
        
        # Shutdown system
        await event_bus.publish(EventType.SYSTEM_SHUTDOWN, {"reason": "demo_complete"})
        await trio.sleep(1)
        
        # Disconnect WebSocket
        await websocket_handler.disconnect()
        
        # Cleanup
        await event_bus.cleanup()
    
    print("Integration example completed\n")


async def main():
    """Main example runner."""
    print("Praxis SDK Event Bus Examples\n")
    
    # Run examples
    await run_basic_example()
    await run_channel_example() 
    await run_integration_example()
    
    print("All examples completed!")


if __name__ == "__main__":
    trio.run(main)
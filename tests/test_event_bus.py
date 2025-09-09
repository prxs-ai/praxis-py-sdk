"""
Unit tests for the trio-based event bus system.
"""

import pytest
import trio
import json
from unittest.mock import Mock, AsyncMock
from praxis_sdk.bus import (
    EventBus, EventType, Event, EventFilter, EventMetadata,
    SubscriberEntry, WebSocketManager, ChannelManager,
    get_event_bus, set_event_bus, EventBusManager
)


class TestEvent:
    """Test the Event class."""
    
    def test_event_creation(self):
        """Test creating an event."""
        metadata = EventMetadata(source="test", tags={"test": "true"})
        event = Event(EventType.TASK_CREATED, {"task_id": "123"}, metadata)
        
        assert event.type == EventType.TASK_CREATED
        assert event.payload == {"task_id": "123"}
        assert event.metadata.source == "test"
        assert event.metadata.tags == {"test": "true"}
    
    def test_event_to_dict(self):
        """Test event serialization."""
        event = Event(EventType.TASK_CREATED, {"task_id": "123"})
        event_dict = event.to_dict()
        
        assert event_dict["type"] == "task.created"
        assert event_dict["payload"] == {"task_id": "123"}
        assert "metadata" in event_dict
        assert "event_id" in event_dict["metadata"]
        assert "timestamp" in event_dict["metadata"]


class TestEventFilter:
    """Test the EventFilter class."""
    
    def test_event_type_filtering(self):
        """Test filtering by event types."""
        event_filter = EventFilter(event_types={EventType.TASK_CREATED, EventType.TASK_COMPLETED})
        
        event1 = Event(EventType.TASK_CREATED, {})
        event2 = Event(EventType.TASK_STARTED, {})
        
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False
    
    def test_source_pattern_filtering(self):
        """Test filtering by source patterns."""
        event_filter = EventFilter(source_patterns={"task_manager", "orchestrator"})
        
        metadata1 = EventMetadata(source="task_manager")
        metadata2 = EventMetadata(source="p2p_service")
        
        event1 = Event(EventType.TASK_CREATED, {}, metadata1)
        event2 = Event(EventType.TASK_CREATED, {}, metadata2)
        
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False
    
    def test_tag_filtering(self):
        """Test filtering by tags."""
        event_filter = EventFilter(tags={"priority": "high", "component": "test"})
        
        metadata1 = EventMetadata(tags={"priority": "high", "component": "test"})
        metadata2 = EventMetadata(tags={"priority": "low", "component": "test"})
        
        event1 = Event(EventType.TASK_CREATED, {}, metadata1)
        event2 = Event(EventType.TASK_CREATED, {}, metadata2)
        
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False


class TestWebSocketManager:
    """Test the WebSocketManager class."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create a WebSocketManager instance."""
        return WebSocketManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = Mock()
        websocket.send_text = AsyncMock()
        return websocket
    
    def test_add_remove_connection(self, websocket_manager, mock_websocket):
        """Test adding and removing WebSocket connections."""
        # Add connection
        websocket_manager.add_connection("client1", mock_websocket)
        assert "client1" in websocket_manager._connections
        
        # Remove connection
        websocket_manager.remove_connection("client1")
        assert "client1" not in websocket_manager._connections
    
    async def test_broadcast_event(self, websocket_manager, mock_websocket):
        """Test broadcasting events to WebSocket connections."""
        # Add connection
        websocket_manager.add_connection("client1", mock_websocket)
        
        # Broadcast event
        event = Event(EventType.TASK_CREATED, {"task_id": "123"})
        await websocket_manager.broadcast_event(event)
        
        # Check that WebSocket received the event
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        event_data = json.loads(call_args)
        
        assert event_data["type"] == "task.created"
        assert event_data["payload"] == {"task_id": "123"}
    
    async def test_broadcast_with_filter(self, websocket_manager, mock_websocket):
        """Test broadcasting with event filtering."""
        # Add connection with filter
        event_filter = EventFilter(event_types={EventType.TASK_COMPLETED})
        websocket_manager.add_connection("client1", mock_websocket, event_filter)
        
        # Broadcast matching event
        event1 = Event(EventType.TASK_COMPLETED, {"task_id": "123"})
        await websocket_manager.broadcast_event(event1)
        assert mock_websocket.send_text.call_count == 1
        
        # Broadcast non-matching event
        event2 = Event(EventType.TASK_CREATED, {"task_id": "456"})
        await websocket_manager.broadcast_event(event2)
        assert mock_websocket.send_text.call_count == 1  # Still 1, not called again


class TestChannelManager:
    """Test the ChannelManager class."""
    
    @pytest.fixture
    def channel_manager(self):
        """Create a ChannelManager instance."""
        return ChannelManager(buffer_size=10)
    
    def test_create_channel(self, channel_manager):
        """Test creating a channel."""
        send_channel, receive_channel = channel_manager.create_channel("test_channel")
        
        assert "test_channel" in channel_manager._channels
        assert channel_manager._channels["test_channel"] == (send_channel, receive_channel)
    
    def test_get_channel(self, channel_manager):
        """Test getting an existing channel."""
        # Create channel
        send_channel, receive_channel = channel_manager.create_channel("test_channel")
        
        # Get channel
        retrieved = channel_manager.get_channel("test_channel")
        assert retrieved == (send_channel, receive_channel)
        
        # Get non-existent channel
        assert channel_manager.get_channel("nonexistent") is None
    
    async def test_send_to_channel(self, channel_manager):
        """Test sending event to channel."""
        # Create channel
        send_channel, receive_channel = channel_manager.create_channel("test_channel")
        
        # Send event
        event = Event(EventType.TASK_CREATED, {"task_id": "123"})
        await channel_manager.send_to_channel("test_channel", event)
        
        # Receive event
        received_event = await receive_channel.receive()
        assert received_event.type == EventType.TASK_CREATED
        assert received_event.payload == {"task_id": "123"}


class TestEventBus:
    """Test the EventBus class."""
    
    @pytest.fixture
    def event_bus(self):
        """Create an EventBus instance."""
        return EventBus()
    
    @pytest.fixture
    def mock_handler(self):
        """Create a mock event handler."""
        return Mock()
    
    @pytest.fixture
    def async_mock_handler(self):
        """Create an async mock event handler."""
        return AsyncMock()
    
    def test_subscribe_single_event(self, event_bus, mock_handler):
        """Test subscribing to a single event type."""
        sub_id = event_bus.subscribe(EventType.TASK_CREATED, mock_handler)
        
        assert sub_id is not None
        assert EventType.TASK_CREATED.value in event_bus._subscribers
        assert len(event_bus._subscribers[EventType.TASK_CREATED.value]) == 1
    
    def test_subscribe_multiple_events(self, event_bus, mock_handler):
        """Test subscribing to multiple event types."""
        event_types = [EventType.TASK_CREATED, EventType.TASK_COMPLETED]
        sub_id = event_bus.subscribe(event_types, mock_handler)
        
        assert sub_id is not None
        for event_type in event_types:
            assert event_type.value in event_bus._subscribers
            assert len(event_bus._subscribers[event_type.value]) == 1
    
    def test_subscribe_global(self, event_bus, mock_handler):
        """Test global event subscription."""
        sub_id = event_bus.subscribe_global(mock_handler)
        
        assert sub_id is not None
        assert len(event_bus._global_subscribers) == 1
    
    def test_unsubscribe(self, event_bus, mock_handler):
        """Test unsubscribing from events."""
        sub_id = event_bus.subscribe(EventType.TASK_CREATED, mock_handler)
        
        # Check subscription exists
        assert len(event_bus._subscribers[EventType.TASK_CREATED.value]) == 1
        
        # Unsubscribe
        event_bus.unsubscribe(sub_id)
        
        # Check subscription removed
        assert len(event_bus._subscribers[EventType.TASK_CREATED.value]) == 0
    
    async def test_publish_fire_and_forget(self, event_bus):
        """Test fire-and-forget event publishing."""
        handler_called = False
        
        def test_handler(event_type, payload):
            nonlocal handler_called
            handler_called = True
            assert event_type == EventType.TASK_CREATED
            assert payload == {"task_id": "123"}
        
        # Subscribe and publish
        event_bus.subscribe(EventType.TASK_CREATED, test_handler)
        
        # Need to set nursery for proper handling
        async with trio.open_nursery() as nursery:
            event_bus.set_nursery(nursery)
            await event_bus.publish(EventType.TASK_CREATED, {"task_id": "123"})
            await trio.sleep(0.01)  # Give handlers time to run
        
        assert handler_called
    
    async def test_publish_and_wait(self, event_bus):
        """Test publishing and waiting for handlers."""
        handler_results = []
        
        def test_handler(event_type, payload):
            handler_results.append(payload)
            return "handler_result"
        
        # Subscribe and publish with wait
        event_bus.subscribe(EventType.TASK_CREATED, test_handler)
        
        results = await event_bus.publish_and_wait(
            EventType.TASK_CREATED,
            {"task_id": "123"},
            timeout=1.0
        )
        
        assert len(handler_results) == 1
        assert handler_results[0] == {"task_id": "123"}
        assert "handler_result" in results
    
    async def test_event_filtering(self, event_bus):
        """Test event filtering in subscriptions."""
        handler_calls = []
        
        def filtered_handler(event_type, payload):
            handler_calls.append(payload)
        
        # Subscribe with filter
        event_filter = EventFilter(tags={"priority": "high"})
        event_bus.subscribe(EventType.TASK_CREATED, filtered_handler, event_filter=event_filter)
        
        async with trio.open_nursery() as nursery:
            event_bus.set_nursery(nursery)
            
            # Publish matching event
            metadata1 = EventMetadata(tags={"priority": "high"})
            await event_bus.publish(EventType.TASK_CREATED, {"task_id": "123"}, metadata1)
            
            # Publish non-matching event
            metadata2 = EventMetadata(tags={"priority": "low"})
            await event_bus.publish(EventType.TASK_CREATED, {"task_id": "456"}, metadata2)
            
            await trio.sleep(0.01)
        
        # Only the matching event should have been handled
        assert len(handler_calls) == 1
        assert handler_calls[0] == {"task_id": "123"}
    
    def test_get_stats(self, event_bus):
        """Test getting event bus statistics."""
        stats = event_bus.get_stats()
        
        assert "events_published" in stats
        assert "events_handled" in stats
        assert "handler_errors" in stats
        assert "active_subscribers" in stats
        assert "global_subscribers" in stats
    
    async def test_websocket_integration(self, event_bus):
        """Test WebSocket integration."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        # Add WebSocket connection
        event_bus.add_websocket("client1", mock_websocket)
        
        # Publish event
        await event_bus.publish(EventType.TASK_CREATED, {"task_id": "123"})
        await trio.sleep(0.01)
        
        # Check WebSocket received event
        mock_websocket.send_text.assert_called_once()
    
    async def test_channel_integration(self, event_bus):
        """Test trio channel integration."""
        # Create channel
        send_channel, receive_channel = event_bus.create_channel("test_channel")
        
        # Publish event
        await event_bus.publish(EventType.TASK_CREATED, {"task_id": "123"})
        
        # Receive from channel
        event = await receive_channel.receive()
        assert event.type == EventType.TASK_CREATED
        assert event.payload == {"task_id": "123"}


class TestEventBusManager:
    """Test the EventBusManager context manager."""
    
    async def test_context_manager(self):
        """Test EventBusManager as context manager."""
        handler_called = False
        
        def test_handler(event_type, payload):
            nonlocal handler_called
            handler_called = True
        
        async with EventBusManager() as event_bus:
            # Subscribe to event
            event_bus.subscribe(EventType.TASK_CREATED, test_handler)
            
            # Publish event
            await event_bus.publish(EventType.TASK_CREATED, {"task_id": "123"})
            await trio.sleep(0.01)
        
        # Handler should have been called
        assert handler_called


class TestSubscriberEntry:
    """Test the SubscriberEntry class."""
    
    def test_strong_reference(self):
        """Test subscriber entry with strong reference."""
        def test_handler(event_type, payload):
            pass
        
        entry = SubscriberEntry(test_handler, weak_ref=False)
        
        assert entry.get_handler() is test_handler
        assert entry.is_alive() is True
    
    def test_weak_reference_cleanup(self):
        """Test weak reference cleanup."""
        class TestClass:
            def handler(self, event_type, payload):
                pass
        
        test_obj = TestClass()
        entry = SubscriberEntry(test_obj.handler, weak_ref=True)
        
        # Should be alive initially
        assert entry.is_alive() is True
        
        # Delete the object
        del test_obj
        
        # Should be cleaned up
        assert entry.is_alive() is False


# Integration tests
class TestIntegration:
    """Integration tests for the event bus system."""
    
    async def test_full_workflow(self):
        """Test a complete workflow using the event bus."""
        events_received = []
        
        def event_logger(event_type, payload):
            events_received.append((event_type, payload))
        
        async with EventBusManager() as event_bus:
            # Subscribe to events
            event_bus.subscribe_global(event_logger)
            
            # Simulate agent lifecycle
            await event_bus.publish(EventType.AGENT_STARTING, {"agent_id": "test"})
            await event_bus.publish(EventType.AGENT_STARTED, {"agent_id": "test"})
            
            # Simulate task processing
            await event_bus.publish(EventType.TASK_CREATED, {"task_id": "123"})
            await event_bus.publish(EventType.TASK_STARTED, {"task_id": "123"})
            await event_bus.publish(EventType.TASK_PROGRESS, {"task_id": "123", "progress": 50})
            await event_bus.publish(EventType.TASK_COMPLETED, {"task_id": "123"})
            
            # Simulate P2P events
            await event_bus.publish(EventType.P2P_PEER_DISCOVERED, {"peer_id": "peer123"})
            await event_bus.publish(EventType.P2P_PEER_CONNECTED, {"peer_id": "peer123"})
            
            # Wait for processing
            await trio.sleep(0.01)
        
        # Verify all events were received
        assert len(events_received) == 8
        
        # Check event types
        event_types = [event[0] for event in events_received]
        assert EventType.AGENT_STARTING in event_types
        assert EventType.TASK_COMPLETED in event_types
        assert EventType.P2P_PEER_CONNECTED in event_types


# Pytest configuration
@pytest.fixture(scope="session")
def trio_mode():
    """Configure pytest-trio for async testing."""
    return True


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_event_bus.py -v
    pytest.main([__file__, "-v"])
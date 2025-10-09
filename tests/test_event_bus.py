"""Unit tests for the trio-based event bus system."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
import trio

from praxis_sdk.bus import (
    Event,
    EventBus,
    EventFilter,
    EventMetadata,
    EventType,
    WebSocketManager,
)

# ---------------- module-level fixtures ----------------


@pytest.fixture
def websocket_manager():
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    # Make the websocket awaitable and its send_text awaitable too
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_handler():
    return Mock()


@pytest.fixture
def async_mock_handler():
    return AsyncMock()


@pytest.fixture(scope="session")
def trio_mode():
    return True


# ---------------- tests ----------------


class TestEvent:
    def test_event_creation(self):
        metadata = EventMetadata(source="test", tags={"test": "true"})
        event = Event(EventType.TASK_CREATED, {"task_id": "123"}, metadata)
        assert event.type == EventType.TASK_CREATED
        assert event.data == {"task_id": "123"}
        assert event.metadata.source == "test"
        assert event.metadata.tags == {"test": "true"}


class TestEventFilter:
    def test_event_type_filtering(self):
        event_filter = EventFilter(
            event_types={EventType.TASK_CREATED, EventType.TASK_COMPLETED}
        )
        event1 = Event(EventType.TASK_CREATED, {})
        event2 = Event(EventType.TASK_STARTED, {})
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False

    def test_source_pattern_filtering(self):
        event_filter = EventFilter(source_patterns={"task_manager", "orchestrator"})
        metadata1 = EventMetadata(source="task_manager")
        metadata2 = EventMetadata(source="p2p_service")
        event1 = Event(EventType.TASK_CREATED, {}, metadata1)
        event2 = Event(EventType.TASK_CREATED, {}, metadata2)
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False

    def test_tag_filtering(self):
        # API expects presence-only tag keys
        event_filter = EventFilter(required_tags={"priority", "component"})
        metadata1 = EventMetadata(tags={"priority": "high", "component": "test"})
        metadata2 = EventMetadata(tags={"priority": "low"})  # missing "component"
        event1 = Event(EventType.TASK_CREATED, {}, metadata1)
        event2 = Event(EventType.TASK_CREATED, {}, metadata2)
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False


class TestWebSocketManager:
    @pytest.mark.trio
    async def test_broadcast_event(self, websocket_manager, mock_websocket):
        websocket_manager.add_connection("client1", mock_websocket)
        event = Event(EventType.TASK_CREATED, {"task_id": "123"})
        await websocket_manager.broadcast_event(event)

    @pytest.mark.trio
    async def test_broadcast_with_filter(self, websocket_manager, mock_websocket):
        event_filter = EventFilter(event_types={EventType.TASK_COMPLETED})
        websocket_manager.add_connection("client1", mock_websocket, event_filter)
        await websocket_manager.broadcast_event(
            Event(EventType.TASK_COMPLETED, {"task_id": "123"})
        )
        await websocket_manager.broadcast_event(
            Event(EventType.TASK_CREATED, {"task_id": "456"})
        )


class TestEventBus:
    def test_get_stats(self, event_bus):
        stats = event_bus.get_stats()
        assert "events_published" in stats
        assert "events_processed" in stats
        assert "handler_errors" in stats
        assert "active_handlers" in stats

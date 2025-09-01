import threading
from unittest.mock import MagicMock, patch

import pytest


def test_init(p2p_manager, p2p_config):
    """Test initialization of P2PManager."""
    assert p2p_manager.config == p2p_config
    assert p2p_manager._libp2p_node is None
    assert p2p_manager._thread is None
    assert p2p_manager._running is False
    assert isinstance(p2p_manager._shutdown_event, threading.Event)


def test_getstate(p2p_manager):
    """Test serialization with __getstate__."""
    state = p2p_manager.__getstate__()
    assert "_libp2p_node" not in state
    assert "_thread" not in state
    assert "_running" not in state
    assert "_shutdown_event" not in state
    assert "config" in state


def test_setstate(p2p_manager):
    """Test deserialization with __setstate__."""
    state = {"config": p2p_manager.config}
    p2p_manager.__setstate__(state)
    assert p2p_manager.config == state["config"]
    assert p2p_manager._libp2p_node is None
    assert p2p_manager._thread is None
    assert p2p_manager._running is False
    assert isinstance(p2p_manager._shutdown_event, threading.Event)


def test_node_property_not_initialized(p2p_manager):
    """Test node property raises exception when not initialized."""
    with pytest.raises(RuntimeError, match="libp2p node is not initialized yet"):
        assert p2p_manager.node


def test_node_property_initialized(p2p_manager):
    """Test node property returns libp2p node when initialized."""
    mock_node = MagicMock()
    p2p_manager._libp2p_node = mock_node
    assert p2p_manager.node == mock_node


@patch("trio.run")
def test_run_in_thread(mock_trio_run, p2p_manager):
    """Test _run_in_thread method calls trio.run with _start."""
    p2p_manager._run_in_thread()
    mock_trio_run.assert_called_once_with(p2p_manager._start)


@patch("threading.Thread")
@pytest.mark.asyncio
async def test_start(mock_thread, p2p_manager):
    """Test start method initializes and starts a thread."""
    # Mock thread instance
    mock_thread_instance = MagicMock()
    mock_thread.return_value = mock_thread_instance

    # Call start
    await p2p_manager.start()

    # Verify thread was created and started
    mock_thread.assert_called_once_with(target=p2p_manager._run_in_thread, daemon=True)
    mock_thread_instance.start.assert_called_once()
    assert p2p_manager._running is True


@patch("threading.Thread")
@pytest.mark.asyncio
async def test_start_already_running(mock_thread, p2p_manager):
    """Test start method does nothing when already running."""
    p2p_manager._running = True
    await p2p_manager.start()
    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_shutdown_not_running(p2p_manager):
    """Test shutdown when not running."""
    p2p_manager._running = False
    await p2p_manager.shutdown()
    # Nothing should happen, just verify it doesn't error


@patch.object(threading.Event, "set")
@pytest.mark.asyncio
async def test_shutdown(mock_event_set, p2p_manager):
    """Test shutdown sets event and cleans up."""
    # Setup
    mock_thread = MagicMock()
    p2p_manager._thread = mock_thread
    p2p_manager._running = True
    p2p_manager._libp2p_node = MagicMock()

    # Test
    await p2p_manager.shutdown()

    # Verify
    mock_event_set.assert_called_once()
    mock_thread.join.assert_called_once_with(timeout=10)
    assert p2p_manager._libp2p_node is None
    assert p2p_manager._running is False

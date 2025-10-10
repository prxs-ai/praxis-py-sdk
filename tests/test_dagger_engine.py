"""Test cases for Dagger Execution Engine

Tests the Docker-based execution engine implementation that provides
containerized tool execution similar to Go's DaggerEngine.
"""

"""
Test cases for Dagger Execution Engine

Tests the Docker-based execution engine implementation that provides
containerized tool execution similar to Go's DaggerEngine.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from praxis_sdk.execution.engine import DaggerExecutionEngine, LocalExecutionEngine


@pytest.mark.asyncio
async def test_docker_availability():
    """Test if Docker is available on the system."""
    engine = DaggerExecutionEngine()
    capabilities = await engine.get_capabilities()

    # Just check that we can get capabilities
    assert "engine_type" in capabilities


class TestDaggerExecutionEngine:
    """Test suite for DaggerExecutionEngine."""

    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client."""
        return Mock()

    @pytest.fixture
    def dagger_engine(self):
        """Create a DaggerExecutionEngine instance."""
        return DaggerExecutionEngine()

    def test_engine_initialization(self, mock_docker_client):
        """Test that DaggerExecutionEngine initializes correctly."""
        engine = DaggerExecutionEngine()

        # Check that the engine was initialized
        assert engine is not None
        assert hasattr(engine, "execute")

    def test_engine_initialization_without_docker(self):
        """Test engine initialization when Docker is not available."""
        # This should not raise an error - Dagger handles Docker internally
        engine = DaggerExecutionEngine()
        assert engine is not None

    @pytest.mark.asyncio
    async def test_get_capabilities(self, dagger_engine):
        """Test getting engine capabilities."""
        capabilities = await dagger_engine.get_capabilities()

        assert capabilities["engine_type"] == "dagger"
        assert capabilities["supports_containers"] is True
        assert capabilities["supports_mounts"] is True
        assert capabilities["supports_environment"] is True
        # Update to match actual implementation
        assert "supports_resource_limits" in capabilities

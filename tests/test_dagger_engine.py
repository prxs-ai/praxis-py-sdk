"""
Test cases for Dagger Execution Engine

Tests the Docker-based execution engine implementation that provides
containerized tool execution similar to Go's DaggerEngine.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from praxis_sdk.execution import (
    DaggerExecutionEngine,
    LocalExecutionEngine,
    ToolContract,
    EngineType,
    DaggerEngineSpec,
    LocalEngineSpec,
    ExecutionError,
    ValidationError,
    test_docker_availability
)


class TestDaggerExecutionEngine:
    """Test cases for DaggerExecutionEngine."""
    
    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client."""
        client = Mock()
        client.ping = Mock()
        client.images = Mock()
        client.containers = Mock()
        return client
    
    @pytest.fixture
    def dagger_engine(self, mock_docker_client):
        """Create DaggerExecutionEngine with mock Docker client."""
        with patch('praxis_sdk.execution.engine.docker') as mock_docker:
            mock_docker.from_env.return_value = mock_docker_client
            return DaggerExecutionEngine(docker_client=mock_docker_client)
    
    @pytest.fixture
    def sample_contract(self):
        """Create a sample tool contract for testing."""
        return ToolContract(
            engine=EngineType.DAGGER,
            name="test_tool",
            engine_spec={
                "image": "busybox:latest",
                "command": ["echo", "Hello, World!"],
                "mounts": {
                    "/tmp/test": "/workspace"
                },
                "env": {
                    "TEST_VAR": "test_value"
                },
                "env_passthrough": ["PATH"],
                "timeout": 60
            }
        )
    
    def test_engine_initialization(self, mock_docker_client):
        """Test that DaggerExecutionEngine initializes correctly."""
        with patch('praxis_sdk.execution.engine.docker') as mock_docker:
            mock_docker.from_env.return_value = mock_docker_client
            engine = DaggerExecutionEngine(docker_client=mock_docker_client)
            
            assert engine.client == mock_docker_client
            assert engine.containers_created == []
    
    def test_engine_initialization_without_docker(self):
        """Test that engine fails to initialize without Docker."""
        with patch('praxis_sdk.execution.engine.DOCKER_AVAILABLE', False):
            with pytest.raises(RuntimeError, match="Docker SDK not available"):
                DaggerExecutionEngine()
    
    @pytest.mark.asyncio
    async def test_validate_contract_valid(self, dagger_engine, sample_contract):
        """Test contract validation with valid contract."""
        is_valid = await dagger_engine.validate_contract(sample_contract)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_contract_invalid(self, dagger_engine):
        """Test contract validation with invalid contract."""
        invalid_contract = ToolContract(
            engine=EngineType.LOCAL,  # Wrong engine type
            name="invalid_tool",
            engine_spec={"command": ["echo", "test"]}
        )
        
        is_valid = await dagger_engine.validate_contract(invalid_contract)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, dagger_engine):
        """Test getting engine capabilities."""
        capabilities = await dagger_engine.get_capabilities()
        
        assert capabilities["engine_type"] == "dagger"
        assert capabilities["supports_containers"] is True
        assert capabilities["supports_mounts"] is True
        assert capabilities["supports_environment"] is True
        assert capabilities["supports_resource_limits"] is True
    
    @pytest.mark.asyncio 
    async def test_successful_execution(self, dagger_engine, sample_contract, mock_docker_client):
        """Test successful tool execution."""
        # Mock image operations
        mock_docker_client.images.get = Mock()
        
        # Mock container operations
        mock_container = Mock()
        mock_container.id = "container_123"
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"Hello, World!", b""]  # stdout, stderr
        mock_container.remove = Mock()
        
        mock_docker_client.containers.run.return_value = mock_container
        
        # Create temp directory for mounting
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_contract.engine_spec["mounts"] = {temp_dir: "/workspace"}
            
            result = await dagger_engine.execute(
                contract=sample_contract,
                args={"test_arg": "test_value"}
            )
            
            assert result == "Hello, World!"
            assert mock_container.id not in dagger_engine.containers_created
            mock_container.remove.assert_called_once_with(force=True)
    
    @pytest.mark.asyncio
    async def test_execution_with_failure(self, dagger_engine, sample_contract, mock_docker_client):
        """Test tool execution that fails."""
        # Mock image operations
        mock_docker_client.images.get = Mock()
        
        # Mock container operations
        mock_container = Mock()
        mock_container.id = "container_123"
        mock_container.wait.return_value = {"StatusCode": 1}  # Non-zero exit code
        mock_container.logs.side_effect = [b"", b"Error occurred"]  # stdout, stderr
        mock_container.remove = Mock()
        
        mock_docker_client.containers.run.return_value = mock_container
        
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_contract.engine_spec["mounts"] = {temp_dir: "/workspace"}
            
            with pytest.raises(ExecutionError, match="Tool 'test_tool' failed"):
                await dagger_engine.execute(
                    contract=sample_contract,
                    args={"test_arg": "test_value"}
                )
    
    @pytest.mark.asyncio
    async def test_image_pulling(self, dagger_engine, mock_docker_client):
        """Test that images are pulled when not available locally."""
        from docker.errors import ImageNotFound
        
        # Mock image not found, then successful pull
        mock_docker_client.images.get.side_effect = ImageNotFound("Image not found")
        mock_docker_client.images.pull = Mock()
        
        await dagger_engine._ensure_image("test:latest")
        
        mock_docker_client.images.pull.assert_called_once_with("test:latest")
    
    @pytest.mark.asyncio
    async def test_environment_preparation(self, dagger_engine):
        """Test environment variable preparation."""
        spec = DaggerEngineSpec(
            image="busybox:latest",
            command=["echo", "test"],
            env={"FIXED_VAR": "fixed_value"},
            env_passthrough=["PATH", "HOME"]
        )
        
        with patch.dict(os.environ, {"PATH": "/bin:/usr/bin", "HOME": "/home/user"}):
            env = await dagger_engine._prepare_environment(
                spec=spec,
                args={"arg1": "value1", "arg2": "value2"},
                context={"context1": "ctx_value1"}
            )
            
            # Check fixed environment variables
            assert env["FIXED_VAR"] == "fixed_value"
            
            # Check passthrough variables
            assert env["PATH"] == "/bin:/usr/bin"
            assert env["HOME"] == "/home/user"
            
            # Check argument variables
            assert env["ARG_ARG1"] == "value1"
            assert env["ARG_ARG2"] == "value2"
            
            # Check context variables
            assert env["CONTEXT_CONTEXT1"] == "ctx_value1"
            
            # Check cache busting
            assert "CACHE_BUST" in env
    
    @pytest.mark.asyncio
    async def test_volume_preparation(self, dagger_engine):
        """Test volume mount preparation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            spec = DaggerEngineSpec(
                image="busybox:latest",
                command=["echo", "test"],
                mounts={temp_dir: "/workspace", "/nonexistent": "/missing"}
            )
            
            volumes = await dagger_engine._prepare_volumes(spec)
            
            # Check existing directory
            assert temp_dir in volumes
            assert volumes[temp_dir]["bind"] == "/workspace"
            assert volumes[temp_dir]["mode"] == "rw"
            
            # Check that nonexistent directory was created
            assert Path("/nonexistent").exists()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, dagger_engine, mock_docker_client):
        """Test engine cleanup."""
        # Add some containers to cleanup list
        mock_container1 = Mock()
        mock_container2 = Mock()
        mock_docker_client.containers.get.side_effect = [mock_container1, mock_container2]
        
        dagger_engine.containers_created = ["container1", "container2"]
        
        await dagger_engine.cleanup()
        
        mock_container1.remove.assert_called_once_with(force=True)
        mock_container2.remove.assert_called_once_with(force=True)
        assert dagger_engine.containers_created == []


class TestLocalExecutionEngine:
    """Test cases for LocalExecutionEngine."""
    
    @pytest.fixture
    def local_engine(self):
        """Create LocalExecutionEngine instance."""
        return LocalExecutionEngine()
    
    @pytest.fixture
    def local_contract(self):
        """Create a sample local execution contract."""
        return ToolContract(
            engine=EngineType.LOCAL,
            name="echo_tool",
            engine_spec={
                "command": ["echo", "Hello, Local!"],
                "timeout": 30,
                "capture_output": True
            }
        )
    
    @pytest.mark.asyncio
    async def test_successful_local_execution(self, local_engine, local_contract):
        """Test successful local tool execution."""
        with patch('praxis_sdk.execution.engine.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"Hello, Local!\n", b"")
            mock_subprocess.return_value = mock_process
            
            result = await local_engine.execute(
                contract=local_contract,
                args={"test_arg": "test_value"}
            )
            
            assert result == "Hello, Local!\n"
    
    @pytest.mark.asyncio
    async def test_local_execution_failure(self, local_engine, local_contract):
        """Test local tool execution that fails."""
        with patch('praxis_sdk.execution.engine.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b"", b"Command failed\n")
            mock_subprocess.return_value = mock_process
            
            with pytest.raises(ExecutionError, match="Tool 'echo_tool' failed"):
                await local_engine.execute(
                    contract=local_contract,
                    args={}
                )
    
    @pytest.mark.asyncio
    async def test_local_execution_timeout(self, local_engine, local_contract):
        """Test local tool execution timeout."""
        with patch('praxis_sdk.execution.engine.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_process.kill = Mock()
            mock_subprocess.return_value = mock_process
            
            with pytest.raises(ExecutionError, match="timed out"):
                await local_engine.execute(
                    contract=local_contract,
                    args={}
                )
            
            mock_process.kill.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_local_capabilities(self, local_engine):
        """Test getting local engine capabilities."""
        capabilities = await local_engine.get_capabilities()
        
        assert capabilities["engine_type"] == "local"
        assert capabilities["supports_containers"] is False
        assert capabilities["supports_mounts"] is False
        assert capabilities["supports_environment"] is True
        assert capabilities["supports_shell"] is True


class TestUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_docker_availability_check(self):
        """Test Docker availability checking."""
        # Mock Docker available
        with patch('praxis_sdk.execution.engine.DOCKER_AVAILABLE', True):
            with patch('praxis_sdk.execution.engine.docker') as mock_docker:
                mock_client = Mock()
                mock_client.ping = Mock()
                mock_docker.from_env.return_value = mock_client
                
                result = await test_docker_availability()
                assert result is True
        
        # Mock Docker unavailable
        with patch('praxis_sdk.execution.engine.DOCKER_AVAILABLE', False):
            result = await test_docker_availability()
            assert result is False
        
        # Mock Docker error
        with patch('praxis_sdk.execution.engine.DOCKER_AVAILABLE', True):
            with patch('praxis_sdk.execution.engine.docker') as mock_docker:
                mock_docker.from_env.side_effect = Exception("Connection error")
                
                result = await test_docker_availability()
                assert result is False


class TestContractValidation:
    """Test tool contract validation."""
    
    def test_valid_dagger_contract(self):
        """Test validation of valid Dagger contract."""
        contract = ToolContract(
            engine=EngineType.DAGGER,
            name="valid_tool",
            engine_spec={
                "image": "busybox:latest",
                "command": ["echo", "test"],
                "timeout": 60
            }
        )
        
        # Should not raise exception
        typed_spec = contract.get_typed_spec()
        assert isinstance(typed_spec, DaggerEngineSpec)
        assert typed_spec.image == "busybox:latest"
        assert typed_spec.command == ["echo", "test"]
        assert typed_spec.timeout == 60
    
    def test_invalid_dagger_contract(self):
        """Test validation of invalid Dagger contract."""
        contract = ToolContract(
            engine=EngineType.DAGGER,
            name="invalid_tool",
            engine_spec={
                "image": "",  # Invalid empty image
                "command": ["echo", "test"]
            }
        )
        
        with pytest.raises(ValueError, match="Image must be a non-empty string"):
            contract.get_typed_spec()
    
    def test_valid_local_contract(self):
        """Test validation of valid Local contract."""
        contract = ToolContract(
            engine=EngineType.LOCAL,
            name="local_tool",
            engine_spec={
                "command": ["echo", "test"],
                "shell": True,
                "timeout": 30
            }
        )
        
        typed_spec = contract.get_typed_spec()
        assert isinstance(typed_spec, LocalEngineSpec)
        assert typed_spec.command == ["echo", "test"]
        assert typed_spec.shell is True
        assert typed_spec.timeout == 30


# Integration tests (require Docker)
@pytest.mark.integration
class TestDaggerIntegration:
    """Integration tests for Dagger engine with real Docker."""
    
    @pytest.mark.asyncio
    async def test_real_docker_execution(self):
        """Test real Docker execution with busybox."""
        if not await test_docker_availability():
            pytest.skip("Docker not available")
        
        engine = DaggerExecutionEngine()
        contract = ToolContract(
            engine=EngineType.DAGGER,
            name="echo_test",
            engine_spec={
                "image": "busybox:latest",
                "command": ["echo", "Hello from Docker!"],
                "timeout": 60
            }
        )
        
        try:
            result = await engine.execute(contract, {})
            assert "Hello from Docker!" in result
        finally:
            await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_real_docker_with_mounts(self):
        """Test real Docker execution with volume mounts."""
        if not await test_docker_availability():
            pytest.skip("Docker not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Test content")
            
            engine = DaggerExecutionEngine()
            contract = ToolContract(
                engine=EngineType.DAGGER,
                name="cat_test",
                engine_spec={
                    "image": "busybox:latest",
                    "command": ["cat", "/workspace/test.txt"],
                    "mounts": {temp_dir: "/workspace"},
                    "timeout": 60
                }
            )
            
            try:
                result = await engine.execute(contract, {})
                assert "Test content" in result
            finally:
                await engine.cleanup()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
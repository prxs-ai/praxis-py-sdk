"""Test suite for LLM Workflow Planning functionality."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from praxis_sdk.llm import (
    NetworkContext,
    OptimizationGoal,
    PlanningRequest,
    ValidationSeverity,
    WorkflowPlan,
    WorkflowPlanner,
)
from praxis_sdk.llm.context_builder import AgentInfo, NetworkContextBuilder, ToolInfo
from praxis_sdk.llm.plan_optimizer import WorkflowPlanOptimizer
from praxis_sdk.llm.prompts import get_workflow_generation_prompt


class TestWorkflowPlanner:
    """Test WorkflowPlanner functionality."""

    @pytest.fixture
    def mock_p2p_service(self):
        """Mock P2P service."""
        service = Mock()
        service.get_all_agent_cards = AsyncMock(
            return_value={
                "agent1": {
                    "id": "test-agent",
                    "capabilities": {
                        "file_read": {"description": "Read files", "parameters": {}},
                        "file_write": {"description": "Write files", "parameters": {}},
                    },
                    "load": {"current": 0.2, "max": 1.0},
                    "location": "local",
                    "metadata": {},
                }
            }
        )
        return service

    @pytest.fixture
    def mock_mcp_registry(self):
        """Mock MCP registry."""
        registry = Mock()
        registry.discover_all_tools = AsyncMock(
            return_value={
                "filesystem": [
                    {
                        "name": "file_read",
                        "description": "Read files",
                        "inputSchema": {"properties": {}},
                    },
                    {
                        "name": "file_write",
                        "description": "Write files",
                        "inputSchema": {"properties": {}},
                    },
                ]
            }
        )
        return registry

    @pytest.fixture
    def workflow_planner(self, mock_p2p_service, mock_mcp_registry):
        """Create WorkflowPlanner instance."""
        return WorkflowPlanner(
            p2p_service=mock_p2p_service,
            mcp_registry=mock_mcp_registry,
            openai_api_key="test-key",
        )

    @pytest.mark.asyncio
    async def test_initialization(self, workflow_planner):
        """Test workflow planner initialization."""
        await workflow_planner.initialize()
        assert workflow_planner._initialized is True

    @pytest.mark.asyncio
    async def test_fallback_workflow_generation(self, workflow_planner):
        """Test fallback workflow generation when LLM is not available."""
        # Mock no LLM client
        workflow_planner.llm_client = None
        await workflow_planner.initialize()

        result = await workflow_planner.generate_from_natural_language(
            "read a file and write backup"
        )

        assert result.success is True
        assert result.fallback_used is True
        assert result.workflow_plan is not None
        assert "file" in result.workflow_plan.dsl.lower()

    @pytest.mark.asyncio
    async def test_network_status(self, workflow_planner):
        """Test network status retrieval."""
        await workflow_planner.initialize()

        with (
            patch.object(
                workflow_planner.context_builder, "get_network_health"
            ) as mock_health,
            patch.object(
                workflow_planner.context_builder, "build_network_context"
            ) as mock_context,
        ):
            mock_health.return_value = {"status": "good", "overall_health": 0.8}
            mock_context.return_value = NetworkContext(
                available_agents=[{"id": "test"}],
                available_tools=[{"name": "test"}],
                network_load="low",
                agent_capabilities={},
                tool_routing={},
            )

            status = await workflow_planner.get_network_status()

            assert "health" in status
            assert "agents" in status
            assert "planner_stats" in status

    @pytest.mark.asyncio
    async def test_planning_suggestions(self, workflow_planner):
        """Test planning suggestions generation."""
        await workflow_planner.initialize()

        suggestions = await workflow_planner.get_planning_suggestions("file operations")

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0


class TestNetworkContextBuilder:
    """Test NetworkContextBuilder functionality."""

    @pytest.fixture
    def mock_services(self):
        """Mock services for context builder."""
        p2p_service = Mock()
        p2p_service.get_all_agent_cards = AsyncMock(return_value={})

        mcp_registry = Mock()
        mcp_registry.discover_all_tools = AsyncMock(return_value={})

        return p2p_service, mcp_registry

    @pytest.fixture
    def context_builder(self, mock_services):
        """Create NetworkContextBuilder instance."""
        p2p_service, mcp_registry = mock_services
        return NetworkContextBuilder(p2p_service, mcp_registry)

    @pytest.mark.asyncio
    async def test_build_network_context(self, context_builder):
        """Test building network context."""
        context = await context_builder.build_network_context()

        assert isinstance(context, NetworkContext)
        assert isinstance(context.available_agents, list)
        assert isinstance(context.available_tools, list)
        assert isinstance(context.agent_capabilities, dict)
        assert isinstance(context.tool_routing, dict)

    @pytest.mark.asyncio
    async def test_get_network_health(self, context_builder):
        """Test network health calculation."""
        health = await context_builder.get_network_health()

        assert "status" in health
        assert isinstance(health.get("overall_health", 0), (int, float))


class TestWorkflowPlanOptimizer:
    """Test WorkflowPlanOptimizer functionality."""

    @pytest.fixture
    def mock_context_builder(self):
        """Mock context builder."""
        builder = Mock()
        builder.build_network_context = AsyncMock(
            return_value=NetworkContext(
                available_agents=[],
                available_tools=[{"name": "test_tool", "success_rate": 0.9}],
                network_load="low",
                agent_capabilities={},
                tool_routing={},
            )
        )
        return builder

    @pytest.fixture
    def optimizer(self, mock_context_builder):
        """Create WorkflowPlanOptimizer instance."""
        return WorkflowPlanOptimizer(mock_context_builder)

    @pytest.fixture
    def sample_workflow_plan(self):
        """Create sample workflow plan."""
        return WorkflowPlan(
            id="test-plan",
            description="Test workflow",
            dsl="test_tool arg1 arg2\nother_tool arg3",
            agents_used=["agent1"],
            estimated_time=5,
            confidence=0.8,
            metadata={},
            created_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_validate_workflow_plan(self, optimizer, sample_workflow_plan):
        """Test workflow plan validation."""
        issues = await optimizer.validate_workflow_plan(sample_workflow_plan)

        assert isinstance(issues, list)
        # May have validation issues due to missing tools, which is expected

    @pytest.mark.asyncio
    async def test_optimize_workflow_plan(self, optimizer, sample_workflow_plan):
        """Test workflow plan optimization."""
        result = await optimizer.optimize_workflow_plan(
            sample_workflow_plan, OptimizationGoal.PERFORMANCE
        )

        assert result.original_dsl == sample_workflow_plan.dsl
        assert isinstance(result.improvements, list)
        assert isinstance(result.estimated_speedup, (int, float))
        assert isinstance(result.reliability_score, (int, float))

    @pytest.mark.asyncio
    async def test_create_execution_plan(self, optimizer, sample_workflow_plan):
        """Test execution plan creation."""
        plan = await optimizer.create_execution_plan(sample_workflow_plan)

        assert plan.workflow_id == sample_workflow_plan.id
        assert isinstance(plan.steps, list)
        assert isinstance(plan.agent_assignments, dict)
        assert isinstance(plan.estimated_duration, (int, float))


class TestPromptGeneration:
    """Test prompt generation functionality."""

    def test_get_workflow_generation_prompt(self):
        """Test workflow generation prompt formatting."""
        user_request = "Test request"
        available_agents = [{"id": "agent1", "capabilities": ["tool1"]}]
        available_tools = [{"name": "tool1", "description": "Test tool"}]

        prompt = get_workflow_generation_prompt(
            user_request=user_request,
            available_agents=available_agents,
            available_tools=available_tools,
        )

        assert "system_prompt" in prompt
        assert "user_prompt" in prompt
        assert user_request in prompt["user_prompt"]
        assert "agent1" in prompt["system_prompt"]
        assert "tool1" in prompt["system_prompt"]


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @pytest.fixture
    def full_setup(self):
        """Create full setup with all components."""
        p2p_service = Mock()
        p2p_service.get_all_agent_cards = AsyncMock(
            return_value={
                "filesystem-agent": {
                    "id": "filesystem-agent",
                    "capabilities": {
                        "file_read": {"description": "Read files"},
                        "file_write": {"description": "Write files"},
                    },
                    "load": {"current": 0.3, "max": 1.0},
                    "location": "local",
                    "metadata": {},
                }
            }
        )

        mcp_registry = Mock()
        mcp_registry.discover_all_tools = AsyncMock(
            return_value={
                "filesystem": [
                    {"name": "file_read", "description": "Read files"},
                    {"name": "file_write", "description": "Write files"},
                ]
            }
        )

        planner = WorkflowPlanner(
            p2p_service=p2p_service,
            mcp_registry=mcp_registry,
            openai_api_key=None,  # Use fallback mode
        )

        return planner

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_planning(self, full_setup):
        """Test complete workflow planning flow."""
        planner = full_setup
        await planner.initialize()

        # Generate workflow
        result = await planner.generate_from_natural_language(
            "backup important files", optimization_goals=[OptimizationGoal.BALANCE]
        )

        assert result.success is True
        assert result.workflow_plan is not None
        assert result.execution_plan is not None
        assert result.fallback_used is True  # No OpenAI key provided

        # Check workflow plan structure
        workflow = result.workflow_plan
        assert workflow.id.startswith("fallback_")
        assert len(workflow.dsl) > 0
        assert workflow.confidence > 0

        # Check execution plan structure
        exec_plan = result.execution_plan
        assert len(exec_plan.steps) > 0
        assert exec_plan.estimated_duration > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

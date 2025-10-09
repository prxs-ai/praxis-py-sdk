"""LLM (Large Language Model) integration module for Praxis SDK.

This module provides:
- Natural language to workflow conversion
- Intelligent agent selection and routing
- Workflow plan optimization and validation
- Integration with DSL execution engine
"""

from .client import LLMClient
from .context_builder import AgentInfo, NetworkContextBuilder, ToolInfo
from .openai_client import NetworkContext, WorkflowPlan, WorkflowPlannerClient
from .plan_optimizer import (
    ExecutionPlan,
    OptimizationGoal,
    ValidationSeverity,
    WorkflowPlanOptimizer,
)
from .prompts import (
    ErrorRecoveryPrompts,
    WorkflowPrompts,
    get_workflow_generation_prompt,
)
from .workflow_planner import PlanningRequest, PlanningResult, WorkflowPlanner

__all__ = [
    # Core client
    "LLMClient",
    # Workflow planning
    "WorkflowPlanner",
    "PlanningRequest",
    "PlanningResult",
    # OpenAI integration
    "WorkflowPlannerClient",
    "WorkflowPlan",
    "NetworkContext",
    # Context building
    "NetworkContextBuilder",
    "AgentInfo",
    "ToolInfo",
    # Plan optimization
    "WorkflowPlanOptimizer",
    "OptimizationGoal",
    "ExecutionPlan",
    "ValidationSeverity",
    # Prompts
    "WorkflowPrompts",
    "ErrorRecoveryPrompts",
    "get_workflow_generation_prompt",
]

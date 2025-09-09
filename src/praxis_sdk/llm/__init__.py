"""
LLM (Large Language Model) integration module for Praxis SDK.

This module provides:
- Natural language to workflow conversion
- Intelligent agent selection and routing
- Workflow plan optimization and validation
- Integration with DSL execution engine
"""

from .client import LLMClient
from .workflow_planner import WorkflowPlanner, PlanningRequest, PlanningResult
from .openai_client import WorkflowPlannerClient, WorkflowPlan, NetworkContext
from .context_builder import NetworkContextBuilder, AgentInfo, ToolInfo
from .plan_optimizer import WorkflowPlanOptimizer, OptimizationGoal, ExecutionPlan, ValidationSeverity
from .prompts import WorkflowPrompts, ErrorRecoveryPrompts, get_workflow_generation_prompt

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
    "get_workflow_generation_prompt"
]
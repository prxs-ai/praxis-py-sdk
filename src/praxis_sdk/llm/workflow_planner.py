"""
Main workflow planner - intelligent workflow generation from natural language.

This is the central module that orchestrates:
- Natural language understanding and intent extraction
- Network context building and agent discovery
- LLM-powered workflow plan generation
- Plan optimization and validation
- Integration with DSL execution engine
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from loguru import logger

from ..config import LLMConfig
from ..dsl.orchestrator import DSLOrchestrator
from ..p2p.service import P2PService
from ..mcp.registry import ToolRegistry
from .openai_client import WorkflowPlannerClient, WorkflowPlan, NetworkContext
from .context_builder import NetworkContextBuilder
from .plan_optimizer import WorkflowPlanOptimizer, OptimizationGoal, ExecutionPlan, ValidationSeverity
from .prompts import get_workflow_generation_prompt


@dataclass
class PlanningRequest:
    """Request for workflow planning."""
    
    user_request: str
    user_id: Optional[str] = None
    priority: str = "medium"
    context: Optional[Dict[str, Any]] = None
    optimization_goals: List[OptimizationGoal] = None
    constraints: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.optimization_goals is None:
            self.optimization_goals = [OptimizationGoal.BALANCE]


@dataclass
class PlanningResult:
    """Result of workflow planning."""
    
    request_id: str
    success: bool
    workflow_plan: Optional[WorkflowPlan]
    execution_plan: Optional[ExecutionPlan]
    validation_issues: List[Any]
    optimization_applied: bool
    processing_time: float
    error_message: Optional[str] = None
    fallback_used: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        
        # Handle datetime serialization
        if self.workflow_plan:
            result["workflow_plan"]["created_at"] = self.workflow_plan.created_at.isoformat()
        
        return result


class WorkflowPlanner:
    """
    Main workflow planner that converts natural language to executable workflows.
    
    This class provides:
    - Natural language understanding and workflow generation
    - Intelligent agent selection and load balancing
    - Plan optimization for performance and reliability
    - Integration with existing DSL execution engine
    - Error recovery and fallback strategies
    """
    
    def __init__(
        self,
        p2p_service: P2PService,
        mcp_registry: ToolRegistry,
        dsl_orchestrator: Optional[DSLOrchestrator] = None,
        openai_api_key: Optional[str] = None
    ):
        self.p2p_service = p2p_service
        self.mcp_registry = mcp_registry
        self.dsl_orchestrator = dsl_orchestrator
        
        # Initialize LLM client
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key provided - LLM planning will be limited")
        
        self.llm_client = WorkflowPlannerClient(
            api_key=api_key or "dummy",
            model="gpt-4",
            temperature=0.1
        ) if api_key else None
        
        # Initialize supporting components
        self.context_builder = NetworkContextBuilder(p2p_service, mcp_registry)
        self.plan_optimizer = WorkflowPlanOptimizer(self.context_builder)
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_plans": 0,
            "failed_plans": 0,
            "llm_used": 0,
            "fallback_used": 0,
            "average_processing_time": 0.0
        }
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize the workflow planner."""
        if self._initialized:
            return
        
        try:
            # Initialize LLM client if available
            if self.llm_client:
                await self.llm_client.initialize()
            
            self._initialized = True
            logger.success("Workflow planner initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow planner: {e}")
            # Continue without LLM - fallback modes will be used
            self._initialized = True
    
    async def generate_from_natural_language(
        self,
        user_request: str,
        user_id: Optional[str] = None,
        optimization_goals: Optional[List[OptimizationGoal]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> PlanningResult:
        """
        Generate workflow plan from natural language description.
        
        Args:
            user_request: User's natural language request
            user_id: Optional user identifier for tracking
            optimization_goals: Optional optimization objectives
            constraints: Optional planning constraints
            
        Returns:
            PlanningResult with generated workflow and execution plan
        """
        
        if not self._initialized:
            await self.initialize()
        
        request_id = f"req_{int(datetime.now().timestamp())}"
        start_time = datetime.now()
        
        logger.info(f"Processing planning request {request_id}: {user_request[:100]}...")
        
        try:
            # Create planning request
            planning_request = PlanningRequest(
                user_request=user_request,
                user_id=user_id,
                optimization_goals=optimization_goals or [OptimizationGoal.BALANCE],
                constraints=constraints
            )
            
            # Build network context
            logger.debug("Building network context...")
            network_context = await self.context_builder.build_network_context()
            
            # Generate workflow plan
            workflow_plan = None
            fallback_used = False
            
            if self.llm_client and network_context.available_tools:
                try:
                    logger.debug("Generating workflow plan using LLM...")
                    workflow_plan = await self._generate_with_llm(user_request, network_context)
                    self.stats["llm_used"] += 1
                    
                except Exception as e:
                    logger.warning(f"LLM generation failed: {e}, falling back to rule-based approach")
                    workflow_plan = await self._generate_with_fallback(user_request, network_context)
                    fallback_used = True
                    self.stats["fallback_used"] += 1
            
            else:
                logger.debug("Using fallback workflow generation...")
                workflow_plan = await self._generate_with_fallback(user_request, network_context)
                fallback_used = True
                self.stats["fallback_used"] += 1
            
            if not workflow_plan:
                raise ValueError("Failed to generate workflow plan with all methods")
            
            # Validate the plan
            logger.debug("Validating workflow plan...")
            validation_issues = await self.plan_optimizer.validate_workflow_plan(
                workflow_plan, network_context
            )
            
            # Check for critical errors
            critical_errors = [issue for issue in validation_issues if issue.severity == ValidationSeverity.ERROR]
            if critical_errors:
                error_msg = f"Workflow plan has critical errors: {', '.join(err.message for err in critical_errors[:3])}"
                raise ValueError(error_msg)
            
            # Optimize the plan
            optimization_applied = False
            if planning_request.optimization_goals and OptimizationGoal.BALANCE in planning_request.optimization_goals:
                logger.debug("Optimizing workflow plan...")
                try:
                    optimization_result = await self.plan_optimizer.optimize_workflow_plan(
                        workflow_plan,
                        goal=OptimizationGoal.BALANCE,
                        constraints=constraints
                    )
                    
                    # Update workflow plan with optimized version if significantly better
                    if optimization_result.estimated_speedup > 1.1:  # At least 10% improvement
                        workflow_plan.dsl = optimization_result.optimized_dsl
                        workflow_plan.metadata["optimization"] = {
                            "applied": True,
                            "improvements": optimization_result.improvements,
                            "speedup": optimization_result.estimated_speedup
                        }
                        optimization_applied = True
                        logger.info(f"Applied optimization with {optimization_result.estimated_speedup:.1f}x speedup")
                
                except Exception as e:
                    logger.warning(f"Optimization failed: {e}, using original plan")
            
            # Create execution plan
            logger.debug("Creating execution plan...")
            execution_plan = await self.plan_optimizer.create_execution_plan(workflow_plan)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["total_requests"] += 1
            self.stats["successful_plans"] += 1
            self._update_average_processing_time(processing_time)
            
            result = PlanningResult(
                request_id=request_id,
                success=True,
                workflow_plan=workflow_plan,
                execution_plan=execution_plan,
                validation_issues=validation_issues,
                optimization_applied=optimization_applied,
                processing_time=processing_time,
                fallback_used=fallback_used
            )
            
            logger.success(f"Generated workflow plan {workflow_plan.id} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["total_requests"] += 1
            self.stats["failed_plans"] += 1
            self._update_average_processing_time(processing_time)
            
            logger.error(f"Failed to generate workflow plan: {e}")
            
            return PlanningResult(
                request_id=request_id,
                success=False,
                workflow_plan=None,
                execution_plan=None,
                validation_issues=[],
                optimization_applied=False,
                processing_time=processing_time,
                error_message=str(e),
                fallback_used=fallback_used
            )
    
    async def execute_workflow_plan(
        self,
        workflow_plan: WorkflowPlan,
        execution_plan: Optional[ExecutionPlan] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow plan using the DSL orchestrator.
        
        Args:
            workflow_plan: The workflow plan to execute
            execution_plan: Optional execution plan with optimizations
            
        Returns:
            Execution result
        """
        
        if not self.dsl_orchestrator:
            logger.error("No DSL orchestrator available for workflow execution")
            return {
                "success": False,
                "error": "DSL orchestrator not available",
                "workflow_id": workflow_plan.id
            }
        
        try:
            logger.info(f"Executing workflow plan {workflow_plan.id}")
            
            # Use the DSL orchestrator to execute the workflow
            # This would integrate with the existing DSL execution system
            result = await self.dsl_orchestrator.execute_workflow(workflow_plan.dsl)
            
            logger.success(f"Workflow plan {workflow_plan.id} executed successfully")
            return {
                "success": True,
                "result": result,
                "workflow_id": workflow_plan.id,
                "execution_time": result.get("execution_time", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to execute workflow plan {workflow_plan.id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_id": workflow_plan.id
            }
    
    async def get_planning_suggestions(self, partial_request: str) -> List[str]:
        """
        Get planning suggestions for partial user input.
        
        Args:
            partial_request: Partial user request
            
        Returns:
            List of suggested completions or related workflows
        """
        
        try:
            # Build network context to understand available capabilities
            network_context = await self.context_builder.build_network_context()
            
            suggestions = []
            available_tools = [tool["name"] for tool in network_context.available_tools]
            
            # Rule-based suggestions based on keywords
            keywords_to_tools = {
                "file": ["file_read", "file_write", "file_list"],
                "web": ["http_request", "web_scrape"],
                "data": ["data_process", "data_analyze"],
                "email": ["send_email", "read_email"],
                "system": ["system_info", "process_list"]
            }
            
            partial_lower = partial_request.lower()
            for keyword, tools in keywords_to_tools.items():
                if keyword in partial_lower:
                    available_keyword_tools = [tool for tool in tools if tool in available_tools]
                    if available_keyword_tools:
                        suggestions.append(f"You can use {', '.join(available_keyword_tools)} for {keyword} operations")
            
            # Add general suggestions
            if "analyze" in partial_lower or "report" in partial_lower:
                suggestions.append("Generate analysis report from data")
            
            if "backup" in partial_lower:
                suggestions.append("Create backup of important files")
            
            if "monitor" in partial_lower:
                suggestions.append("Monitor system resources and send alerts")
            
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.error(f"Failed to get planning suggestions: {e}")
            return ["Try describing your task in simple terms"]
    
    async def _generate_with_llm(self, user_request: str, network_context: NetworkContext) -> WorkflowPlan:
        """Generate workflow plan using LLM."""
        if not self.llm_client:
            raise ValueError("LLM client not available")
        
        return await self.llm_client.generate_workflow_from_natural_language(
            user_request=user_request,
            network_context=network_context
        )
    
    async def _generate_with_fallback(self, user_request: str, network_context: NetworkContext) -> WorkflowPlan:
        """Generate workflow plan using rule-based fallback."""
        
        # Simple rule-based workflow generation
        plan_id = f"fallback_{int(datetime.now().timestamp())}"
        
        # Analyze request for keywords
        request_lower = user_request.lower()
        dsl_commands = []
        
        # File operations
        if any(word in request_lower for word in ["file", "read", "write", "copy"]):
            if "read" in request_lower:
                dsl_commands.append("file_read input.txt")
            if "write" in request_lower or "save" in request_lower:
                dsl_commands.append("file_write output.txt")
        
        # Web operations
        elif any(word in request_lower for word in ["web", "http", "api", "download"]):
            dsl_commands.append("http_request https://api.example.com/data")
            if "analyze" in request_lower:
                dsl_commands.append("data_analyze")
        
        # System operations
        elif any(word in request_lower for word in ["system", "process", "monitor"]):
            dsl_commands.append("system_info")
            if "alert" in request_lower or "notify" in request_lower:
                dsl_commands.append("send_notification 'System status update'")
        
        # Default operation
        if not dsl_commands:
            # Find the first available tool
            if network_context.available_tools:
                first_tool = network_context.available_tools[0]["name"]
                dsl_commands.append(f"{first_tool} # Generated from: {user_request}")
            else:
                dsl_commands.append(f"echo 'Processing: {user_request}'")
        
        dsl = "\n".join(dsl_commands)
        
        return WorkflowPlan(
            id=plan_id,
            description=f"Rule-based workflow for: {user_request}",
            dsl=dsl,
            agents_used=[],
            estimated_time=len(dsl_commands) * 2,  # 2 minutes per command
            confidence=0.6,  # Lower confidence for rule-based
            metadata={
                "generation_method": "rule_based_fallback",
                "user_request": user_request,
                "commands_generated": len(dsl_commands)
            },
            created_at=datetime.now()
        )
    
    def _update_average_processing_time(self, processing_time: float):
        """Update average processing time statistic."""
        total_requests = self.stats["total_requests"]
        current_avg = self.stats["average_processing_time"]
        
        # Calculate new average
        new_avg = ((current_avg * (total_requests - 1)) + processing_time) / total_requests
        self.stats["average_processing_time"] = new_avg
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Get current network status for planning."""
        try:
            health = await self.context_builder.get_network_health()
            context = await self.context_builder.build_network_context()
            
            return {
                "health": health,
                "agents": len(context.available_agents),
                "tools": len(context.available_tools),
                "network_load": context.network_load,
                "planner_stats": self.stats,
                "llm_available": self.llm_client is not None and self.llm_client._initialized
            }
            
        except Exception as e:
            logger.error(f"Failed to get network status: {e}")
            return {
                "error": str(e),
                "planner_stats": self.stats,
                "llm_available": False
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get planning statistics."""
        total = self.stats["total_requests"]
        
        return {
            **self.stats,
            "success_rate": (self.stats["successful_plans"] / max(total, 1)),
            "llm_usage_rate": (self.stats["llm_used"] / max(total, 1)),
            "fallback_rate": (self.stats["fallback_used"] / max(total, 1)),
            "initialized": self._initialized
        }
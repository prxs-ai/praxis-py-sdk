"""
Plan optimizer for workflow validation, optimization and execution planning.

This module provides:
- DSL syntax validation and error detection
- Workflow plan optimization for performance and reliability
- Resource allocation and load balancing recommendations
- Execution timeline estimation and bottleneck analysis
"""

import re
import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from loguru import logger

from .openai_client import WorkflowPlan, NetworkContext
from .context_builder import NetworkContextBuilder, AgentInfo, ToolInfo


class OptimizationGoal(Enum):
    """Workflow optimization goals."""
    PERFORMANCE = "performance"
    RELIABILITY = "reliability" 
    COST = "cost"
    BALANCE = "balance"


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning" 
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue in a workflow plan."""
    
    severity: ValidationSeverity
    message: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    rule_id: str = ""


@dataclass
class OptimizationResult:
    """Results from workflow plan optimization."""
    
    original_dsl: str
    optimized_dsl: str
    improvements: List[str]
    estimated_speedup: float
    reliability_score: float
    resource_requirements: Dict[str, Any]
    execution_timeline: Dict[str, float]
    bottlenecks: List[str]
    warnings: List[ValidationIssue]


@dataclass
class ExecutionPlan:
    """Detailed execution plan for a workflow."""
    
    workflow_id: str
    steps: List[Dict[str, Any]]
    agent_assignments: Dict[str, str]  # step_id -> agent_id
    resource_reservations: Dict[str, Dict[str, Any]]
    estimated_duration: float
    critical_path: List[str]
    dependencies: Dict[str, List[str]]
    checkpoints: List[str]


class WorkflowPlanOptimizer:
    """
    Optimizes workflow plans for better performance, reliability and resource utilization.
    
    This class provides:
    - DSL syntax validation
    - Performance optimization
    - Resource allocation optimization
    - Execution planning
    """
    
    def __init__(self, context_builder: NetworkContextBuilder):
        self.context_builder = context_builder
        
        # DSL syntax patterns
        self.dsl_patterns = {
            "command": r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*(.*?)(?:\s*#.*)?$',
            "quoted_string": r'"([^"\\]*(\\.[^"\\]*)*)"',
            "argument": r'([^\s"]+|"[^"\\]*(\\.[^"\\]*)*")',
            "comment": r'^\s*#.*$',
            "empty_line": r'^\s*$'
        }
        
        # Performance heuristics
        self.tool_performance = {
            "file_read": {"avg_time": 0.5, "memory": "low"},
            "file_write": {"avg_time": 1.0, "memory": "low"},
            "http_request": {"avg_time": 2.0, "memory": "medium"},
            "data_processing": {"avg_time": 5.0, "memory": "high"},
            "ml_inference": {"avg_time": 10.0, "memory": "very_high"}
        }
    
    async def validate_workflow_plan(
        self,
        workflow_plan: WorkflowPlan,
        network_context: Optional[NetworkContext] = None
    ) -> List[ValidationIssue]:
        """
        Validate a workflow plan for syntax and feasibility.
        
        Args:
            workflow_plan: The workflow plan to validate
            network_context: Current network state for feasibility checks
            
        Returns:
            List of validation issues found
        """
        
        issues = []
        
        try:
            # Get network context if not provided
            if network_context is None:
                network_context = await self.context_builder.build_network_context()
            
            # Validate DSL syntax
            syntax_issues = self._validate_dsl_syntax(workflow_plan.dsl)
            issues.extend(syntax_issues)
            
            # Validate tool availability
            availability_issues = self._validate_tool_availability(workflow_plan.dsl, network_context)
            issues.extend(availability_issues)
            
            # Validate agent assignments
            if workflow_plan.agents_used:
                agent_issues = self._validate_agent_assignments(workflow_plan.agents_used, network_context)
                issues.extend(agent_issues)
            
            # Validate resource requirements
            resource_issues = self._validate_resource_requirements(workflow_plan.dsl, network_context)
            issues.extend(resource_issues)
            
            # Performance warnings
            performance_issues = self._check_performance_concerns(workflow_plan.dsl)
            issues.extend(performance_issues)
            
            logger.debug(f"Validated workflow plan {workflow_plan.id}: {len(issues)} issues found")
            
            return issues
            
        except Exception as e:
            logger.error(f"Failed to validate workflow plan: {e}")
            return [ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Validation failed: {str(e)}",
                rule_id="validation_error"
            )]
    
    async def optimize_workflow_plan(
        self,
        workflow_plan: WorkflowPlan,
        goal: OptimizationGoal = OptimizationGoal.BALANCE,
        constraints: Optional[Dict[str, Any]] = None
    ) -> OptimizationResult:
        """
        Optimize a workflow plan based on specified goals and constraints.
        
        Args:
            workflow_plan: The workflow plan to optimize
            goal: Optimization objective
            constraints: Optimization constraints
            
        Returns:
            OptimizationResult with improved plan and analysis
        """
        
        try:
            logger.info(f"Optimizing workflow plan {workflow_plan.id} for {goal.value}")
            
            # Set default constraints
            if constraints is None:
                constraints = {
                    "max_execution_time": 300,  # 5 minutes
                    "max_agents": 5,
                    "prefer_local": True,
                    "error_tolerance": "medium"
                }
            
            # Get network context
            network_context = await self.context_builder.build_network_context()
            
            # Parse current DSL
            commands = self._parse_dsl(workflow_plan.dsl)
            
            # Apply optimizations based on goal
            optimized_commands = []
            improvements = []
            
            if goal in [OptimizationGoal.PERFORMANCE, OptimizationGoal.BALANCE]:
                optimized_commands, perf_improvements = self._optimize_for_performance(
                    commands, network_context, constraints
                )
                improvements.extend(perf_improvements)
            
            if goal in [OptimizationGoal.RELIABILITY, OptimizationGoal.BALANCE]:
                optimized_commands, rel_improvements = self._optimize_for_reliability(
                    optimized_commands or commands, network_context, constraints
                )
                improvements.extend(rel_improvements)
            
            if goal in [OptimizationGoal.COST, OptimizationGoal.BALANCE]:
                optimized_commands, cost_improvements = self._optimize_for_cost(
                    optimized_commands or commands, network_context, constraints
                )
                improvements.extend(cost_improvements)
            
            # Use original if no optimizations were applied
            if not optimized_commands:
                optimized_commands = commands
            
            # Build optimized DSL
            optimized_dsl = self._build_dsl_from_commands(optimized_commands)
            
            # Calculate metrics
            execution_timeline = self._estimate_execution_timeline(optimized_commands)
            estimated_speedup = self._calculate_speedup(commands, optimized_commands)
            reliability_score = self._calculate_reliability_score(optimized_commands, network_context)
            resource_requirements = self._calculate_resource_requirements(optimized_commands)
            bottlenecks = self._identify_bottlenecks(optimized_commands, execution_timeline)
            
            # Validate optimized plan
            warnings = await self.validate_workflow_plan(
                WorkflowPlan(
                    id=f"{workflow_plan.id}_optimized",
                    description=workflow_plan.description,
                    dsl=optimized_dsl,
                    agents_used=workflow_plan.agents_used,
                    estimated_time=int(execution_timeline.get("total", workflow_plan.estimated_time)),
                    confidence=workflow_plan.confidence,
                    metadata=workflow_plan.metadata,
                    created_at=workflow_plan.created_at
                ),
                network_context
            )
            
            result = OptimizationResult(
                original_dsl=workflow_plan.dsl,
                optimized_dsl=optimized_dsl,
                improvements=improvements,
                estimated_speedup=estimated_speedup,
                reliability_score=reliability_score,
                resource_requirements=resource_requirements,
                execution_timeline=execution_timeline,
                bottlenecks=bottlenecks,
                warnings=[w for w in warnings if w.severity != ValidationSeverity.ERROR]
            )
            
            logger.success(f"Optimized workflow plan with {len(improvements)} improvements")
            return result
            
        except Exception as e:
            logger.error(f"Failed to optimize workflow plan: {e}")
            # Return minimal result with original plan
            return OptimizationResult(
                original_dsl=workflow_plan.dsl,
                optimized_dsl=workflow_plan.dsl,
                improvements=[],
                estimated_speedup=1.0,
                reliability_score=0.5,
                resource_requirements={},
                execution_timeline={"total": workflow_plan.estimated_time * 60},
                bottlenecks=[],
                warnings=[ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Optimization failed: {str(e)}",
                    rule_id="optimization_error"
                )]
            )
    
    async def create_execution_plan(
        self,
        workflow_plan: WorkflowPlan,
        optimization_result: Optional[OptimizationResult] = None
    ) -> ExecutionPlan:
        """
        Create detailed execution plan for a workflow.
        
        Args:
            workflow_plan: The workflow plan to execute
            optimization_result: Optional optimization results to use
            
        Returns:
            ExecutionPlan with detailed execution strategy
        """
        
        try:
            # Use optimized DSL if available
            dsl = optimization_result.optimized_dsl if optimization_result else workflow_plan.dsl
            commands = self._parse_dsl(dsl)
            
            # Get network context
            network_context = await self.context_builder.build_network_context()
            
            # Create execution steps
            steps = []
            agent_assignments = {}
            resource_reservations = {}
            dependencies = {}
            
            for i, command in enumerate(commands):
                step_id = f"step_{i+1}"
                tool_name = command["tool"]
                
                # Find best agent for this step
                agent_recommendations = await self.context_builder.get_agent_recommendations(
                    tool_name=tool_name,
                    requirements={"max_load": 80}
                )
                
                selected_agent = agent_recommendations[0]["id"] if agent_recommendations else "default"
                
                # Create step
                step = {
                    "id": step_id,
                    "tool": tool_name,
                    "arguments": command["args"],
                    "estimated_duration": self._estimate_step_duration(tool_name),
                    "resource_requirements": self._get_tool_resources(tool_name),
                    "retry_policy": {"max_attempts": 3, "backoff": "exponential"}
                }
                
                steps.append(step)
                agent_assignments[step_id] = selected_agent
                
                # Reserve resources
                if selected_agent not in resource_reservations:
                    resource_reservations[selected_agent] = {"cpu": 0, "memory": 0, "network": 0}
                
                tool_resources = self._get_tool_resources(tool_name)
                for resource, amount in tool_resources.items():
                    resource_reservations[selected_agent][resource] += amount
                
                # Track dependencies (simple sequential for now)
                if i > 0:
                    dependencies[step_id] = [f"step_{i}"]
            
            # Calculate critical path
            critical_path = [step["id"] for step in steps]
            
            # Determine checkpoints (every 3 steps or before long operations)
            checkpoints = []
            for i, step in enumerate(steps):
                if (i + 1) % 3 == 0 or step["estimated_duration"] > 30:
                    checkpoints.append(step["id"])
            
            # Calculate total duration
            total_duration = sum(step["estimated_duration"] for step in steps)
            
            plan = ExecutionPlan(
                workflow_id=workflow_plan.id,
                steps=steps,
                agent_assignments=agent_assignments,
                resource_reservations=resource_reservations,
                estimated_duration=total_duration,
                critical_path=critical_path,
                dependencies=dependencies,
                checkpoints=checkpoints
            )
            
            logger.success(f"Created execution plan for {workflow_plan.id}: {len(steps)} steps, {total_duration:.1f}s estimated")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create execution plan: {e}")
            # Return minimal fallback plan
            return ExecutionPlan(
                workflow_id=workflow_plan.id,
                steps=[],
                agent_assignments={},
                resource_reservations={},
                estimated_duration=workflow_plan.estimated_time * 60,
                critical_path=[],
                dependencies={},
                checkpoints=[]
            )
    
    def _validate_dsl_syntax(self, dsl: str) -> List[ValidationIssue]:
        """Validate DSL syntax."""
        issues = []
        lines = dsl.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if re.match(self.dsl_patterns["empty_line"], line) or re.match(self.dsl_patterns["comment"], line):
                continue
            
            # Validate command syntax
            command_match = re.match(self.dsl_patterns["command"], line)
            if not command_match:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid command syntax",
                    line_number=line_num,
                    suggestion="Commands should be in format: tool_name arg1 arg2 ...",
                    rule_id="syntax_error"
                ))
                continue
            
            tool_name, args_str = command_match.groups()
            
            # Validate tool name
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', tool_name):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid tool name: {tool_name}",
                    line_number=line_num,
                    suggestion="Tool names should contain only letters, numbers and underscores",
                    rule_id="invalid_tool_name"
                ))
            
            # Validate quoted strings
            if '"' in args_str:
                try:
                    # Check for unmatched quotes
                    in_quotes = False
                    escaped = False
                    for char in args_str:
                        if char == '\\' and not escaped:
                            escaped = True
                            continue
                        elif char == '"' and not escaped:
                            in_quotes = not in_quotes
                        escaped = False
                    
                    if in_quotes:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            message="Unmatched quote in arguments",
                            line_number=line_num,
                            suggestion="Ensure all quotes are properly closed",
                            rule_id="unmatched_quote"
                        ))
                
                except Exception:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="Complex quote structure detected",
                        line_number=line_num,
                        rule_id="complex_quotes"
                    ))
        
        return issues
    
    def _validate_tool_availability(self, dsl: str, network_context: NetworkContext) -> List[ValidationIssue]:
        """Validate that all tools in the DSL are available."""
        issues = []
        available_tools = {tool["name"] for tool in network_context.available_tools}
        
        commands = self._parse_dsl(dsl)
        for i, command in enumerate(commands):
            tool_name = command["tool"]
            
            if tool_name not in available_tools:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Tool '{tool_name}' is not available in the network",
                    line_number=i + 1,
                    suggestion=f"Available tools: {', '.join(list(available_tools)[:5])}{'...' if len(available_tools) > 5 else ''}",
                    rule_id="tool_not_available"
                ))
        
        return issues
    
    def _validate_agent_assignments(self, agents_used: List[str], network_context: NetworkContext) -> List[ValidationIssue]:
        """Validate agent assignments."""
        issues = []
        available_agents = {agent["id"] for agent in network_context.available_agents}
        
        for agent_id in agents_used:
            if agent_id not in available_agents:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Agent '{agent_id}' is not currently available",
                    suggestion="Agent assignment will be re-evaluated at execution time",
                    rule_id="agent_not_available"
                ))
        
        return issues
    
    def _validate_resource_requirements(self, dsl: str, network_context: NetworkContext) -> List[ValidationIssue]:
        """Validate resource requirements against available capacity."""
        issues = []
        
        # Calculate total resource requirements
        commands = self._parse_dsl(dsl)
        total_memory = sum(self._get_tool_resources(cmd["tool"]).get("memory", 100) for cmd in commands)
        
        # Simple validation - in reality this would be more sophisticated
        if total_memory > 1000:  # MB
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"High memory requirements detected: {total_memory}MB",
                suggestion="Consider optimizing for memory usage or using streaming operations",
                rule_id="high_memory_usage"
            ))
        
        return issues
    
    def _check_performance_concerns(self, dsl: str) -> List[ValidationIssue]:
        """Check for potential performance issues."""
        issues = []
        commands = self._parse_dsl(dsl)
        
        # Check for potentially slow operations
        slow_ops = 0
        for command in commands:
            tool_perf = self.tool_performance.get(command["tool"], {"avg_time": 1.0})
            if tool_perf["avg_time"] > 5.0:
                slow_ops += 1
        
        if slow_ops > 3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                message=f"Workflow contains {slow_ops} potentially slow operations",
                suggestion="Consider parallelization or caching strategies",
                rule_id="slow_operations"
            ))
        
        return issues
    
    def _optimize_for_performance(
        self,
        commands: List[Dict[str, Any]],
        network_context: NetworkContext,
        constraints: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Optimize commands for performance."""
        optimized_commands = commands.copy()
        improvements = []
        
        # Example optimization: combine file operations
        file_ops = []
        other_ops = []
        
        for cmd in commands:
            if cmd["tool"].startswith("file_"):
                file_ops.append(cmd)
            else:
                other_ops.append(cmd)
        
        if len(file_ops) > 2:
            # Could batch file operations
            improvements.append("Batched multiple file operations for better I/O performance")
        
        # Keep original order for now (more sophisticated optimizations would reorder)
        return optimized_commands, improvements
    
    def _optimize_for_reliability(
        self,
        commands: List[Dict[str, Any]],
        network_context: NetworkContext,
        constraints: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Optimize commands for reliability."""
        optimized_commands = []
        improvements = []
        
        for cmd in commands:
            optimized_cmd = cmd.copy()
            
            # Add retry logic for network operations
            if cmd["tool"] in ["http_request", "api_call"]:
                optimized_cmd["retry_policy"] = {"max_attempts": 3, "backoff": "exponential"}
                improvements.append(f"Added retry policy for {cmd['tool']}")
            
            # Add validation for file operations
            if cmd["tool"].startswith("file_"):
                optimized_cmd["validation"] = {"check_exists": True, "verify_permissions": True}
                improvements.append(f"Added validation for {cmd['tool']}")
            
            optimized_commands.append(optimized_cmd)
        
        return optimized_commands, improvements
    
    def _optimize_for_cost(
        self,
        commands: List[Dict[str, Any]],
        network_context: NetworkContext,
        constraints: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Optimize commands for cost efficiency."""
        optimized_commands = commands.copy()
        improvements = []
        
        # Example: prefer local agents to reduce network costs
        if constraints.get("prefer_local", True):
            improvements.append("Optimized agent selection to prefer local execution")
        
        return optimized_commands, improvements
    
    def _parse_dsl(self, dsl: str) -> List[Dict[str, Any]]:
        """Parse DSL into command structure."""
        commands = []
        lines = dsl.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse command
            match = re.match(self.dsl_patterns["command"], line)
            if match:
                tool_name, args_str = match.groups()
                
                # Parse arguments (simplified)
                args = []
                if args_str:
                    args = re.findall(self.dsl_patterns["argument"], args_str.strip())
                
                commands.append({
                    "tool": tool_name,
                    "args": args,
                    "raw_line": line
                })
        
        return commands
    
    def _build_dsl_from_commands(self, commands: List[Dict[str, Any]]) -> str:
        """Build DSL string from command structure."""
        lines = []
        
        for cmd in commands:
            if "raw_line" in cmd:
                lines.append(cmd["raw_line"])
            else:
                # Reconstruct line
                args_str = " ".join(cmd["args"])
                lines.append(f"{cmd['tool']} {args_str}".strip())
        
        return "\n".join(lines)
    
    def _estimate_execution_timeline(self, commands: List[Dict[str, Any]]) -> Dict[str, float]:
        """Estimate execution timeline for commands."""
        total_time = 0
        step_times = {}
        
        for i, cmd in enumerate(commands):
            tool_perf = self.tool_performance.get(cmd["tool"], {"avg_time": 1.0})
            step_time = tool_perf["avg_time"]
            
            step_times[f"step_{i+1}"] = step_time
            total_time += step_time
        
        step_times["total"] = total_time
        return step_times
    
    def _calculate_speedup(self, original_commands: List[Dict[str, Any]], optimized_commands: List[Dict[str, Any]]) -> float:
        """Calculate estimated speedup from optimization."""
        original_time = sum(self.tool_performance.get(cmd["tool"], {"avg_time": 1.0})["avg_time"] for cmd in original_commands)
        optimized_time = sum(self.tool_performance.get(cmd["tool"], {"avg_time": 1.0})["avg_time"] for cmd in optimized_commands)
        
        if optimized_time == 0:
            return 1.0
        
        return original_time / optimized_time
    
    def _calculate_reliability_score(self, commands: List[Dict[str, Any]], network_context: NetworkContext) -> float:
        """Calculate reliability score for the workflow."""
        # Simplified calculation based on tool success rates
        tool_success_rates = {tool["name"]: tool.get("success_rate", 0.9) for tool in network_context.available_tools}
        
        total_reliability = 1.0
        for cmd in commands:
            tool_reliability = tool_success_rates.get(cmd["tool"], 0.8)
            total_reliability *= tool_reliability
        
        return total_reliability
    
    def _calculate_resource_requirements(self, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate resource requirements for the workflow."""
        requirements = {"cpu": 0, "memory": 0, "network": 0, "storage": 0}
        
        for cmd in commands:
            tool_resources = self._get_tool_resources(cmd["tool"])
            for resource, amount in tool_resources.items():
                if resource in requirements:
                    requirements[resource] += amount
        
        return requirements
    
    def _identify_bottlenecks(self, commands: List[Dict[str, Any]], timeline: Dict[str, float]) -> List[str]:
        """Identify potential bottlenecks in the workflow."""
        bottlenecks = []
        
        # Find steps that take significantly longer than average
        step_times = [v for k, v in timeline.items() if k.startswith("step_")]
        if step_times:
            avg_time = sum(step_times) / len(step_times)
            
            for i, time in enumerate(step_times):
                if time > avg_time * 2:  # More than 2x average
                    bottlenecks.append(f"Step {i+1} ({commands[i]['tool']}) takes {time:.1f}s")
        
        return bottlenecks
    
    def _get_tool_resources(self, tool_name: str) -> Dict[str, float]:
        """Get resource requirements for a tool."""
        # Default resource requirements
        base_resources = {"cpu": 10, "memory": 50, "network": 5, "storage": 0}
        
        # Tool-specific adjustments
        if tool_name.startswith("file_"):
            base_resources["storage"] = 20
        elif tool_name.startswith("http_"):
            base_resources["network"] = 50
        elif "process" in tool_name:
            base_resources["cpu"] = 50
            base_resources["memory"] = 200
        
        return base_resources
    
    def _estimate_step_duration(self, tool_name: str) -> float:
        """Estimate duration for a single step."""
        return self.tool_performance.get(tool_name, {"avg_time": 1.0})["avg_time"]
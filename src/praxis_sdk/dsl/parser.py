"""Main DSL Parser - Advanced DSL Processing Engine.
Combines tokenizer, AST builder, validator, and cache for complete DSL processing.
Go-equivalent functionality with Python enhancements.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from .ast_builder import ASTBuilder
from .cache import ToolExecutionCache
from .planner import NetworkContext, TaskPlanner, WorkflowPlan
from .tokenizer import DSLTokenizer
from .types import (
    AST,
    ASTNode,
    DSLExecutionError,
    DSLSyntaxError,
    DSLValidationError,
    ExecutionContext,
    ExecutionResult,
    NodeType,
    Token,
)
from .validator import DSLValidator, ValidationLevel


class AgentInterface:
    """Interface for agent integration matching Go SDK AgentInterface.
    Provides local and remote tool execution capabilities.
    """

    def __init__(self, agent):
        self.agent = agent

    def has_local_tool(self, tool_name: str) -> bool:
        """Check if tool is available locally."""
        if hasattr(self.agent, "has_local_tool"):
            return self.agent.has_local_tool(tool_name)
        return False

    async def execute_local_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        """Execute tool locally."""
        if hasattr(self.agent, "invoke_tool"):
            result = await self.agent.invoke_tool(tool_name, args)
            return result
        raise DSLExecutionError(f"Local tool execution not available for {tool_name}")

    async def find_agent_with_tool(self, tool_name: str) -> str | None:
        """Find agent that has the specified tool."""
        if hasattr(self.agent, "find_agent_with_tool"):
            return await self.agent.find_agent_with_tool(tool_name)
        return None

    async def execute_remote_tool(
        self, peer_id: str, tool_name: str, args: dict[str, Any]
    ) -> Any:
        """Execute tool on remote agent."""
        if hasattr(self.agent, "execute_remote_tool"):
            return await self.agent.execute_remote_tool(peer_id, tool_name, args)
        raise DSLExecutionError(
            f"Remote tool execution not available for {tool_name} on {peer_id}"
        )


class AdvancedDSLParser:
    """Advanced DSL Parser combining all DSL processing components.
    Provides Go SDK equivalent functionality with Python enhancements.

    Features:
    - Advanced tokenization with nested quotes and escaping
    - AST generation with PARALLEL, SEQUENCE, CONDITIONAL support
    - Comprehensive validation engine
    - Tool execution caching
    - Natural language workflow planning
    - Agent-aware execution
    """

    def __init__(self, agent_interface: AgentInterface | None = None):
        self.tokenizer = DSLTokenizer()
        self.ast_builder = ASTBuilder()
        self.validator = DSLValidator()
        self.cache = ToolExecutionCache()
        self.agent_interface = agent_interface
        self.planner: TaskPlanner | None = None

        # Performance tracking
        self.stats = {
            "commands_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0,
        }

        self.logger = logger
        self.logger.info("Advanced DSL Parser initialized")

    def set_planner(self, planner: TaskPlanner) -> None:
        """Set task planner for natural language processing."""
        self.planner = planner
        self.logger.debug("Task planner configured")

    async def parse_and_execute(
        self,
        dsl_content: str,
        context: ExecutionContext | None = None,
        validate: bool = True,
        use_cache: bool = True,
    ) -> ExecutionResult:
        """Parse and execute DSL content with full processing pipeline.

        Args:
            dsl_content: DSL text to process
            context: Execution context
            validate: Whether to validate before execution
            use_cache: Whether to use caching

        Returns:
            Execution result with comprehensive information

        """
        start_time = time.time()

        try:
            self.logger.debug(f"Processing DSL content: {dsl_content[:100]}...")

            # Parse DSL to AST
            ast = await self.parse(dsl_content, validate=validate)

            # Execute AST
            result = await self.execute_ast(ast, context, use_cache=use_cache)

            # Update statistics
            execution_time = time.time() - start_time
            self._update_stats(execution_time)

            result.execution_time = execution_time
            result.metadata["parser_stats"] = self.get_stats()

            self.logger.info(f"DSL processing completed in {execution_time:.3f}s")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"DSL processing failed after {execution_time:.3f}s: {e}")

            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                metadata={"error_type": type(e).__name__},
            )

    async def parse(self, dsl_content: str, validate: bool = True) -> AST:
        """Parse DSL content to AST.

        Args:
            dsl_content: DSL text to parse
            validate: Whether to validate the AST

        Returns:
            Parsed AST

        Raises:
            DSLSyntaxError: If parsing fails
            DSLValidationError: If validation fails

        """
        try:
            # Tokenize
            tokens = self.tokenizer.tokenize(dsl_content)
            self.logger.debug(f"Tokenized to {len(tokens)} tokens")

            # Validate tokens if requested
            if validate:
                token_validation = self.validator.validate_tokens(tokens)
                if not token_validation.is_valid:
                    errors = token_validation.get_errors()
                    raise DSLValidationError(f"Token validation failed: {errors}")

            # Build AST
            ast = self.ast_builder.build_ast(tokens)
            self.logger.debug(f"Built AST with {len(ast.nodes)} nodes")

            # Validate AST if requested
            if validate:
                available_tools = self._get_available_tools()
                ast_validation = self.validator.validate_ast(ast, available_tools)

                if not ast_validation.is_valid:
                    errors = ast_validation.get_errors()
                    raise DSLValidationError(f"AST validation failed: {errors}")

                # Log warnings
                warnings = ast_validation.get_warnings()
                for warning in warnings:
                    self.logger.warning(f"DSL Warning: {warning['message']}")

            return ast

        except (DSLSyntaxError, DSLValidationError):
            raise
        except Exception as e:
            raise DSLSyntaxError(f"Failed to parse DSL: {str(e)}")

    async def execute_ast(
        self, ast: AST, context: ExecutionContext | None = None, use_cache: bool = True
    ) -> ExecutionResult:
        """Execute AST with proper node handling and caching.

        Args:
            ast: AST to execute
            context: Execution context
            use_cache: Whether to use caching

        Returns:
            Execution result

        """
        if not ast.nodes:
            return ExecutionResult(
                success=True,
                data={"message": "Empty AST - nothing to execute"},
                metadata={"node_count": 0},
            )

        try:
            results = []

            for i, node in enumerate(ast.nodes):
                self.logger.debug(f"Executing node {i}: {node.type.value}")

                node_result = await self._execute_node(node, context, use_cache)
                results.append(node_result)

                # Break on error if not in parallel mode
                if isinstance(node_result, dict) and not node_result.get(
                    "success", True
                ):
                    if node.type not in [NodeType.PARALLEL]:
                        break

            return ExecutionResult(
                success=True,
                data={
                    "status": "completed",
                    "results": results,
                    "node_count": len(ast.nodes),
                },
                metadata={"ast_metadata": ast.metadata, "execution_mode": "sequential"},
            )

        except Exception as e:
            self.logger.error(f"AST execution failed: {e}")
            return ExecutionResult(
                success=False, error=str(e), metadata={"failed_at": "ast_execution"}
            )

    async def _execute_node(
        self,
        node: ASTNode,
        context: ExecutionContext | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Execute individual AST node with type-specific handling.
        Matches Go SDK executeNode functionality.

        Args:
            node: AST node to execute
            context: Execution context
            use_cache: Whether to use caching

        Returns:
            Execution result dictionary

        """
        try:
            if node.type == NodeType.CALL:
                return await self._execute_call_node(node, context, use_cache)
            if node.type == NodeType.PARALLEL:
                return await self._execute_parallel_node(node, context, use_cache)
            if node.type == NodeType.SEQUENCE:
                return await self._execute_sequence_node(node, context, use_cache)
            if node.type == NodeType.CONDITIONAL:
                return await self._execute_conditional_node(node, context, use_cache)
            if node.type == NodeType.WORKFLOW:
                return await self._execute_workflow_node(node, context)
            if node.type == NodeType.TASK:
                return await self._execute_task_node(node, context)
            if node.type == NodeType.AGENT:
                return await self._execute_agent_node(node, context)
            return {
                "type": node.type.value,
                "value": node.value,
                "args": node.args,
                "status": "executed",
                "message": "Default node execution",
            }

        except Exception as e:
            self.logger.error(f"Node execution failed: {e}")
            return {
                "type": node.type.value,
                "status": "failed",
                "error": str(e),
                "success": False,
            }

    async def _execute_call_node(
        self,
        node: ASTNode,
        context: ExecutionContext | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Execute CALL node with caching and agent selection.
        Implements Go SDK executeCall functionality.
        """
        tool_name = node.tool_name
        args = node.args or {}

        self.logger.info(f"Executing tool: {tool_name} with args: {args}")

        # Check cache first
        if use_cache:
            cached_result = self.cache.get(tool_name, args)
            if cached_result is not None:
                self.logger.info(f"Cache hit for tool {tool_name}")
                self.stats["cache_hits"] += 1
                return {
                    "type": "call",
                    "tool": tool_name,
                    "args": args,
                    "status": "executed",
                    "result": cached_result,
                    "cache_hit": True,
                    "success": True,
                }

        # Execute tool
        if self.agent_interface is None:
            # Simulation mode
            self.logger.debug("No agent integration, simulating execution")
            result = {
                "type": "call",
                "tool": tool_name,
                "args": args,
                "status": "simulated",
                "message": f"Simulated execution of {tool_name}",
                "success": True,
            }
        else:
            # Real execution with agent
            result = await self._execute_tool_with_agent(tool_name, args)

        # Cache successful results
        if use_cache and result.get("success", True) and "result" in result:
            self.cache.set(tool_name, args, result["result"])
            self.stats["cache_misses"] += 1

        return result

    async def _execute_tool_with_agent(
        self, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute tool using agent interface with local/remote selection."""
        try:
            # Try local execution first
            if self.agent_interface.has_local_tool(tool_name):
                self.logger.info(f"Executing tool {tool_name} locally")
                result = await self.agent_interface.execute_local_tool(tool_name, args)

                return {
                    "type": "call",
                    "tool": tool_name,
                    "args": args,
                    "status": "executed",
                    "result": result,
                    "executed_by": "local",
                    "success": True,
                }

            # Try remote execution
            peer_id = await self.agent_interface.find_agent_with_tool(tool_name)
            if peer_id:
                self.logger.info(f"Executing tool {tool_name} remotely on {peer_id}")
                result = await self.agent_interface.execute_remote_tool(
                    peer_id, tool_name, args
                )

                return {
                    "type": "call",
                    "tool": tool_name,
                    "args": args,
                    "status": "executed",
                    "result": result,
                    "executed_by": peer_id,
                    "success": True,
                }

            # Tool not found
            return {
                "type": "call",
                "tool": tool_name,
                "args": args,
                "status": "failed",
                "error": f"Tool {tool_name} not found locally or remotely",
                "success": False,
            }

        except Exception as e:
            return {
                "type": "call",
                "tool": tool_name,
                "args": args,
                "status": "failed",
                "error": str(e),
                "success": False,
            }

    async def _execute_parallel_node(
        self,
        node: ASTNode,
        context: ExecutionContext | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Execute PARALLEL node with concurrent child execution."""
        self.logger.info(f"Executing {len(node.children)} tasks in parallel")

        # Execute all children concurrently
        tasks = [
            self._execute_node(child, context, use_cache) for child in node.children
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle exceptions
            processed_results = []
            success_count = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        {
                            "status": "failed",
                            "error": str(result),
                            "child_index": i,
                            "success": False,
                        }
                    )
                else:
                    processed_results.append(result)
                    if result.get("success", True):
                        success_count += 1

            return {
                "type": "parallel",
                "results": processed_results,
                "status": "completed",
                "success_count": success_count,
                "total_count": len(node.children),
                "success": success_count > 0,
            }

        except Exception as e:
            return {
                "type": "parallel",
                "status": "failed",
                "error": str(e),
                "success": False,
            }

    async def _execute_sequence_node(
        self,
        node: ASTNode,
        context: ExecutionContext | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Execute SEQUENCE node with ordered child execution."""
        self.logger.info(f"Executing {len(node.children)} tasks in sequence")

        results = []

        for i, child in enumerate(node.children):
            try:
                result = await self._execute_node(child, context, use_cache)
                results.append(result)

                # Stop on failure in sequence mode
                if not result.get("success", True):
                    self.logger.warning(
                        f"Sequence execution stopped at step {i} due to failure"
                    )
                    return {
                        "type": "sequence",
                        "results": results,
                        "status": "failed",
                        "failed_at_step": i,
                        "success": False,
                    }

            except Exception as e:
                results.append(
                    {"status": "failed", "error": str(e), "step": i, "success": False}
                )

                return {
                    "type": "sequence",
                    "results": results,
                    "status": "failed",
                    "failed_at_step": i,
                    "error": str(e),
                    "success": False,
                }

        return {
            "type": "sequence",
            "results": results,
            "status": "completed",
            "steps_completed": len(results),
            "success": True,
        }

    async def _execute_conditional_node(
        self,
        node: ASTNode,
        context: ExecutionContext | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Execute CONDITIONAL (IF/ELSE) node."""
        condition = node.args.get("condition", "true")

        # Simple condition evaluation (can be enhanced)
        condition_result = self._evaluate_condition(condition, context)

        self.logger.info(f"Conditional: '{condition}' = {condition_result}")

        # Choose which children to execute
        if condition_result:
            children_to_execute = node.children
            branch = "if"
        else:
            else_children = node.args.get("else_children", [])
            children_to_execute = else_children
            branch = "else"

        # Execute chosen branch
        results = []
        for child in children_to_execute:
            result = await self._execute_node(child, context, use_cache)
            results.append(result)

        return {
            "type": "conditional",
            "condition": condition,
            "condition_result": condition_result,
            "branch_executed": branch,
            "results": results,
            "status": "completed",
            "success": True,
        }

    def _evaluate_condition(
        self, condition: str, context: ExecutionContext | None = None
    ) -> bool:
        """Simple condition evaluation (can be enhanced with expression parser)."""
        condition = condition.strip().lower()

        # Simple boolean evaluation
        if condition in ["true", "1", "yes"]:
            return True
        if condition in ["false", "0", "no"]:
            return False

        # Variable-based conditions (if context provided)
        if context and context.variables:
            # Simple variable substitution
            for var_name, var_value in context.variables.items():
                condition = condition.replace(f"${var_name}", str(var_value))

        # Default to true for now
        return True

    async def _execute_workflow_node(
        self, node: ASTNode, context: ExecutionContext | None = None
    ) -> dict[str, Any]:
        """Execute WORKFLOW node."""
        workflow_name = node.args.get("name", "unnamed_workflow")

        return {
            "type": "workflow",
            "name": workflow_name,
            "status": "started",
            "args": node.args,
            "success": True,
        }

    async def _execute_task_node(
        self, node: ASTNode, context: ExecutionContext | None = None
    ) -> dict[str, Any]:
        """Execute TASK node."""
        task_name = node.args.get("name", "unnamed_task")

        return {
            "type": "task",
            "name": task_name,
            "status": "completed",
            "args": node.args,
            "success": True,
        }

    async def _execute_agent_node(
        self, node: ASTNode, context: ExecutionContext | None = None
    ) -> dict[str, Any]:
        """Execute AGENT node."""
        agent_id = node.args.get("agent_id", "default_agent")

        return {
            "type": "agent",
            "agent_id": agent_id,
            "status": "selected",
            "success": True,
        }

    def _get_available_tools(self) -> list[str] | None:
        """Get list of available tools from agent interface."""
        if self.agent_interface and hasattr(
            self.agent_interface.agent, "get_available_tools"
        ):
            tools = self.agent_interface.agent.get_available_tools()
            return [tool.get("name") for tool in tools if "name" in tool]
        return None

    def _update_stats(self, execution_time: float) -> None:
        """Update performance statistics."""
        self.stats["commands_processed"] += 1
        self.stats["total_execution_time"] += execution_time
        self.stats["avg_execution_time"] = (
            self.stats["total_execution_time"] / self.stats["commands_processed"]
        )

    def get_stats(self) -> dict[str, Any]:
        """Get parser statistics."""
        cache_stats = self.cache.get_stats()

        return {
            **self.stats,
            "cache_stats": cache_stats,
            "cache_hit_rate": (
                self.stats["cache_hits"]
                / max(self.stats["cache_hits"] + self.stats["cache_misses"], 1)
            ),
        }

    def clear_cache(self) -> None:
        """Clear execution cache."""
        self.cache.clear()
        self.logger.info("DSL parser cache cleared")

    async def generate_workflow_from_natural_language(
        self, user_request: str, network_context: NetworkContext | None = None
    ) -> WorkflowPlan | None:
        """Generate workflow from natural language using planner."""
        if not self.planner:
            self.logger.warning("No planner configured for natural language processing")
            return None

        if network_context is None:
            network_context = NetworkContext()
            # Populate from agent interface if available
            if self.agent_interface:
                tools = self._get_available_tools()
                if tools:
                    for tool in tools:
                        network_context.add_tool(
                            {"name": tool, "description": f"Tool: {tool}"}
                        )

        return await self.planner.generate_workflow_from_natural_language(
            user_request, network_context
        )

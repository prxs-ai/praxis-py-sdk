"""
Node Executor - Individual node execution with P2P delegation support.

Handles execution of individual workflow nodes with:
- Local and remote (P2P) execution capabilities
- Tool integration via DSL orchestrator
- Error handling and retry mechanisms
- Context management and data flow
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import trio

from loguru import logger

from ..agent import Agent
from ..dsl.orchestrator import DSLOrchestrator
from ..dsl.types import NodeType
from ..mcp.service import MCPService
from ..p2p.service import P2PService
from .models import WorkflowNode, NodeStatus, NodeResult, ExecutionContext


class NodeExecutor:
    """
    Executes individual workflow nodes with support for:
    - Local tool execution via DSL orchestrator
    - Remote P2P task delegation
    - Error handling and retry logic
    - Context management and data passing
    """
    
    def __init__(
        self,
        agent: Agent,
        dsl_orchestrator: Optional[DSLOrchestrator] = None
    ):
        self.agent = agent
        self.dsl_orchestrator = dsl_orchestrator
        
        # Component access
        self.p2p_service = getattr(agent, 'p2p_service', None)
        self.mcp_service = getattr(agent, 'mcp_service', None)
        
        # Execution statistics
        self.node_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "retried_executions": 0,
            "remote_executions": 0,
            "local_executions": 0,
            "average_execution_time": 0.0
        }
        
        logger.info("NodeExecutor initialized")
    
    async def execute_node(
        self, 
        node: WorkflowNode,
        context: ExecutionContext
    ) -> NodeResult:
        """
        Execute a single workflow node.
        
        Determines execution strategy (local vs remote) and handles
        retry logic, error recovery, and result processing.
        """
        
        logger.debug(f"Executing node {node.id}: {node.command}")
        
        start_time = time.time()
        self.node_stats["total_executions"] += 1
        
        result = NodeResult(
            node_id=node.id,
            status=NodeStatus.RUNNING,
            started_at=datetime.utcnow(),
            agent_id=node.agent_id
        )
        
        retry_count = 0
        max_retries = node.max_retries
        
        while retry_count <= max_retries:
            try:
                # Execute node based on type and configuration
                execution_result = await self._execute_node_internal(node, context)
                
                # Process successful result
                result.status = NodeStatus.COMPLETED
                result.result = execution_result.get('result')
                result.error = None
                result.completed_at = datetime.utcnow()
                result.retry_count = retry_count
                
                # Update statistics
                self.node_stats["successful_executions"] += 1
                if retry_count > 0:
                    self.node_stats["retried_executions"] += 1
                
                break
                
            except Exception as e:
                logger.warning(f"Node {node.id} execution failed (attempt {retry_count + 1}): {e}")
                
                retry_count += 1
                result.error = str(e)
                result.retry_count = retry_count
                
                # Check if we should retry
                if retry_count <= max_retries and self._should_retry_error(e):
                    logger.info(f"Retrying node {node.id} (attempt {retry_count + 1}/{max_retries + 1})")
                    
                    # Exponential backoff
                    delay = min(2 ** retry_count, 30)  # Max 30 second delay
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final failure
                    result.status = NodeStatus.FAILED
                    result.completed_at = datetime.utcnow()
                    
                    # Update statistics
                    self.node_stats["failed_executions"] += 1
                    
                    break
        
        # Calculate execution time
        execution_time = time.time() - start_time
        result.execution_time = execution_time
        
        # Update average execution time
        prev_avg = self.node_stats["average_execution_time"]
        total_execs = self.node_stats["total_executions"]
        self.node_stats["average_execution_time"] = (
            (prev_avg * (total_execs - 1) + execution_time) / total_execs
        )
        
        logger.debug(
            f"Node {node.id} execution completed: {result.status.value} "
            f"in {execution_time:.2f}s (retries: {retry_count})"
        )
        
        return result
    
    async def _execute_node_internal(
        self, 
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Internal node execution logic."""
        
        # Determine execution strategy
        if node.agent_id and node.agent_id != self.agent.config.agent_id:
            # Remote execution via P2P
            return await self._execute_remote_node(node, context)
        else:
            # Local execution
            return await self._execute_local_node(node, context)
    
    async def _execute_local_node(
        self, 
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute node locally via DSL orchestrator or MCP tools."""
        
        logger.debug(f"Executing node {node.id} locally")
        self.node_stats["local_executions"] += 1
        
        # Build DSL command from node
        dsl_command = self._build_dsl_command(node, context)
        
        if self.dsl_orchestrator:
            # Execute via DSL orchestrator
            result = await self.dsl_orchestrator.execute_command(
                command=dsl_command,
                context=context.to_dict()
            )
        else:
            # Execute via direct tool call
            result = await self._execute_direct_tool_call(node, context)
        
        return self._process_execution_result(result, node, context)
    
    async def _execute_remote_node(
        self, 
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute node remotely via P2P delegation."""
        
        logger.debug(f"Executing node {node.id} remotely on agent {node.agent_id}")
        self.node_stats["remote_executions"] += 1
        
        if not self.p2p_service:
            raise RuntimeError("P2P service not available for remote execution")
        
        # Build remote execution request
        remote_request = {
            "type": "node_execution",
            "node_id": node.id,
            "command": node.command,
            "arguments": node.arguments,
            "context": {
                "shared_data": context.shared_data,
                "execution_id": context.execution_id,
                "workflow_id": context.workflow_id
            }
        }
        
        # Send to remote agent
        try:
            response = await self.p2p_service.call_remote_tool(
                peer_id=node.agent_id,
                tool_name="execute_workflow_node",
                arguments=remote_request
            )
            
            if response.get("success"):
                return response
            else:
                raise RuntimeError(f"Remote execution failed: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"P2P remote execution failed for node {node.id}: {e}")
            raise
    
    async def _execute_direct_tool_call(
        self, 
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute node as direct MCP tool call."""
        
        if not self.mcp_service:
            raise RuntimeError("MCP service not available for tool execution")
        
        # Prepare tool arguments with context
        tool_args = node.arguments.copy()
        
        # Add context data if needed
        if context.shared_data:
            # Merge shared context data
            for key, value in context.shared_data.items():
                if key not in tool_args:
                    tool_args[f"context_{key}"] = value
        
        # Execute tool
        result = await self.mcp_service.call_tool(
            tool_name=node.command,
            arguments=tool_args
        )
        
        return result
    
    def _build_dsl_command(self, node: WorkflowNode, context: ExecutionContext) -> str:
        """Build DSL command string from node definition."""
        
        command_parts = []
        
        # Add node type prefix if needed
        if node.node_type == NodeType.CALL:
            command_parts.append("CALL")
        
        # Add command name
        command_parts.append(node.command)
        
        # Add arguments
        for key, value in node.arguments.items():
            if isinstance(value, str) and " " in value:
                # Quote arguments with spaces
                command_parts.append(f'--{key} "{value}"')
            else:
                command_parts.append(f"--{key} {value}")
        
        return " ".join(command_parts)
    
    def _process_execution_result(
        self, 
        raw_result: Any,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Process execution result and update shared context."""
        
        # Normalize result format
        if isinstance(raw_result, dict):
            result = raw_result
        else:
            result = {"result": raw_result}
        
        # Extract data for sharing
        if "data" in result:
            data_to_share = result["data"]
        elif "result" in result:
            data_to_share = result["result"]
        else:
            data_to_share = result
        
        # Update shared context with node result
        if isinstance(data_to_share, dict):
            # Share structured data
            for key, value in data_to_share.items():
                context_key = f"{node.id}_{key}"
                context.shared_data[context_key] = value
        else:
            # Share simple result
            context.shared_data[f"{node.id}_result"] = data_to_share
        
        # Share node output under its ID
        context.shared_data[node.id] = data_to_share
        
        return result
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        
        error_str = str(error).lower()
        
        # Non-retryable errors
        non_retryable_patterns = [
            "permission denied",
            "authentication failed", 
            "invalid argument",
            "not found",
            "syntax error"
        ]
        
        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return False
        
        # Retryable errors (network, temporary failures, etc.)
        retryable_patterns = [
            "timeout",
            "connection",
            "network",
            "service unavailable",
            "temporary"
        ]
        
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True
        
        # Default: retry for unknown errors
        return True
    
    async def execute_test_node(
        self,
        command: str,
        arguments: Dict[str, Any] = None,
        agent_id: Optional[str] = None
    ) -> NodeResult:
        """Execute a test node for debugging/validation."""
        
        test_node = WorkflowNode(
            id="test_node",
            name="test_execution",
            node_type=NodeType.CALL,
            command=command,
            arguments=arguments or {},
            agent_id=agent_id
        )
        
        test_context = ExecutionContext(
            workflow_id="test_workflow",
            execution_id="test_execution"
        )
        
        return await self.execute_node(test_node, test_context)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get node execution statistics."""
        stats = self.node_stats.copy()
        
        # Calculate derived metrics
        total = stats["total_executions"]
        if total > 0:
            stats["success_rate"] = stats["successful_executions"] / total * 100
            stats["failure_rate"] = stats["failed_executions"] / total * 100
            stats["retry_rate"] = stats["retried_executions"] / total * 100
            stats["remote_execution_rate"] = stats["remote_executions"] / total * 100
        else:
            stats["success_rate"] = 0
            stats["failure_rate"] = 0
            stats["retry_rate"] = 0 
            stats["remote_execution_rate"] = 0
        
        return stats
    
    async def validate_node_executable(self, node: WorkflowNode) -> List[str]:
        """Validate that a node can be executed."""
        
        issues = []
        
        # Check if command exists
        if not node.command:
            issues.append("Node has no command specified")
        
        # Check if remote agent is available
        if node.agent_id and node.agent_id != self.agent.config.agent_id:
            if not self.p2p_service:
                issues.append("P2P service required for remote execution but not available")
            else:
                # Check if remote agent is reachable
                peers = await self.p2p_service.list_peers()
                if node.agent_id not in peers:
                    issues.append(f"Remote agent {node.agent_id} not found in peer list")
        
        # Check if tool exists locally
        else:
            if self.mcp_service:
                available_tools = await self.mcp_service.list_tools()
                if node.command not in [tool.get("name") for tool in available_tools]:
                    issues.append(f"Tool '{node.command}' not found in available tools")
        
        # Validate arguments
        if node.arguments:
            for key, value in node.arguments.items():
                if not isinstance(key, str):
                    issues.append(f"Argument key must be string: {key}")
        
        return issues
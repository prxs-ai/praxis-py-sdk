"""
Graph Orchestrator - Main execution engine for visual workflows.

This is the central component that orchestrates workflow execution with:
- Parallel and sequential node execution
- Real-time progress tracking via WebSocket
- Error recovery and retry mechanisms  
- Integration with DSL AST nodes
- P2P task delegation for remote execution
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor
import trio

from loguru import logger

from ..agent import Agent
from ..bus import Event, EventType, event_bus
from ..dsl.types import ASTNode, NodeType
from ..dsl.orchestrator import DSLOrchestrator
from .models import (
    WorkflowGraph,
    WorkflowNode,
    WorkflowEdge, 
    NodeStatus,
    ExecutionContext,
    WorkflowResult,
    NodeResult,
    ProgressUpdate
)
from .node_executor import NodeExecutor
from .progress_tracker import ProgressTracker
from .error_recovery import ErrorRecovery


class GraphOrchestrator:
    """
    Main execution engine for graph-based workflows.
    
    Provides:
    - Graph execution with parallel/sequential node coordination
    - Real-time progress tracking and WebSocket events
    - Error recovery and retry mechanisms
    - Integration with existing DSL components
    - P2P task delegation capabilities
    """
    
    def __init__(
        self,
        agent: Agent,
        dsl_orchestrator: Optional[DSLOrchestrator] = None,
        max_parallel_nodes: int = 5,
        execution_timeout: int = 1800  # 30 minutes
    ):
        self.agent = agent
        self.dsl_orchestrator = dsl_orchestrator
        self.max_parallel_nodes = max_parallel_nodes
        self.execution_timeout = execution_timeout
        
        # Component initialization
        self.node_executor = NodeExecutor(agent, dsl_orchestrator)
        self.progress_tracker = ProgressTracker()
        self.error_recovery = ErrorRecovery()
        
        # Active executions tracking
        self.active_executions: Dict[str, WorkflowGraph] = {}
        self.execution_tasks: Dict[str, asyncio.Task] = {}
        
        # Performance metrics
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "total_nodes_executed": 0,
            "parallel_efficiency": 0.0
        }
        
        logger.info("GraphOrchestrator initialized")
    
    async def create_from_ast(
        self,
        ast_nodes: List[ASTNode],
        workflow_id: Optional[str] = None,
        execution_context: Optional[ExecutionContext] = None
    ) -> WorkflowGraph:
        """
        Create workflow graph from DSL AST nodes.
        
        Converts DSL AST structure to executable workflow graph with
        proper dependency resolution and parallel/sequential grouping.
        """
        
        workflow_id = workflow_id or str(uuid.uuid4())
        
        logger.info(f"Creating workflow graph {workflow_id} from {len(ast_nodes)} AST nodes")
        
        # Create execution context if not provided
        if not execution_context:
            execution_context = ExecutionContext(
                workflow_id=workflow_id,
                execution_id=str(uuid.uuid4()),
                max_parallel_nodes=self.max_parallel_nodes,
                global_timeout_seconds=self.execution_timeout
            )
        
        # Build workflow graph from AST nodes
        workflow = await self._build_graph_from_ast(ast_nodes, workflow_id, execution_context)
        
        # Validate graph structure
        validation_issues = workflow.validate_graph()
        if validation_issues:
            logger.warning(f"Workflow {workflow_id} validation issues: {validation_issues}")
        
        logger.info(f"Created workflow graph {workflow_id} with {len(workflow.nodes)} nodes")
        return workflow
    
    async def execute_workflow(
        self,
        workflow: WorkflowGraph,
        track_progress: bool = True
    ) -> WorkflowResult:
        """
        Execute workflow graph with progress tracking.
        
        Orchestrates parallel/sequential execution of nodes with
        real-time progress updates via WebSocket events.
        """
        
        execution_id = workflow.execution_context.execution_id if workflow.execution_context else str(uuid.uuid4())
        
        logger.info(f"Starting workflow execution {execution_id}")
        
        # Initialize execution tracking
        start_time = time.time()
        workflow.execution_context.started_at = datetime.utcnow()
        
        # Track active execution
        self.active_executions[execution_id] = workflow
        
        try:
            # Create execution task
            execution_task = asyncio.create_task(
                self._execute_workflow_internal(workflow, track_progress)
            )
            self.execution_tasks[execution_id] = execution_task
            
            # Execute with timeout
            result = await asyncio.wait_for(
                execution_task,
                timeout=self.execution_timeout
            )
            
            # Update statistics
            execution_time = time.time() - start_time
            await self._update_execution_stats(result, execution_time)
            
            logger.info(f"Workflow execution {execution_id} completed in {execution_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Workflow execution {execution_id} timed out")
            await self._handle_execution_timeout(workflow)
            
            result = WorkflowResult(
                workflow_id=workflow.id,
                execution_id=execution_id,
                status="failed",
                error_summary="Execution timed out",
                started_at=workflow.execution_context.started_at,
                completed_at=datetime.utcnow(),
                total_execution_time=time.time() - start_time
            )
            return result
            
        except Exception as e:
            logger.exception(f"Workflow execution {execution_id} failed: {e}")
            
            result = WorkflowResult(
                workflow_id=workflow.id,
                execution_id=execution_id,
                status="failed", 
                error_summary=str(e),
                started_at=workflow.execution_context.started_at,
                completed_at=datetime.utcnow(),
                total_execution_time=time.time() - start_time
            )
            return result
            
        finally:
            # Cleanup
            self.active_executions.pop(execution_id, None)
            self.execution_tasks.pop(execution_id, None)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel active workflow execution."""
        
        if execution_id not in self.execution_tasks:
            logger.warning(f"No active execution found for {execution_id}")
            return False
        
        logger.info(f"Cancelling workflow execution {execution_id}")
        
        task = self.execution_tasks[execution_id]
        task.cancel()
        
        # Update node statuses to cancelled
        if execution_id in self.active_executions:
            workflow = self.active_executions[execution_id]
            for node in workflow.nodes.values():
                if node.status in [NodeStatus.PENDING, NodeStatus.RUNNING]:
                    node.status = NodeStatus.CANCELLED
        
        # Send cancellation event
        await self._emit_progress_update(
            execution_id,
            ProgressUpdate(
                workflow_id=workflow.id,
                execution_id=execution_id,
                update_type="workflow_status",
                message="Workflow execution cancelled",
                data={"status": "cancelled"}
            )
        )
        
        return True
    
    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of workflow execution."""
        
        if execution_id not in self.active_executions:
            return None
        
        workflow = self.active_executions[execution_id]
        
        # Calculate progress
        total_nodes = len(workflow.nodes)
        completed_nodes = sum(1 for node in workflow.nodes.values() 
                            if node.status == NodeStatus.COMPLETED)
        failed_nodes = sum(1 for node in workflow.nodes.values()
                         if node.status == NodeStatus.FAILED)
        running_nodes = sum(1 for node in workflow.nodes.values()
                          if node.status == NodeStatus.RUNNING)
        
        progress_percentage = (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0
        
        return {
            "execution_id": execution_id,
            "workflow_id": workflow.id,
            "status": "running" if running_nodes > 0 else "pending",
            "progress_percentage": progress_percentage,
            "total_nodes": total_nodes,
            "completed_nodes": completed_nodes,
            "failed_nodes": failed_nodes,
            "running_nodes": running_nodes,
            "started_at": workflow.execution_context.started_at.isoformat() if workflow.execution_context.started_at else None,
            "node_statuses": {
                node_id: {
                    "status": node.status.value,
                    "name": node.name,
                    "execution_time": node.execution_time,
                    "error": node.error
                }
                for node_id, node in workflow.nodes.items()
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return self.execution_stats.copy()
    
    # Internal implementation methods
    
    async def _build_graph_from_ast(
        self,
        ast_nodes: List[ASTNode], 
        workflow_id: str,
        execution_context: ExecutionContext
    ) -> WorkflowGraph:
        """Build workflow graph from AST nodes with proper dependency resolution."""
        
        workflow = WorkflowGraph(
            id=workflow_id,
            name=f"workflow_{workflow_id[:8]}",
            execution_context=execution_context
        )
        
        # Parse AST nodes into workflow structure
        node_stack: List[WorkflowNode] = []
        parallel_groups: List[List[str]] = []
        current_parallel_group: Optional[List[str]] = None
        
        for ast_node in ast_nodes:
            if ast_node.type == NodeType.PARALLEL:
                # Start new parallel group
                current_parallel_group = []
                parallel_groups.append(current_parallel_group)
                continue
                
            elif ast_node.type == NodeType.SEQUENCE:
                # End parallel execution, continue sequential
                current_parallel_group = None
                continue
                
            elif ast_node.type == NodeType.CONDITIONAL:
                # Handle conditional nodes
                await self._process_conditional_node(ast_node, workflow, node_stack)
                continue
                
            elif ast_node.type in [NodeType.CALL, NodeType.COMMAND]:
                # Create executable node
                node_id = str(uuid.uuid4())
                node = WorkflowNode.from_ast_node(ast_node, node_id)
                
                # Set up dependencies
                if current_parallel_group is not None:
                    # Add to parallel group
                    current_parallel_group.append(node_id)
                elif node_stack:
                    # Sequential dependency on previous node
                    prev_node = node_stack[-1]
                    node.dependencies.add(prev_node.id)
                    prev_node.dependents.add(node_id)
                
                workflow.nodes[node_id] = node
                node_stack.append(node)
        
        # Create edges from dependencies
        workflow._create_edges_from_dependencies()
        
        return workflow
    
    async def _execute_workflow_internal(
        self,
        workflow: WorkflowGraph,
        track_progress: bool
    ) -> WorkflowResult:
        """Internal workflow execution with orchestration."""
        
        execution_id = workflow.execution_context.execution_id
        result = WorkflowResult(
            workflow_id=workflow.id,
            execution_id=execution_id,
            status="running",
            started_at=datetime.utcnow()
        )
        
        if track_progress:
            await self._emit_workflow_start(workflow)
        
        # Track execution state
        completed_nodes: Set[str] = set()
        failed_nodes: Set[str] = set()
        running_nodes: Dict[str, asyncio.Task] = {}
        
        try:
            # Main execution loop
            while True:
                # Check for nodes ready to execute
                ready_nodes = workflow.get_ready_nodes(completed_nodes)
                
                # Filter out already running nodes
                ready_nodes = [
                    node for node in ready_nodes 
                    if node.id not in running_nodes
                ]
                
                # Start new node executions (respecting parallel limit)
                available_slots = self.max_parallel_nodes - len(running_nodes)
                nodes_to_start = ready_nodes[:available_slots]
                
                for node in nodes_to_start:
                    task = asyncio.create_task(
                        self._execute_single_node(node, workflow, track_progress)
                    )
                    running_nodes[node.id] = task
                    node.status = NodeStatus.RUNNING
                    node.started_at = datetime.utcnow()
                
                # Wait for at least one running node to complete
                if running_nodes:
                    done, pending = await asyncio.wait(
                        running_nodes.values(),
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Process completed nodes
                    for task in done:
                        node_result = await task
                        node_id = node_result.node_id
                        
                        # Update node status
                        node = workflow.nodes[node_id]
                        node.status = node_result.status
                        node.result = node_result.result
                        node.error = node_result.error
                        node.execution_time = node_result.execution_time
                        node.completed_at = node_result.completed_at
                        
                        # Update tracking sets
                        running_nodes.pop(node_id, None)
                        
                        if node_result.status == NodeStatus.COMPLETED:
                            completed_nodes.add(node_id)
                            result.nodes_completed += 1
                        elif node_result.status == NodeStatus.FAILED:
                            failed_nodes.add(node_id)
                            result.nodes_failed += 1
                            
                            # Check if this is a critical failure
                            if await self._is_critical_failure(node, workflow):
                                logger.error(f"Critical failure in node {node_id}, stopping workflow")
                                break
                        
                        result.node_results[node_id] = node_result
                        
                        # Send progress update
                        if track_progress:
                            await self._emit_node_completion(node, node_result, workflow)
                
                # Check completion conditions
                total_nodes = len(workflow.nodes)
                processed_nodes = len(completed_nodes) + len(failed_nodes)
                
                if processed_nodes >= total_nodes:
                    # All nodes processed
                    break
                    
                if not running_nodes and not ready_nodes:
                    # No more nodes can execute
                    remaining_nodes = total_nodes - processed_nodes
                    if remaining_nodes > 0:
                        logger.warning(f"Workflow stuck: {remaining_nodes} nodes cannot execute")
                        result.status = "failed"
                        result.error_summary = f"{remaining_nodes} nodes blocked by dependencies"
                    break
            
            # Determine final status
            if result.nodes_failed == 0:
                result.status = "completed"
            elif result.nodes_completed > 0:
                result.status = "partial"
            else:
                result.status = "failed"
                
        except Exception as e:
            logger.exception(f"Workflow execution error: {e}")
            result.status = "failed"
            result.error_summary = str(e)
            
        finally:
            # Cancel any remaining running tasks
            for task in running_nodes.values():
                if not task.done():
                    task.cancel()
            
            result.completed_at = datetime.utcnow()
            if result.started_at:
                result.total_execution_time = (
                    result.completed_at - result.started_at
                ).total_seconds()
            
            if track_progress:
                await self._emit_workflow_completion(workflow, result)
        
        return result
    
    async def _execute_single_node(
        self,
        node: WorkflowNode,
        workflow: WorkflowGraph,
        track_progress: bool
    ) -> NodeResult:
        """Execute a single workflow node."""
        
        logger.debug(f"Executing node {node.id}: {node.name}")
        
        start_time = time.time()
        
        try:
            # Execute node via NodeExecutor
            result = await self.node_executor.execute_node(
                node, 
                workflow.execution_context
            )
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            if track_progress:
                await self._emit_progress_update(
                    workflow.execution_context.execution_id,
                    ProgressUpdate(
                        workflow_id=workflow.id,
                        execution_id=workflow.execution_context.execution_id,
                        update_type="node_status",
                        node_id=node.id,
                        old_status=NodeStatus.RUNNING,
                        new_status=result.status,
                        message=f"Node {node.name} {result.status.value}",
                        data={
                            "execution_time": execution_time,
                            "result": result.result if result.status == NodeStatus.COMPLETED else None,
                            "error": result.error if result.error else None
                        }
                    )
                )
            
            return result
            
        except Exception as e:
            logger.exception(f"Node execution error: {e}")
            
            execution_time = time.time() - start_time
            
            result = NodeResult(
                node_id=node.id,
                status=NodeStatus.FAILED,
                error=str(e),
                execution_time=execution_time,
                started_at=node.started_at,
                completed_at=datetime.utcnow()
            )
            
            return result
    
    async def _process_conditional_node(
        self,
        ast_node: ASTNode,
        workflow: WorkflowGraph,
        node_stack: List[WorkflowNode]
    ):
        """Process conditional AST nodes (IF/ELSE structures)."""
        # Implementation for conditional logic
        # This would be expanded based on conditional DSL requirements
        pass
    
    async def _is_critical_failure(self, node: WorkflowNode, workflow: WorkflowGraph) -> bool:
        """Determine if a node failure should stop the entire workflow."""
        
        # Check if this node has dependents
        if not node.dependents:
            return False  # Leaf node failure is not critical
        
        # Check if there are alternative paths
        # For now, treat any node with dependents as critical
        return len(node.dependents) > 0
    
    async def _update_execution_stats(self, result: WorkflowResult, execution_time: float):
        """Update execution statistics."""
        
        self.execution_stats["total_executions"] += 1
        
        if result.status == "completed":
            self.execution_stats["successful_executions"] += 1
        else:
            self.execution_stats["failed_executions"] += 1
        
        # Update average execution time
        prev_avg = self.execution_stats["average_execution_time"]
        total_execs = self.execution_stats["total_executions"]
        self.execution_stats["average_execution_time"] = (
            (prev_avg * (total_execs - 1) + execution_time) / total_execs
        )
        
        self.execution_stats["total_nodes_executed"] += len(result.node_results)
    
    async def _handle_execution_timeout(self, workflow: WorkflowGraph):
        """Handle workflow execution timeout."""
        
        logger.warning(f"Workflow {workflow.id} execution timed out")
        
        # Mark all running/pending nodes as cancelled
        for node in workflow.nodes.values():
            if node.status in [NodeStatus.PENDING, NodeStatus.RUNNING]:
                node.status = NodeStatus.CANCELLED
    
    # Progress tracking and WebSocket events
    
    async def _emit_workflow_start(self, workflow: WorkflowGraph):
        """Emit workflow start event."""
        
        await event_bus.publish(Event(
            type=EventType.TASK_STARTED,
            data={
                "type": "workflowStart",
                "workflowId": workflow.id,
                "executionId": workflow.execution_context.execution_id,
                "totalNodes": len(workflow.nodes),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ))
    
    async def _emit_workflow_completion(self, workflow: WorkflowGraph, result: WorkflowResult):
        """Emit workflow completion event."""
        
        event_type = EventType.TASK_COMPLETED if result.status == "completed" else EventType.TASK_FAILED
        
        await event_bus.publish(Event(
            type=event_type,
            data={
                "type": "workflowComplete" if result.status == "completed" else "workflowError",
                "workflowId": workflow.id,
                "executionId": workflow.execution_context.execution_id,
                "status": result.status,
                "nodesCompleted": result.nodes_completed,
                "nodesFailed": result.nodes_failed,
                "totalExecutionTime": result.total_execution_time,
                "error": result.error_summary if result.error_summary else None,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ))
    
    async def _emit_node_completion(
        self, 
        node: WorkflowNode, 
        result: NodeResult, 
        workflow: WorkflowGraph
    ):
        """Emit node completion event."""
        
        await event_bus.publish(Event(
            type=EventType.NODE_STATUS_UPDATE,
            data={
                "type": "nodeStatusUpdate",
                "workflowId": workflow.id,
                "executionId": workflow.execution_context.execution_id,
                "nodeId": node.id,
                "nodeName": node.name,
                "status": result.status.value,
                "executionTime": result.execution_time,
                "error": result.error if result.error else None,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ))
    
    async def _emit_progress_update(self, execution_id: str, update: ProgressUpdate):
        """Emit general progress update."""
        
        await event_bus.publish(Event(
            type=EventType.TASK_PROGRESS,
            data={
                "type": "workflowProgress",
                "executionId": execution_id,
                "updateType": update.update_type,
                "message": update.message,
                "data": update.data,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ))
"""
Workflow API Handlers for Frontend Integration.

This module provides FastAPI handlers for the /api/workflow/* endpoints
required by the React frontend, ensuring full compatibility with the
frontend's API client expectations.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import trio
from fastapi import BackgroundTasks, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from praxis_sdk.bus import Event, EventType, event_bus
from praxis_sdk.a2a.models import Task, Message, TaskState, create_message
from praxis_sdk.api.websocket import MessageType


class WorkflowNode(BaseModel):
    """Frontend workflow node structure."""
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]


class WorkflowEdge(BaseModel):
    """Frontend workflow edge structure."""
    id: str
    source: str
    target: str
    data: Optional[Dict[str, Any]] = None


class WorkflowMetadata(BaseModel):
    """Frontend workflow metadata structure."""
    name: str
    description: str
    version: str = "1.0.0"
    createdAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class WorkflowExecutionPayload(BaseModel):
    """Frontend workflow execution payload."""
    workflow_id: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    metadata: WorkflowMetadata


class WorkflowExecutionResponse(BaseModel):
    """Frontend workflow execution response."""
    success: bool
    workflowId: str
    executionId: str
    message: str
    estimatedDuration: Optional[int] = None


class WorkflowStatusResponse(BaseModel):
    """Frontend workflow status response."""
    workflowId: str
    executionId: str
    status: str = Field(
        description="'idle' | 'running' | 'paused' | 'completed' | 'error' | 'cancelled'"
    )
    progress: int = Field(ge=0, le=100)
    currentNode: Optional[str] = None
    completedNodes: List[str] = Field(default_factory=list)
    erroredNodes: List[str] = Field(default_factory=list)
    startTime: str
    endTime: Optional[str] = None
    error: Optional[str] = None


class WorkflowCancelRequest(BaseModel):
    """Frontend workflow cancel request."""
    executionId: str


class WorkflowState:
    """Workflow state tracking."""
    def __init__(self):
        self.executions: Dict[str, Dict[str, Any]] = {}
        self.workflows: Dict[str, WorkflowExecutionPayload] = {}
    
    def create_execution(self, workflow_id: str, execution_id: str, payload: WorkflowExecutionPayload) -> None:
        """Create new workflow execution."""
        self.executions[workflow_id] = {
            "execution_id": execution_id,
            "status": "running",
            "progress": 0,
            "current_node": None,
            "completed_nodes": [],
            "errored_nodes": [],
            "start_time": datetime.utcnow().isoformat() + "Z",
            "end_time": None,
            "error": None,
            "payload": payload
        }
        self.workflows[workflow_id] = payload
        logger.info(f"Created workflow execution: {workflow_id} -> {execution_id}")
    
    def get_execution(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution state."""
        return self.executions.get(workflow_id)
    
    def update_execution(self, workflow_id: str, **updates) -> None:
        """Update workflow execution state."""
        if workflow_id in self.executions:
            self.executions[workflow_id].update(updates)
            logger.debug(f"Updated workflow {workflow_id}: {updates}")
    
    def cancel_execution(self, workflow_id: str) -> bool:
        """Cancel workflow execution."""
        if workflow_id in self.executions:
            self.executions[workflow_id]["status"] = "cancelled"
            self.executions[workflow_id]["end_time"] = datetime.utcnow().isoformat() + "Z"
            logger.info(f"Cancelled workflow execution: {workflow_id}")
            return True
        return False
    
    def complete_execution(self, workflow_id: str, success: bool = True) -> None:
        """Complete workflow execution."""
        if workflow_id in self.executions:
            self.executions[workflow_id]["status"] = "completed" if success else "error"
            self.executions[workflow_id]["progress"] = 100
            self.executions[workflow_id]["end_time"] = datetime.utcnow().isoformat() + "Z"
            logger.info(f"Completed workflow execution: {workflow_id} (success: {success})")


# Global workflow state manager
workflow_state = WorkflowState()


class WorkflowHandlers:
    """Workflow API handlers for frontend compatibility."""
    
    @staticmethod
    async def execute_workflow(payload: WorkflowExecutionPayload, background_tasks: BackgroundTasks) -> WorkflowExecutionResponse:
        """Execute workflow - main frontend endpoint."""
        try:
            workflow_id = payload.workflow_id
            execution_id = str(uuid4())
            
            logger.info(f"Starting workflow execution: {workflow_id}")
            logger.debug(f"Workflow payload: {payload.dict()}")
            
            # Create execution state
            workflow_state.create_execution(workflow_id, execution_id, payload)
            
            # Broadcast workflow start event
            await event_bus.publish(Event(
                type=EventType.TASK_STARTED,
                data={
                    "type": "workflowStart",
                    "workflowId": workflow_id,
                    "executionId": execution_id,
                    "nodes": [node.dict() for node in payload.nodes],
                    "edges": [edge.dict() for edge in payload.edges],
                    "metadata": payload.metadata.dict(),
                    "startTime": datetime.utcnow().isoformat() + "Z"
                }
            ))
            
            # Schedule background workflow execution
            background_tasks.add_task(
                WorkflowHandlers._execute_workflow_async,
                workflow_id,
                execution_id,
                payload
            )
            
            # Estimate duration based on node count
            estimated_duration = max(30, len(payload.nodes) * 10)  # 10 seconds per node, minimum 30s
            
            return WorkflowExecutionResponse(
                success=True,
                workflowId=workflow_id,
                executionId=execution_id,
                message="Workflow execution started successfully",
                estimatedDuration=estimated_duration
            )
            
        except Exception as e:
            logger.error(f"Error starting workflow execution: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start workflow execution: {str(e)}"
            )
    
    @staticmethod
    async def cancel_workflow(workflow_id: str, request: WorkflowCancelRequest) -> Dict[str, Any]:
        """Cancel workflow execution."""
        try:
            execution_id = request.executionId
            logger.info(f"Cancelling workflow: {workflow_id} (execution: {execution_id})")
            
            # Cancel execution
            success = workflow_state.cancel_execution(workflow_id)
            
            if success:
                # Broadcast cancellation event
                await event_bus.publish(Event(
                    type=EventType.TASK_FAILED,
                    data={
                        "type": "workflowError",
                        "workflowId": workflow_id,
                        "executionId": execution_id,
                        "error": "Workflow cancelled by user",
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                ))
                
                return {
                    "success": True,
                    "message": f"Workflow {workflow_id} cancelled successfully"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {workflow_id} not found"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error cancelling workflow {workflow_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel workflow: {str(e)}"
            )
    
    @staticmethod
    async def get_workflow_status(workflow_id: str) -> WorkflowStatusResponse:
        """Get workflow execution status."""
        try:
            execution = workflow_state.get_execution(workflow_id)
            
            if not execution:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {workflow_id} not found"
                )
            
            return WorkflowStatusResponse(
                workflowId=workflow_id,
                executionId=execution["execution_id"],
                status=execution["status"],
                progress=execution["progress"],
                currentNode=execution["current_node"],
                completedNodes=execution["completed_nodes"],
                erroredNodes=execution["errored_nodes"],
                startTime=execution["start_time"],
                endTime=execution["end_time"],
                error=execution["error"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting workflow status {workflow_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get workflow status: {str(e)}"
            )
    
    @staticmethod
    async def list_workflows(
        state: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List all workflows with pagination."""
        try:
            all_workflows = []
            
            for workflow_id, execution in workflow_state.executions.items():
                if state and execution["status"] != state:
                    continue
                
                workflow_info = {
                    "workflowId": workflow_id,
                    "executionId": execution["execution_id"],
                    "status": execution["status"],
                    "progress": execution["progress"],
                    "startTime": execution["start_time"],
                    "endTime": execution["end_time"],
                    "metadata": execution["payload"].metadata.dict() if "payload" in execution else {}
                }
                all_workflows.append(workflow_info)
            
            # Apply pagination
            total = len(all_workflows)
            workflows = all_workflows[offset:offset + limit]
            
            return {
                "workflows": workflows,
                "total": total,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total
            }
            
        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list workflows: {str(e)}"
            )
    
    @staticmethod
    async def get_workflow(workflow_id: str) -> Dict[str, Any]:
        """Get detailed workflow information."""
        try:
            execution = workflow_state.get_execution(workflow_id)
            
            if not execution:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {workflow_id} not found"
                )
            
            payload = execution.get("payload")
            
            return {
                "workflowId": workflow_id,
                "executionId": execution["execution_id"],
                "status": execution["status"],
                "progress": execution["progress"],
                "currentNode": execution["current_node"],
                "completedNodes": execution["completed_nodes"],
                "erroredNodes": execution["errored_nodes"],
                "startTime": execution["start_time"],
                "endTime": execution["end_time"],
                "error": execution["error"],
                "nodes": [node.dict() for node in payload.nodes] if payload else [],
                "edges": [edge.dict() for edge in payload.edges] if payload else [],
                "metadata": payload.metadata.dict() if payload else {}
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting workflow {workflow_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get workflow: {str(e)}"
            )
    
    @staticmethod
    async def create_workflow(payload: WorkflowExecutionPayload) -> Dict[str, Any]:
        """Create workflow without execution."""
        try:
            workflow_id = payload.workflow_id
            
            # Store workflow definition
            workflow_state.workflows[workflow_id] = payload
            
            logger.info(f"Created workflow definition: {workflow_id}")
            
            return {
                "success": True,
                "workflowId": workflow_id,
                "message": "Workflow created successfully",
                "createdAt": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create workflow: {str(e)}"
            )
    
    @staticmethod
    async def update_workflow(workflow_id: str, payload: WorkflowExecutionPayload) -> Dict[str, Any]:
        """Update existing workflow."""
        try:
            if workflow_id not in workflow_state.workflows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {workflow_id} not found"
                )
            
            # Update workflow definition
            workflow_state.workflows[workflow_id] = payload
            
            logger.info(f"Updated workflow: {workflow_id}")
            
            return {
                "success": True,
                "workflowId": workflow_id,
                "message": "Workflow updated successfully",
                "updatedAt": datetime.utcnow().isoformat() + "Z"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating workflow {workflow_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update workflow: {str(e)}"
            )
    
    @staticmethod
    async def delete_workflow(workflow_id: str) -> Dict[str, Any]:
        """Delete workflow."""
        try:
            # Cancel active execution if exists
            if workflow_id in workflow_state.executions:
                workflow_state.cancel_execution(workflow_id)
            
            # Remove workflow definition
            if workflow_id in workflow_state.workflows:
                del workflow_state.workflows[workflow_id]
            
            # Remove execution state
            if workflow_id in workflow_state.executions:
                del workflow_state.executions[workflow_id]
            
            logger.info(f"Deleted workflow: {workflow_id}")
            
            return {
                "success": True,
                "workflowId": workflow_id,
                "message": "Workflow deleted successfully",
                "deletedAt": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Error deleting workflow {workflow_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete workflow: {str(e)}"
            )
    
    @staticmethod
    async def _execute_workflow_async(workflow_id: str, execution_id: str, payload: WorkflowExecutionPayload):
        """Async workflow execution in background."""
        try:
            logger.info(f"Starting async workflow execution: {workflow_id}")
            
            nodes = payload.nodes
            total_nodes = len(nodes)
            
            # Process each node
            for i, node in enumerate(nodes):
                node_id = node.id
                node_type = node.type
                
                # Update current node
                workflow_state.update_execution(
                    workflow_id,
                    current_node=node_id,
                    progress=int((i / total_nodes) * 90)  # Leave 10% for completion
                )
                
                # Broadcast node start
                await event_bus.publish(Event(
                    type=EventType.TASK_PROGRESS,
                    data={
                        "type": "workflowStep",
                        "workflowId": workflow_id,
                        "executionId": execution_id,
                        "nodeId": node_id,
                        "status": "running",
                        "message": f"Processing {node_type} node: {node_id}",
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                ))
                
                # Simulate node processing
                try:
                    await asyncio.sleep(2)  # Simulate work
                    
                    # Mark node completed
                    execution = workflow_state.get_execution(workflow_id)
                    if execution:
                        completed_nodes = execution.get("completed_nodes", [])
                        completed_nodes.append(node_id)
                        workflow_state.update_execution(workflow_id, completed_nodes=completed_nodes)
                    
                    # Broadcast node completion
                    await event_bus.publish(Event(
                        type=EventType.TASK_PROGRESS,
                        data={
                            "type": "workflowStepComplete",
                            "workflowId": workflow_id,
                            "executionId": execution_id,
                            "nodeId": node_id,
                            "status": "completed",
                            "result": {"message": f"Node {node_id} completed successfully"},
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                    ))
                    
                except Exception as node_error:
                    logger.error(f"Error processing node {node_id}: {node_error}")
                    
                    # Mark node as errored
                    execution = workflow_state.get_execution(workflow_id)
                    if execution:
                        errored_nodes = execution.get("errored_nodes", [])
                        errored_nodes.append(node_id)
                        workflow_state.update_execution(
                            workflow_id,
                            errored_nodes=errored_nodes,
                            error=f"Node {node_id} failed: {str(node_error)}"
                        )
                    
                    # Broadcast node error
                    await event_bus.publish(Event(
                        type=EventType.TASK_FAILED,
                        data={
                            "type": "workflowError",
                            "workflowId": workflow_id,
                            "executionId": execution_id,
                            "nodeId": node_id,
                            "error": str(node_error),
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                    ))
                    
                    # Continue processing other nodes or stop on critical error
                    continue
            
            # Complete workflow
            workflow_state.complete_execution(workflow_id, success=True)
            
            # Broadcast completion
            await event_bus.publish(Event(
                type=EventType.TASK_COMPLETED,
                data={
                    "type": "workflowComplete",
                    "workflowId": workflow_id,
                    "executionId": execution_id,
                    "message": "Workflow execution completed successfully",
                    "results": f"Processed {total_nodes} nodes successfully",
                    "duration": (datetime.utcnow() - datetime.fromisoformat(
                        workflow_state.get_execution(workflow_id)["start_time"].replace("Z", "+00:00")
                    )).total_seconds(),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ))
            
            logger.info(f"Completed workflow execution: {workflow_id}")
            
        except Exception as e:
            logger.error(f"Error in async workflow execution {workflow_id}: {e}")
            
            # Mark workflow as failed
            workflow_state.update_execution(
                workflow_id,
                status="error",
                error=str(e),
                end_time=datetime.utcnow().isoformat() + "Z"
            )
            
            # Broadcast error
            await event_bus.publish(Event(
                type=EventType.TASK_FAILED,
                data={
                    "type": "workflowError",
                    "workflowId": workflow_id,
                    "executionId": execution_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ))


# Export handlers instance
workflow_handlers = WorkflowHandlers()
"""
Workflow Graph Data Models

Defines the core data structures for graph-based workflow orchestration,
including nodes, edges, execution contexts, and progress tracking.
"""

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field, asdict

from ..dsl.types import ASTNode, NodeType


class NodeStatus(str, Enum):
    """Status of a workflow node during execution."""
    PENDING = "pending"
    READY = "ready"  # Dependencies satisfied, ready to execute
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Conditional execution skipped this node
    CANCELLED = "cancelled"


class EdgeType(str, Enum):
    """Type of connection between workflow nodes."""
    SEQUENCE = "sequence"  # Sequential dependency
    PARALLEL = "parallel"  # Parallel execution branch
    CONDITIONAL = "conditional"  # Conditional dependency
    DATA_FLOW = "data_flow"  # Data passing between nodes
    ERROR_HANDLER = "error_handler"  # Error recovery path


@dataclass
class WorkflowNode:
    """
    Individual node in a workflow graph.
    
    Represents a single executable unit (tool call, DSL command, etc.)
    with dependencies, status, and execution metadata.
    """
    
    id: str
    name: str
    node_type: NodeType  # From DSL types
    command: str  # DSL command or tool name
    arguments: Dict[str, Any] = field(default_factory=dict)
    
    # Execution metadata
    status: NodeStatus = NodeStatus.PENDING
    agent_id: Optional[str] = None  # Which agent should execute this
    execution_time: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Dependencies
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    
    # Results
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300
    
    # Visual representation (for UI)
    position: Dict[str, float] = field(default_factory=dict)
    ui_data: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_ast_node(
        cls, 
        ast_node: ASTNode, 
        node_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> "WorkflowNode":
        """Create WorkflowNode from DSL AST node."""
        
        node_id = node_id or str(uuid.uuid4())
        
        # Extract command and arguments from AST node
        command = ast_node.value
        arguments = {}
        
        if hasattr(ast_node, 'args') and ast_node.args:
            arguments = ast_node.args.copy()
        
        # Determine node name
        name = f"{ast_node.type.value}_{command}" if command else ast_node.type.value
        
        return cls(
            id=node_id,
            name=name,
            node_type=ast_node.type,
            command=command,
            arguments=arguments,
            agent_id=agent_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        
        # Convert sets to lists for JSON serialization
        data['dependencies'] = list(self.dependencies)
        data['dependents'] = list(self.dependents)
        
        # Convert enums to strings
        data['status'] = self.status.value
        data['node_type'] = self.node_type.value
        
        # Convert datetime to ISO format
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
            
        return data
    
    def is_ready_to_execute(self, completed_nodes: Set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        if self.status != NodeStatus.PENDING:
            return False
            
        # All dependencies must be completed
        return self.dependencies.issubset(completed_nodes)
    
    def can_retry(self) -> bool:
        """Check if node can be retried."""
        return (
            self.status == NodeStatus.FAILED and 
            self.retry_count < self.max_retries
        )


@dataclass 
class WorkflowEdge:
    """
    Edge connecting two workflow nodes.
    
    Represents dependency relationships and data flow between nodes.
    """
    
    id: str
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType = EdgeType.SEQUENCE
    
    # Conditional execution
    condition: Optional[str] = None  # Condition expression for conditional edges
    
    # Data passing
    data_mapping: Dict[str, str] = field(default_factory=dict)  # source_field -> target_field
    
    # Visual representation
    ui_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['edge_type'] = self.edge_type.value
        return data


@dataclass
class ExecutionContext:
    """
    Context for workflow execution.
    
    Contains shared data, configuration, and state across all nodes.
    """
    
    workflow_id: str
    execution_id: str
    user_id: Optional[str] = None
    
    # Shared data store for passing data between nodes
    shared_data: Dict[str, Any] = field(default_factory=dict)
    
    # Execution configuration
    max_parallel_nodes: int = 5
    global_timeout_seconds: int = 1800  # 30 minutes
    enable_retry: bool = True
    
    # Progress tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Agent selection preferences
    preferred_agents: List[str] = field(default_factory=list)
    avoid_agents: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
            
        return data


@dataclass
class WorkflowGraph:
    """
    Complete workflow graph definition.
    
    Contains all nodes, edges, and metadata for workflow execution.
    """
    
    id: str
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    
    # Graph structure
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    edges: List[WorkflowEdge] = field(default_factory=list)
    
    # Execution metadata
    execution_context: Optional[ExecutionContext] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Visual layout
    layout: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_ast_nodes(
        cls,
        ast_nodes: List[ASTNode],
        workflow_id: Optional[str] = None,
        name: Optional[str] = None
    ) -> "WorkflowGraph":
        """Create WorkflowGraph from list of DSL AST nodes."""
        
        workflow_id = workflow_id or str(uuid.uuid4())
        name = name or f"workflow_{workflow_id[:8]}"
        
        graph = cls(id=workflow_id, name=name)
        
        # Convert AST nodes to workflow nodes
        node_stack: List[WorkflowNode] = []
        current_parallel_group: List[str] = []
        
        for i, ast_node in enumerate(ast_nodes):
            node_id = str(uuid.uuid4())
            workflow_node = WorkflowNode.from_ast_node(ast_node, node_id)
            
            # Handle different node types
            if ast_node.type == NodeType.PARALLEL:
                # Start parallel group
                current_parallel_group = []
                continue
                
            elif ast_node.type == NodeType.SEQUENCE:
                # End parallel group, start sequential
                current_parallel_group = []
                continue
                
            elif ast_node.type in [NodeType.CALL, NodeType.COMMAND]:
                # Regular executable node
                graph.nodes[node_id] = workflow_node
                
                if current_parallel_group:
                    # Add to parallel group
                    current_parallel_group.append(node_id)
                elif node_stack:
                    # Sequential dependency on previous node
                    prev_node = node_stack[-1]
                    workflow_node.dependencies.add(prev_node.id)
                    prev_node.dependents.add(node_id)
                
                node_stack.append(workflow_node)
        
        # Create edges from dependencies
        graph._create_edges_from_dependencies()
        
        return graph
    
    def _create_edges_from_dependencies(self):
        """Create edges based on node dependencies."""
        
        for node in self.nodes.values():
            for dep_id in node.dependencies:
                edge_id = f"{dep_id}_{node.id}"
                edge = WorkflowEdge(
                    id=edge_id,
                    source_node_id=dep_id,
                    target_node_id=node.id,
                    edge_type=EdgeType.SEQUENCE
                )
                self.edges.append(edge)
    
    def get_ready_nodes(self, completed_nodes: Set[str]) -> List[WorkflowNode]:
        """Get nodes that are ready to execute."""
        ready_nodes = []
        
        for node in self.nodes.values():
            if node.is_ready_to_execute(completed_nodes):
                ready_nodes.append(node)
        
        return ready_nodes
    
    def get_node_dependencies(self, node_id: str) -> Set[str]:
        """Get all dependencies for a node."""
        if node_id not in self.nodes:
            return set()
            
        return self.nodes[node_id].dependencies.copy()
    
    def validate_graph(self) -> List[str]:
        """Validate graph structure and return list of issues."""
        issues = []
        
        # Check for cycles
        if self._has_cycles():
            issues.append("Graph contains cycles")
        
        # Check for orphaned nodes
        orphaned = self._find_orphaned_nodes()
        if orphaned:
            issues.append(f"Orphaned nodes found: {orphaned}")
        
        # Check edge validity
        for edge in self.edges:
            if edge.source_node_id not in self.nodes:
                issues.append(f"Edge references non-existent source node: {edge.source_node_id}")
            if edge.target_node_id not in self.nodes:
                issues.append(f"Edge references non-existent target node: {edge.target_node_id}")
        
        return issues
    
    def _has_cycles(self) -> bool:
        """Check for cycles using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {node_id: WHITE for node_id in self.nodes}
        
        def dfs(node_id: str) -> bool:
            if colors[node_id] == GRAY:
                return True  # Back edge found - cycle detected
                
            if colors[node_id] == BLACK:
                return False
            
            colors[node_id] = GRAY
            
            for dep_id in self.nodes[node_id].dependents:
                if dfs(dep_id):
                    return True
            
            colors[node_id] = BLACK
            return False
        
        for node_id in self.nodes:
            if colors[node_id] == WHITE:
                if dfs(node_id):
                    return True
        
        return False
    
    def _find_orphaned_nodes(self) -> List[str]:
        """Find nodes with no dependencies and no dependents."""
        orphaned = []
        
        for node_id, node in self.nodes.items():
            if not node.dependencies and not node.dependents and len(self.nodes) > 1:
                orphaned.append(node_id)
        
        return orphaned
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
            "execution_context": self.execution_context.to_dict() if self.execution_context else None,
            "created_at": self.created_at.isoformat(),
            "layout": self.layout
        }


@dataclass
class NodeResult:
    """Result of executing a single node."""
    
    node_id: str
    status: NodeStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    agent_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
            
        return data


@dataclass
class WorkflowResult:
    """Result of executing an entire workflow."""
    
    workflow_id: str
    execution_id: str
    status: str  # "completed", "failed", "cancelled"
    
    # Node results
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    
    # Overall metrics
    total_execution_time: Optional[float] = None
    nodes_completed: int = 0
    nodes_failed: int = 0
    nodes_skipped: int = 0
    
    # Final result data
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_summary: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        
        # Convert node results
        data['node_results'] = {
            node_id: result.to_dict() 
            for node_id, result in self.node_results.items()
        }
        
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
            
        return data


@dataclass
class ProgressUpdate:
    """Real-time progress update for workflow execution."""
    
    workflow_id: str
    execution_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Progress information
    update_type: str = "node_status"  # "node_status", "workflow_status", "error", "log"
    node_id: Optional[str] = None
    
    # Status updates
    old_status: Optional[NodeStatus] = None
    new_status: Optional[NodeStatus] = None
    
    # Message and data
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Progress metrics
    progress_percentage: Optional[float] = None
    estimated_remaining_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for WebSocket transmission."""
        data = {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat() + "Z",
            "update_type": self.update_type,
            "message": self.message,
            "data": self.data.copy()
        }
        
        if self.node_id:
            data["node_id"] = self.node_id
        
        if self.old_status:
            data["old_status"] = self.old_status.value
        if self.new_status:
            data["new_status"] = self.new_status.value
            
        if self.progress_percentage is not None:
            data["progress_percentage"] = self.progress_percentage
        if self.estimated_remaining_time is not None:
            data["estimated_remaining_time"] = self.estimated_remaining_time
            
        return data
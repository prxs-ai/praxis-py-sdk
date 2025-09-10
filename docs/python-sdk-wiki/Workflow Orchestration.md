# Workflow Orchestration



## Table of Contents
1. [Introduction](#introduction)
2. [DSL Processing Pipeline](#dsl-processing-pipeline)
3. [AST Structure and Node Types](#ast-structure-and-node-types)
4. [Graph Orchestration System](#graph-orchestration-system)
5. [Node Execution and P2P Delegation](#node-execution-and-p2p-delegation)
6. [Workflow Execution Flow](#workflow-execution-flow)
7. [Conditional Logic and Control Flow](#conditional-logic-and-control-flow)
8. [Error Handling and Retry Mechanisms](#error-handling-and-retry-mechanisms)
9. [Performance Monitoring and Statistics](#performance-monitoring-and-statistics)
10. [Integration with LLM Planning](#integration-with-llm-planning)

## Introduction
The workflow orchestration system provides a comprehensive framework for executing complex workflows using both domain-specific language (DSL) and graph-based execution models. The system enables users to define workflows through a structured DSL syntax that is parsed into an Abstract Syntax Tree (AST), which is then transformed into an executable graph structure. This document details the architecture, components, and functionality of the orchestration system, focusing on the DSL parser, AST builder, graph orchestrator, and node executor components. The system supports advanced features including parallel execution, conditional branching, error recovery, and distributed task delegation through peer-to-peer (P2P) networks.

## DSL Processing Pipeline

The DSL processing pipeline transforms human-readable workflow definitions into executable structures through a multi-stage process. This pipeline begins with tokenization of the DSL text, followed by AST construction, validation, and finally execution. The `AdvancedDSLParser` class serves as the central component that coordinates these stages, providing a unified interface for parsing and executing DSL commands.

```mermaid
flowchart TD
A["DSL Text Input"] --> B["Tokenization"]
B --> C["AST Construction"]
C --> D["Validation"]
D --> E["Execution"]
E --> F["Execution Result"]
subgraph "Parser Components"
B
C
D
E
end
style A fill:#f9f,stroke:#333
style F fill:#f9f,stroke:#333
```

**Diagram sources**
- [parser.py](file://src/praxis_sdk/dsl/parser.py#L1-L100)

**Section sources**
- [parser.py](file://src/praxis_sdk/dsl/parser.py#L1-L100)

## AST Structure and Node Types

The Abstract Syntax Tree (AST) serves as the intermediate representation of DSL commands, capturing the hierarchical structure and semantic meaning of workflow definitions. The AST is composed of nodes that represent different types of operations and control structures. Each node contains metadata about its type, value, arguments, and child nodes for composite structures.

```mermaid
classDiagram
class AST {
+nodes : List[ASTNode]
+metadata : Dict[str, Any]
+created_at : datetime
+to_dict() Dict[str, Any]
+from_dict(data) AST
}
class ASTNode {
+type : NodeType
+value : str
+tool_name : Optional[str]
+args : Dict[str, Any]
+children : List[ASTNode]
+metadata : Dict[str, Any]
+to_dict() Dict[str, Any]
+from_dict(data) ASTNode
}
class NodeType {
<<enumeration>>
COMMAND
WORKFLOW
TASK
AGENT
CALL
PARALLEL
SEQUENCE
CONDITIONAL
}
class Token {
+type : TokenType
+value : str
+args : List[str]
}
class TokenType {
<<enumeration>>
COMMAND
OPERATOR
VALUE
}
AST "1" *-- "0..*" ASTNode : contains
ASTNode "1" *-- "0..*" ASTNode : children
```

**Diagram sources**
- [types.py](file://src/praxis_sdk/dsl/types.py#L1-L100)

**Section sources**
- [types.py](file://src/praxis_sdk/dsl/types.py#L1-L100)

## Graph Orchestration System

The graph orchestration system manages the execution of workflows represented as directed acyclic graphs (DAGs). The `GraphOrchestrator` class coordinates the execution of nodes according to their dependencies, handling parallel and sequential execution patterns while providing real-time progress tracking and error recovery capabilities.

```mermaid
classDiagram
class GraphOrchestrator {
+agent : Agent
+dsl_orchestrator : DSLOrchestrator
+max_parallel_nodes : int
+execution_timeout : int
+node_executor : NodeExecutor
+progress_tracker : ProgressTracker
+error_recovery : ErrorRecovery
+active_executions : Dict[str, WorkflowGraph]
+execution_tasks : Dict[str, asyncio.Task]
+execution_stats : Dict[str, Any]
+create_from_ast(ast_nodes, workflow_id, context) WorkflowGraph
+execute_workflow(workflow, track_progress) WorkflowResult
+cancel_execution(execution_id) bool
+get_execution_status(execution_id) Dict[str, Any]
+get_stats() Dict[str, Any]
}
class WorkflowGraph {
+id : str
+name : str
+description : Optional[str]
+version : str
+nodes : Dict[str, WorkflowNode]
+edges : List[WorkflowEdge]
+execution_context : Optional[ExecutionContext]
+created_at : datetime
+layout : Dict[str, Any]
+from_ast_nodes(ast_nodes, workflow_id, name) WorkflowGraph
+_create_edges_from_dependencies() void
+get_ready_nodes(completed_nodes) List[WorkflowNode]
+get_node_dependencies(node_id) Set[str]
+validate_graph() List[str]
+to_dict() Dict[str, Any]
}
class WorkflowNode {
+id : str
+name : str
+node_type : NodeType
+command : str
+arguments : Dict[str, Any]
+status : NodeStatus
+agent_id : Optional[str]
+execution_time : Optional[float]
+retry_count : int
+max_retries : int
+dependencies : Set[str]
+dependents : Set[str]
+result : Optional[Any]
+error : Optional[str]
+started_at : Optional[datetime]
+completed_at : Optional[datetime]
+timeout_seconds : int
+position : Dict[str, float]
+ui_data : Dict[str, Any]
+from_ast_node(ast_node, node_id, agent_id) WorkflowNode
+to_dict() Dict[str, Any]
+is_ready_to_execute(completed_nodes) bool
+can_retry() bool
}
class WorkflowEdge {
+id : str
+source_node_id : str
+target_node_id : str
+edge_type : EdgeType
+condition : Optional[str]
+data_mapping : Dict[str, str]
+ui_data : Dict[str, Any]
+to_dict() Dict[str, Any]
}
GraphOrchestrator --> WorkflowGraph : creates
GraphOrchestrator --> WorkflowNode : executes
WorkflowGraph "1" *-- "0..*" WorkflowNode : contains
WorkflowGraph "1" *-- "0..*" WorkflowEdge : contains
WorkflowNode "1" --> "0..*" WorkflowNode : depends on
```

**Diagram sources**
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L100)
- [models.py](file://src/praxis_sdk/workflow/models.py#L1-L100)

**Section sources**
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L100)
- [models.py](file://src/praxis_sdk/workflow/models.py#L1-L100)

## Node Execution and P2P Delegation

The node execution system handles the actual execution of individual workflow nodes, supporting both local execution and remote delegation through P2P networks. The `NodeExecutor` class determines the appropriate execution strategy based on the node configuration and agent availability, implementing retry logic and error recovery mechanisms.

```mermaid
sequenceDiagram
participant NodeExecutor
participant LocalExecution
participant RemoteExecution
participant P2PService
participant MCPService
NodeExecutor->>NodeExecutor : execute_node(node, context)
alt Local Execution
NodeExecutor->>LocalExecution : _execute_local_node()
LocalExecution->>MCPService : call_tool(command, arguments)
MCPService-->>LocalExecution : result
LocalExecution-->>NodeExecutor : processed result
else Remote Execution
NodeExecutor->>RemoteExecution : _execute_remote_node()
RemoteExecution->>P2PService : call_remote_tool(agent_id, arguments)
P2PService->>RemoteAgent : execute_workflow_node()
RemoteAgent-->>P2PService : execution result
P2PService-->>RemoteExecution : result
RemoteExecution-->>NodeExecutor : processed result
end
NodeExecutor-->>Caller : NodeResult
```

**Diagram sources**
- [node_executor.py](file://src/praxis_sdk/workflow/node_executor.py#L1-L100)

**Section sources**
- [node_executor.py](file://src/praxis_sdk/workflow/node_executor.py#L1-L100)

## Workflow Execution Flow

The workflow execution flow illustrates the complete process from DSL input to final execution result. This flow encompasses the transformation of DSL text into an executable graph, the orchestration of node execution according to dependencies, and the collection of results with comprehensive error handling.

```mermaid
flowchart TD
A["DSL Text"] --> B["Tokenization"]
B --> C["AST Construction"]
C --> D["Graph Creation"]
D --> E["Execution Planning"]
E --> F["Ready Nodes"]
F --> G["Execute Nodes"]
G --> H["Update Status"]
H --> I["Check Completion"]
I --> J{"All Nodes<br/>Processed?"}
J --> |No| F
J --> |Yes| K["Finalize Result"]
subgraph "Execution Loop"
F
G
H
I
J
end
style A fill:#f9f,stroke:#333
style K fill:#f9f,stroke:#333
```

**Diagram sources**
- [parser.py](file://src/praxis_sdk/dsl/parser.py#L1-L100)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L100)

**Section sources**
- [parser.py](file://src/praxis_sdk/dsl/parser.py#L1-L100)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L100)

## Conditional Logic and Control Flow

The system supports conditional logic through the CONDITIONAL node type, enabling workflows to make decisions based on runtime conditions. The AST builder parses IF/ELSE constructs into conditional nodes that contain separate branches for different execution paths.

```mermaid
flowchart TD
A["IF condition"] --> B{"Condition<br/>True?"}
B --> |Yes| C["Execute IF branch"]
B --> |No| D["Execute ELSE branch"]
C --> E["Continue workflow"]
D --> E
E --> F["Next node"]
style A fill:#ff7,stroke:#333
style C fill:#ff7,stroke:#333
style D fill:#ff7,stroke:#333
```

**Diagram sources**
- [ast_builder.py](file://src/praxis_sdk/dsl/ast_builder.py#L1-L100)

**Section sources**
- [ast_builder.py](file://src/praxis_sdk/dsl/ast_builder.py#L1-L100)

## Error Handling and Retry Mechanisms

The orchestration system implements comprehensive error handling and retry mechanisms to ensure robust workflow execution. Each component includes specific error handling strategies, with the node executor implementing retry logic for transient failures and the graph orchestrator managing workflow-level error recovery.

```mermaid
flowchart TD
A["Node Execution"] --> B{"Success?"}
B --> |Yes| C["Complete Node"]
B --> |No| D["Increment Retry Count"]
D --> E{"Retry Limit<br/>Reached?"}
E --> |No| F["Apply Backoff Delay"]
F --> G["Retry Execution"]
G --> B
E --> |Yes| H["Mark as Failed"]
H --> I["Update Workflow Status"]
style A fill:#f9f,stroke:#333
style C fill:#9f9,stroke:#333
style H fill:#f99,stroke:#333
```

**Diagram sources**
- [node_executor.py](file://src/praxis_sdk/workflow/node_executor.py#L1-L100)

**Section sources**
- [node_executor.py](file://src/praxis_sdk/workflow/node_executor.py#L1-L100)

## Performance Monitoring and Statistics

The system includes comprehensive performance monitoring and statistics collection across all components. The parser, orchestrator, and executor components track execution metrics such as processing time, cache hit rates, and success/failure rates, providing insights into workflow performance and system efficiency.

```mermaid
classDiagram
class PerformanceMetrics {
+commands_processed : int
+cache_hits : int
+cache_misses : int
+total_execution_time : float
+avg_execution_time : float
+cache_hit_rate : float
}
class ExecutionStats {
+total_executions : int
+successful_executions : int
+failed_executions : int
+average_execution_time : float
+total_nodes_executed : int
+parallel_efficiency : float
}
class NodeExecutionStats {
+total_executions : int
+successful_executions : int
+failed_executions : int
+retried_executions : int
+remote_executions : int
+local_executions : int
+average_execution_time : float
+success_rate : float
+failure_rate : float
+retry_rate : float
+remote_execution_rate : float
}
PerformanceMetrics <|-- ExecutionStats
PerformanceMetrics <|-- NodeExecutionStats
```

**Diagram sources**
- [parser.py](file://src/praxis_sdk/dsl/parser.py#L1-L100)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L100)
- [node_executor.py](file://src/praxis_sdk/workflow/node_executor.py#L1-L100)

**Section sources**
- [parser.py](file://src/praxis_sdk/dsl/parser.py#L1-L100)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L100)
- [node_executor.py](file://src/praxis_sdk/workflow/node_executor.py#L1-L100)

## Integration with LLM Planning

The workflow orchestration system integrates with LLM-based planning capabilities, allowing natural language requests to be transformed into executable workflows. The `AdvancedDSLParser` includes functionality to generate workflow plans from natural language input by leveraging a task planner component.

```mermaid
sequenceDiagram
participant User
participant DSLParser
participant TaskPlanner
participant NetworkContext
User->>DSLParser : generate_workflow_from_natural_language(request)
DSLParser->>TaskPlanner : generate_workflow_from_natural_language(request, context)
TaskPlanner->>TaskPlanner : Analyze request
TaskPlanner->>TaskPlanner : Identify required tools
TaskPlanner->>TaskPlanner : Plan execution sequence
TaskPlanner-->>DSLParser : WorkflowPlan
DSLParser-->>User : Optional[WorkflowPlan]
```

**Diagram sources**
- [parser.py](file://src/praxis_sdk/dsl/parser.py#L1-L100)

**Section sources**
- [parser.py](file://src/praxis_sdk/dsl/parser.py#L1-L100)

**Referenced Files in This Document**   
- [parser.py](file://src/praxis_sdk/dsl/parser.py)
- [ast_builder.py](file://src/praxis_sdk/dsl/ast_builder.py)
- [types.py](file://src/praxis_sdk/dsl/types.py)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py)
- [node_executor.py](file://src/praxis_sdk/workflow/node_executor.py)
- [models.py](file://src/praxis_sdk/workflow/models.py)
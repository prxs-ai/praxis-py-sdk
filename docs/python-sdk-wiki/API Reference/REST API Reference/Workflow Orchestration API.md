# Workflow Orchestration API



## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
The Workflow Orchestration API provides a comprehensive system for managing and executing DSL-based workflows through a RESTful interface. This documentation details the API endpoints under `/api/workflow`, the workflow lifecycle, integration with the LLM planner and DSL orchestrator, and practical usage examples. The system enables users to create, execute, monitor, and manage complex workflows through both direct API calls and natural language processing.

## Project Structure
The project follows a modular structure with clear separation of concerns. The core workflow orchestration components are located in the `src/praxis_sdk` directory, with specific modules for API handling, DSL processing, workflow modeling, and execution orchestration.

```mermaid
graph TD
subgraph "API Layer"
A[workflow_handlers.py]
end
subgraph "DSL Processing"
B[orchestrator.py]
C[parser.py]
D[validator.py]
end
subgraph "Workflow Modeling"
E[models.py]
F[graph_orchestrator.py]
G[node_executor.py]
end
subgraph "LLM Integration"
H[workflow_planner.py]
I[openai_client.py]
end
A --> B
B --> H
H --> E
E --> F
F --> B
```

**Diagram sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py)
- [models.py](file://src/praxis_sdk/workflow/models.py)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py)

**Section sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py)

## Core Components

The Workflow Orchestration API consists of several interconnected components that work together to provide a complete workflow management system. The core components include the API handlers that expose the REST endpoints, the workflow models that define the data structures, the graph orchestrator that manages execution, and the LLM-based planner that converts natural language to executable workflows.

**Section sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py#L1-L581)
- [models.py](file://src/praxis_sdk/workflow/models.py#L1-L512)

## Architecture Overview

The architecture follows a layered approach with clear separation between the API interface, workflow modeling, execution engine, and AI integration components. The system is designed to handle both simple DSL commands and complex multi-step workflows generated from natural language requests.

```mermaid
graph TD
Client[Client Application]
API[Workflow API Handlers]
Planner[LLM Workflow Planner]
Orchestrator[DSL Orchestrator]
Graph[Graph Orchestrator]
Executor[Node Executor]
Tools[External Tools]
Client --> API
API --> Planner
API --> Graph
Planner --> Orchestrator
Orchestrator --> Graph
Graph --> Executor
Executor --> Tools
Executor --> Orchestrator
Graph --> API
subgraph "AI Layer"
Planner
Orchestrator
end
subgraph "Execution Layer"
Graph
Executor
end
```

**Diagram sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py#L1-L581)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L654)

## Detailed Component Analysis

### API Handlers Analysis
The `workflow_handlers.py` module provides FastAPI handlers for the `/api/workflow/*` endpoints, ensuring compatibility with the frontend's API client expectations. It handles all CRUD operations for workflows and provides real-time status updates.

#### For API/Service Components:
```mermaid
sequenceDiagram
participant Client as "Client"
participant Handlers as "WorkflowHandlers"
participant State as "WorkflowState"
participant EventBus as "EventBus"
Client->>Handlers : POST /api/workflow/execute
Handlers->>State : create_execution()
Handlers->>EventBus : publish(TASK_STARTED)
Handlers->>Handlers : add_task(_execute_workflow_async)
Handlers-->>Client : WorkflowExecutionResponse
loop Background Execution
Handlers->>State : update_execution() - progress
Handlers->>EventBus : publish(TASK_PROGRESS)
Handlers->>State : complete_execution()
Handlers->>EventBus : publish(TASK_COMPLETED)
end
```

**Diagram sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py#L1-L581)

**Section sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py#L1-L581)

### Workflow Models Analysis
The `models.py` file defines the core data structures for workflow orchestration using Python dataclasses. These models represent nodes, edges, execution contexts, and results in a workflow graph.

#### For Object-Oriented Components:
```mermaid
classDiagram
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
class ExecutionContext {
+workflow_id : str
+execution_id : str
+user_id : Optional[str]
+shared_data : Dict[str, Any]
+max_parallel_nodes : int
+global_timeout_seconds : int
+enable_retry : bool
+started_at : Optional[datetime]
+completed_at : Optional[datetime]
+preferred_agents : List[str]
+avoid_agents : List[str]
+to_dict() Dict[str, Any]
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
+_has_cycles() bool
+_find_orphaned_nodes() List[str]
+to_dict() Dict[str, Any]
}
class WorkflowResult {
+workflow_id : str
+execution_id : str
+status : str
+node_results : Dict[str, NodeResult]
+total_execution_time : Optional[float]
+nodes_completed : int
+nodes_failed : int
+nodes_skipped : int
+output_data : Dict[str, Any]
+error_summary : Optional[str]
+started_at : Optional[datetime]
+completed_at : Optional[datetime]
+to_dict() Dict[str, Any]
}
class ProgressUpdate {
+workflow_id : str
+execution_id : str
+timestamp : datetime
+update_type : str
+node_id : Optional[str]
+old_status : Optional[NodeStatus]
+new_status : Optional[NodeStatus]
+message : str
+data : Dict[str, Any]
+progress_percentage : Optional[float]
+estimated_remaining_time : Optional[float]
+to_dict() Dict[str, Any]
}
WorkflowGraph --> WorkflowNode : "contains"
WorkflowGraph --> WorkflowEdge : "contains"
WorkflowResult --> NodeResult : "contains"
ProgressUpdate --> NodeStatus : "references"
```

**Diagram sources**
- [models.py](file://src/praxis_sdk/workflow/models.py#L1-L512)

**Section sources**
- [models.py](file://src/praxis_sdk/workflow/models.py#L1-L512)

### Graph Orchestrator Analysis
The `graph_orchestrator.py` module is the main execution engine for visual workflows, providing parallel and sequential node execution, real-time progress tracking, and error recovery mechanisms.

#### For Complex Logic Components:
```mermaid
flowchart TD
Start([Execute Workflow]) --> ValidateInput["Validate Input Parameters"]
ValidateInput --> InputValid{"Input Valid?"}
InputValid --> |No| ReturnError["Return Error Response"]
InputValid --> |Yes| InitializeExecution["Initialize Execution Tracking"]
InitializeExecution --> CheckReadyNodes["Get Ready Nodes"]
CheckReadyNodes --> ReadyNodes{"Nodes Ready?"}
ReadyNodes --> |No| CheckCompletion["Check Completion"]
ReadyNodes --> |Yes| StartNodes["Start New Node Executions"]
StartNodes --> WaitCompletion["Wait for Node Completion"]
WaitCompletion --> ProcessResults["Process Completed Nodes"]
ProcessResults --> UpdateTracking["Update Execution Tracking"]
UpdateTracking --> CheckCompletion
CheckCompletion --> AllProcessed{"All Nodes Processed?"}
AllProcessed --> |No| CheckStuck["Check if Stuck?"]
CheckStuck --> |Yes| ReturnError
CheckStuck --> |No| CheckReadyNodes
AllProcessed --> |Yes| DetermineStatus["Determine Final Status"]
DetermineStatus --> Cleanup["Cleanup Resources"]
Cleanup --> ReturnResult["Return Workflow Result"]
ReturnResult --> End([Function Exit])
ReturnError --> End
```

**Diagram sources**
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L654)

**Section sources**
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L654)

### LLM Workflow Planner Analysis
The `workflow_planner.py` module serves as the intelligent workflow generator that converts natural language requests into executable workflows using LLM technology.

#### For API/Service Components:
```mermaid
sequenceDiagram
participant User as "User"
participant Planner as "WorkflowPlanner"
participant Context as "NetworkContextBuilder"
participant LLM as "LLM Client"
participant Optimizer as "PlanOptimizer"
participant Orchestrator as "DSLOrchestrator"
User->>Planner : generate_from_natural_language()
Planner->>Context : build_network_context()
Context-->>Planner : NetworkContext
Planner->>LLM : generate_workflow_from_natural_language()
LLM-->>Planner : WorkflowPlan
Planner->>Optimizer : validate_workflow_plan()
Optimizer-->>Planner : validation_issues
Planner->>Optimizer : optimize_workflow_plan()
Optimizer-->>Planner : optimized_plan
Planner->>Optimizer : create_execution_plan()
Optimizer-->>Planner : execution_plan
Planner-->>User : PlanningResult
```

**Diagram sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)

**Section sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)

### DSL Orchestrator Analysis
The `orchestrator.py` module provides enhanced DSL command orchestration with Advanced DSL Processing Engine integration, supporting both simple DSL commands and natural language processing with LLM.

#### For Complex Logic Components:
```mermaid
flowchart TD
Start([Execute Command]) --> LLMOrchestration["LLM Orchestration"]
LLMOrchestration --> DiscoverAgents["Discover P2P Agents"]
DiscoverAgents --> BuildContext["Build Agent Context"]
BuildContext --> GetTools["Get Available Tools"]
GetTools --> ConvertFunctions["Convert Tools to Functions"]
ConvertFunctions --> CallLLM["Call LLM with Function Calling"]
CallLLM --> ProcessResponse["Process LLM Response"]
ProcessResponse --> ExecuteTools["Execute Tools via P2P"]
ExecuteTools --> CollectResults["Collect Tool Results"]
CollectResults --> FinalResponse["Get Final LLM Response"]
FinalResponse --> ReturnResult["Return Result"]
ReturnResult --> End([Function Exit])
style Start fill:#f9f,stroke:#333
style End fill:#f9f,stroke:#333
```

**Diagram sources**
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)

**Section sources**
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)

## Dependency Analysis

The Workflow Orchestration API components have a well-defined dependency structure that enables modularity and separation of concerns. The API handlers depend on the workflow state management, which in turn integrates with the graph orchestrator for execution. The LLM workflow planner generates plans that are executed by the DSL orchestrator, creating a cohesive system for natural language to executable workflow conversion.

```mermaid
graph TD
A[workflow_handlers.py] --> B[WorkflowState]
A --> C[EventBus]
D[graph_orchestrator.py] --> E[WorkflowGraph]
D --> F[NodeExecutor]
D --> C
G[workflow_planner.py] --> H[NetworkContextBuilder]
G --> I[PlanOptimizer]
G --> J[DSLOrchestrator]
K[orchestrator.py] --> L[AsyncOpenAI]
K --> C
F --> K
J --> K
A --> D
G --> D
```

**Diagram sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py#L1-L581)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L654)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)

**Section sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py#L1-L581)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L654)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)

## Performance Considerations

The Workflow Orchestration API is designed with performance in mind, particularly for handling long-running workflows and real-time progress updates. The system uses asynchronous execution with background tasks to prevent blocking the main API thread. The graph orchestrator limits parallel execution to prevent resource exhaustion, with a default maximum of 5 parallel nodes.

For large workflows, the system provides estimated duration calculations based on node count (10 seconds per node with a minimum of 30 seconds). The event-driven architecture using the EventBus pattern enables efficient real-time updates without polling, reducing network overhead.

Caching mechanisms are implemented in the DSL orchestrator to avoid redundant LLM calls for similar commands. The workflow state is maintained in memory for active executions, providing fast access to status information.

## Troubleshooting Guide

When encountering issues with the Workflow Orchestration API, consider the following common problems and solutions:

**Section sources**
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py#L1-L581)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py#L1-L654)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)

### Common Issues

1. **Workflow execution timeout**: Workflows have a default timeout of 1800 seconds (30 minutes). For longer workflows, increase the `execution_timeout` parameter in the GraphOrchestrator initialization.

2. **LLM orchestration failures**: Ensure the OpenAI API key is properly configured in the environment variables or configuration file. Check the LLM service availability and rate limits.

3. **Node execution errors**: Verify that the required tools are available and properly registered in the tool registry. Check the agent's capabilities and P2P connectivity.

4. **Progress updates not received**: Confirm that the WebSocket connection is established and the EventBus is properly configured to broadcast events.

5. **Workflow validation errors**: Check for cycles in the workflow graph or orphaned nodes without dependencies. Ensure all edge references point to existing nodes.

### Debugging Tips

- Enable debug logging to trace the workflow execution path
- Use the `list_workflows` endpoint to inspect the state of active workflows
- Check the `get_workflow_status` response for detailed node-level information
- Monitor the EventBus for published events to verify progress updates
- Validate workflow definitions using the `validate_graph()` method before execution

## Conclusion

The Workflow Orchestration API provides a robust and flexible system for managing complex workflows through both programmatic API calls and natural language interaction. The architecture combines RESTful endpoints for direct control with LLM-powered natural language processing for intuitive workflow creation.

Key features include:
- Comprehensive CRUD operations for workflow management
- Real-time progress tracking through event-driven updates
- Support for both sequential and parallel execution
- Integration with LLM for natural language to workflow conversion
- Robust error handling and retry mechanisms
- Scalable architecture suitable for long-running workflows

The system is designed to be extensible, allowing for the addition of new tools, agents, and execution strategies while maintaining a consistent API interface.

**Referenced Files in This Document**   
- [workflow_handlers.py](file://src/praxis_sdk/api/workflow_handlers.py)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py)
- [models.py](file://src/praxis_sdk/workflow/models.py)
- [graph_orchestrator.py](file://src/praxis_sdk/workflow/graph_orchestrator.py)
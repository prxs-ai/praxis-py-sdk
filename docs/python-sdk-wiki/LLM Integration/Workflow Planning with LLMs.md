# Workflow Planning with LLMs



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
This document provides a comprehensive analysis of the LLM-powered workflow planning system in the Praxis Py SDK. The system enables natural language requests to be converted into executable Domain Specific Language (DSL) workflows through intelligent planning, optimization, and orchestration. It leverages large language models (LLMs) for intent understanding, task decomposition, tool selection, and dependency resolution. The architecture integrates with a distributed peer-to-peer (P2P) agent network, allowing dynamic discovery of available tools and agents across the network. This documentation details the implementation of the workflow planner, its interaction with the DSL orchestrator, optimization strategies, error handling, and performance characteristics.

## Project Structure
The project follows a modular structure with clear separation of concerns. The core functionality resides in the `src/praxis_sdk` directory, which contains specialized modules for LLM integration, DSL processing, P2P communication, and workflow execution.

```mermaid
graph TD
subgraph "Core Modules"
A[llm] --> B[workflow_planner]
A --> C[plan_optimizer]
A --> D[openai_client]
A --> E[prompts]
A --> F[context_builder]
G[dsl] --> H[orchestrator]
G --> I[parser]
G --> J[validator]
K[p2p] --> L[service]
K --> M[registry]
end
subgraph "Configuration"
N[configs] --> O[agent1.yaml]
N --> P[agent2.yaml]
N --> Q[orchestrator.yaml]
end
subgraph "Tools"
R[tools] --> S[calculator]
R --> T[file_merger]
R --> U[python_data_processor]
R --> V[text_summarizer]
end
B --> H
C --> B
D --> B
E --> D
F --> B
F --> C
H --> K
H --> M
```

**Diagram sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L200)

**Section sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)

## Core Components
The workflow planning system consists of several interconnected components that work together to convert natural language requests into executable workflows. The main components include the WorkflowPlanner, DSLOrchestrator, PlanOptimizer, OpenAIClient, and ContextBuilder. These components collaborate to handle natural language understanding, network context building, workflow generation, optimization, validation, and execution.

**Section sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L737)
- [openai_client.py](file://src/praxis_sdk/llm/openai_client.py#L1-L480)

## Architecture Overview
The workflow planning system follows a layered architecture that separates concerns and enables extensibility. The system begins with natural language input from the user, which is processed by the WorkflowPlanner. The planner uses the ContextBuilder to gather information about available agents and tools in the network. It then leverages the OpenAIClient to generate a workflow plan using LLM-powered reasoning. The generated plan is optimized and validated by the PlanOptimizer before being executed by the DSLOrchestrator.

```mermaid
graph TB
subgraph "User Interface"
A[User Request] --> B[WorkflowPlanner]
end
subgraph "Planning Layer"
B --> C[ContextBuilder]
C --> D[P2PService]
C --> E[ToolRegistry]
B --> F[OpenAIClient]
F --> G[LLM API]
B --> H[PlanOptimizer]
end
subgraph "Execution Layer"
B --> I[DSLOrchestrator]
I --> J[Execution Engine]
I --> D
I --> E
end
subgraph "Monitoring"
K[Statistics] --> B
L[Network Status] --> C
end
```

**Diagram sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L200)

## Detailed Component Analysis

### Workflow Planner Analysis
The WorkflowPlanner class is the central component responsible for converting natural language requests into executable DSL workflows. It coordinates the entire planning process, from context gathering to plan generation, optimization, and execution.

#### Class Diagram
```mermaid
classDiagram
class WorkflowPlanner {
+p2p_service : P2PService
+mcp_registry : ToolRegistry
+dsl_orchestrator : DSLOrchestrator
+llm_client : WorkflowPlannerClient
+context_builder : NetworkContextBuilder
+plan_optimizer : WorkflowPlanOptimizer
+stats : Dict[str, Any]
+_initialized : bool
+__init__(p2p_service, mcp_registry, dsl_orchestrator, openai_api_key)
+initialize()
+generate_from_natural_language(user_request, user_id, optimization_goals, constraints)
+execute_workflow_plan(workflow_plan, execution_plan)
+get_planning_suggestions(partial_request)
+_generate_with_llm(user_request, network_context)
+_generate_with_fallback(user_request, network_context)
+_update_average_processing_time(processing_time)
+get_network_status()
+get_statistics()
}
class PlanningRequest {
+user_request : str
+user_id : Optional[str]
+priority : str
+context : Optional[Dict[str, Any]]
+optimization_goals : List[OptimizationGoal]
+constraints : Optional[Dict[str, Any]]
+__post_init__()
}
class PlanningResult {
+request_id : str
+success : bool
+workflow_plan : Optional[WorkflowPlan]
+execution_plan : Optional[ExecutionPlan]
+validation_issues : List[Any]
+optimization_applied : bool
+processing_time : float
+error_message : Optional[str]
+fallback_used : bool
+to_dict()
}
WorkflowPlanner --> NetworkContextBuilder : "uses"
WorkflowPlanner --> WorkflowPlanOptimizer : "uses"
WorkflowPlanner --> WorkflowPlannerClient : "uses"
WorkflowPlanner --> DSLOrchestrator : "uses"
WorkflowPlanner --> PlanningResult : "returns"
WorkflowPlanner --> PlanningRequest : "creates"
```

**Diagram sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)

**Section sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)

### Plan Optimizer Analysis
The PlanOptimizer component is responsible for validating, optimizing, and creating execution plans for workflow plans. It ensures that generated workflows are syntactically correct, feasible given the current network context, and optimized for performance, reliability, or cost based on specified goals.

#### Sequence Diagram
```mermaid
sequenceDiagram
participant Planner as "WorkflowPlanner"
participant Optimizer as "WorkflowPlanOptimizer"
participant Context as "NetworkContextBuilder"
participant LLM as "OpenAIClient"
Planner->>Optimizer : validate_workflow_plan(workflow_plan, network_context)
Optimizer->>Context : build_network_context()
Context-->>Optimizer : network_context
Optimizer->>Optimizer : _validate_dsl_syntax(dsl)
Optimizer->>Optimizer : _validate_tool_availability(dsl, network_context)
Optimizer->>Optimizer : _validate_agent_assignments(agents_used, network_context)
Optimizer->>Optimizer : _validate_resource_requirements(dsl, network_context)
Optimizer-->>Planner : validation_issues
Planner->>Optimizer : optimize_workflow_plan(workflow_plan, goal, constraints)
Optimizer->>Context : build_network_context()
Context-->>Optimizer : network_context
Optimizer->>Optimizer : _optimize_for_performance(commands, network_context, constraints)
Optimizer->>Optimizer : _optimize_for_reliability(commands, network_context, constraints)
Optimizer->>Optimizer : _optimize_for_cost(commands, network_context, constraints)
Optimizer->>Optimizer : _calculate_speedup(original_commands, optimized_commands)
Optimizer-->>Planner : OptimizationResult
Planner->>Optimizer : create_execution_plan(workflow_plan, optimization_result)
Optimizer->>Context : build_network_context()
Context-->>Optimizer : network_context
Optimizer->>Optimizer : _parse_dsl(dsl)
Optimizer->>Context : get_agent_recommendations(tool_name, requirements)
Context-->>Optimizer : agent_recommendations
Optimizer->>Optimizer : _estimate_step_duration(tool_name)
Optimizer->>Optimizer : _get_tool_resources(tool_name)
Optimizer-->>Planner : ExecutionPlan
```

**Diagram sources**
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L737)

**Section sources**
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L737)

### Prompt System Analysis
The prompt system provides structured templates for various LLM interactions, ensuring consistent and effective communication with the language model for different planning tasks. The system includes templates for workflow generation, agent selection, plan optimization, and error recovery.

#### Flowchart
```mermaid
flowchart TD
Start([Prompt Template System]) --> DefineTemplates["Define Prompt Templates"]
DefineTemplates --> WorkflowGen["Workflow Generation Template"]
DefineTemplates --> AgentSelect["Agent Selection Template"]
DefineTemplates --> PlanOptimize["Plan Optimization Template"]
DefineTemplates --> ErrorRecovery["Error Recovery Template"]
WorkflowGen --> ContextFields["Context Fields: available_agents, available_tools, user_request"]
AgentSelect --> ContextFields2["Context Fields: agent_details, tool_name, task_priority"]
PlanOptimize --> ContextFields3["Context Fields: original_dsl, optimization_goal, constraints"]
ErrorRecovery --> ContextFields4["Context Fields: error_message, failed_workflow, execution_context"]
Start --> FormatPrompt["format_prompt(template, context)"]
FormatPrompt --> CheckContext["Check for Missing Context Fields"]
CheckContext --> |Missing| Error["Raise ValueError"]
CheckContext --> |Complete| FormatSystem["Format System Prompt"]
FormatSystem --> FormatUser["Format User Prompt"]
FormatUser --> Return["Return Formatted Prompt"]
Return --> UseInLLM["Use in LLM Client"]
UseInLLM --> GenerateResponse["Generate LLM Response"]
GenerateResponse --> ParseResponse["Parse JSON Response"]
ParseResponse --> UseInPlanning["Use in Workflow Planning"]
```

**Diagram sources**
- [prompts.py](file://src/praxis_sdk/llm/prompts.py#L1-L303)

**Section sources**
- [prompts.py](file://src/praxis_sdk/llm/prompts.py#L1-L303)

## Dependency Analysis
The workflow planning system has a well-defined dependency structure that enables modularity and testability. The core dependencies flow from the WorkflowPlanner to supporting components like the ContextBuilder, PlanOptimizer, and OpenAIClient. These components in turn depend on lower-level services like the P2PService and ToolRegistry for network discovery and tool management.

```mermaid
graph TD
A[WorkflowPlanner] --> B[NetworkContextBuilder]
A --> C[WorkflowPlanOptimizer]
A --> D[WorkflowPlannerClient]
A --> E[DSLOrchestrator]
B --> F[P2PService]
B --> G[ToolRegistry]
C --> B
D --> H[AsyncOpenAI]
E --> F
E --> G
I[WorkflowPlannerClient] --> H
J[DSLOrchestrator] --> K[EventBus]
J --> L[PraxisConfig]
```

**Diagram sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L200)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L737)
- [openai_client.py](file://src/praxis_sdk/llm/openai_client.py#L1-L480)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)

**Section sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L200)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L737)

## Performance Considerations
The workflow planning system is designed with performance in mind, balancing the need for intelligent planning with execution efficiency. The system implements several performance optimizations, including caching, fallback mechanisms, and asynchronous processing.

The planning process involves multiple steps that contribute to overall latency: network context building, LLM inference, plan validation, and optimization. The system mitigates these latencies through asynchronous operations and intelligent fallbacks. When the LLM service is unavailable or fails, the system falls back to rule-based planning, ensuring continued operation.

Token usage is optimized by carefully crafting prompt templates that provide sufficient context without unnecessary verbosity. The system also implements retry logic with exponential backoff for failed LLM requests, preventing cascading failures during temporary service disruptions.

The PlanOptimizer analyzes workflows for potential bottlenecks and suggests improvements for performance, reliability, and cost. It estimates execution timelines and resource requirements, helping to prevent overloading of network agents.

```mermaid
flowchart TD
A[User Request] --> B{LLM Available?}
B --> |Yes| C[Generate Plan with LLM]
B --> |No| D[Rule-based Fallback]
C --> E[Validate Plan]
D --> E
E --> F{Critical Errors?}
F --> |Yes| G[Return Error]
F --> |No| H[Optimize Plan]
H --> I[Create Execution Plan]
I --> J[Execute Workflow]
J --> K[Return Result]
style C fill:#e1f5fe,stroke:#039be5
style D fill:#f3e5f5,stroke:#8e24aa
style H fill:#e8f5e8,stroke:#43a047
```

**Diagram sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L737)

## Troubleshooting Guide
The workflow planning system includes comprehensive error handling and troubleshooting capabilities to ensure robust operation in various scenarios.

### Error Handling Strategies
The system handles invalid or ambiguous requests through multiple mechanisms:

1. **Validation**: The PlanOptimizer validates workflow plans for syntax correctness and tool availability, identifying issues before execution.
2. **Fallback Mechanisms**: When LLM-based planning fails, the system falls back to rule-based planning using keyword matching.
3. **Error Recovery**: The system can analyze execution errors and suggest recovery strategies.

Common issues and their solutions:

- **LLM Service Unavailable**: The system automatically falls back to rule-based planning. Ensure the OpenAI API key is configured correctly.
- **Tool Not Available**: The validation process identifies missing tools and suggests alternatives. Verify that required tools are registered in the ToolRegistry.
- **Network Discovery Issues**: The ContextBuilder handles P2P discovery failures by falling back to local tools. Check P2P service connectivity.
- **Syntax Errors in DSL**: The PlanOptimizer detects and reports DSL syntax issues, helping users correct their requests.

### Configuration Options
The planning behavior can be controlled through several configuration options:

- **Planning Depth**: Controlled by the optimization goals parameter, allowing users to specify whether to prioritize performance, reliability, or cost.
- **Creativity**: Influenced by the LLM temperature setting, with lower values producing more deterministic outputs.
- **Tool Constraints**: Users can specify constraints to limit tool selection or execution parameters.

**Section sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L737)
- [openai_client.py](file://src/praxis_sdk/llm/openai_client.py#L1-L480)

## Conclusion
The LLM-powered workflow planning system in the Praxis Py SDK provides a sophisticated framework for converting natural language requests into executable workflows. By leveraging large language models, the system enables users to interact with complex distributed systems using simple, intuitive language. The architecture combines intelligent planning with robust execution, validation, and optimization capabilities.

Key strengths of the system include its modular design, comprehensive error handling, and ability to operate in both connected and degraded modes. The integration with a P2P agent network allows for dynamic discovery of capabilities across distributed systems, enabling flexible and scalable workflow execution.

The system demonstrates a practical application of LLMs in workflow automation, balancing the power of AI with the need for reliability and predictability in production environments. Future enhancements could include support for parallel execution, more sophisticated optimization strategies, and enhanced user feedback mechanisms.

**Referenced Files in This Document**   
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L490)
- [prompts.py](file://src/praxis_sdk/llm/prompts.py#L1-L303)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L737)
- [openai_client.py](file://src/praxis_sdk/llm/openai_client.py#L1-L480)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L200)
- [orchestrator.py](file://src/praxis_sdk/dsl/orchestrator.py#L1-L799)
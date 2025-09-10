# MCP Client



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
The MCP Client is a core component of the Praxis SDK that enables agents to discover and interact with remote MCP servers for accessing external tools. This document provides a comprehensive analysis of the MCP Client functionality, covering client initialization, connection management, capability fetching, caching strategies, retry logic, API for invoking remote tools, integration with third-party servers, orchestration of cross-agent tool usage, integration with the LLM planner for dynamic tool selection, security practices, and performance considerations.

## Project Structure
The MCP Client functionality is organized within the `src/praxis_sdk/mcp` directory, which contains several key modules:

```mermaid
graph TD
mcp[mcp/] --> client[client.py]
mcp --> service[service.py]
mcp --> registry[registry.py]
mcp --> server[server.py]
mcp --> integration[integration.py]
mcp --> tools[tools/]
```

The structure follows a modular design with clear separation of concerns:
- `client.py`: Implements the MCPClient class for connecting to external MCP servers
- `service.py`: Provides a high-level service wrapper for MCP functionality
- `registry.py`: Manages the central registry for all MCP tools
- `server.py`: Implements the MCPServer class for local tool execution
- `integration.py`: Coordinates integration between MCP components and P2P protocols
- `tools/`: Contains specific tool implementations

**Diagram sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)

## Core Components
The MCP Client system consists of several interconnected components that work together to enable tool discovery and execution across distributed agents:

- **MCPClient**: Manages connections to external MCP servers, handles transport protocols, and provides tool discovery and invocation capabilities
- **MCPServer**: Provides local tool execution capabilities and serves as an endpoint for other agents
- **ToolRegistry**: Central registry that manages all available tools, both local and external
- **MCPService**: High-level service wrapper that integrates MCP functionality with HTTP endpoints
- **MCPIntegration**: Coordinates MCP functionality with P2P protocols and event bus

These components work together to create a distributed system where agents can discover and invoke tools across the network, enabling complex workflows that span multiple agents and systems.

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)

## Architecture Overview
The MCP Client architecture is designed to enable seamless tool discovery and execution across distributed agents. The system follows a client-server model where agents can act as both clients (consuming tools from other agents) and servers (providing tools to other agents).

```mermaid
graph TD
subgraph "Local Agent"
MCPClient[MCP Client]
MCPServer[MCPServer]
ToolRegistry[ToolRegistry]
MCPService[MCPService]
MCPIntegration[MCPIntegration]
end
MCPClient --> |Connects to| ExternalServer1[External MCP Server 1]
MCPClient --> |Connects to| ExternalServer2[External MCP Server 2]
MCPClient --> |Discovers tools| ToolRegistry
MCPServer --> |Provides tools| ToolRegistry
MCPService --> |Orchestrates| MCPClient
MCPService --> |Orchestrates| MCPServer
MCPIntegration --> |Integrates| MCPClient
MCPIntegration --> |Integrates| MCPServer
MCPIntegration --> |Communicates via| P2PService[P2P Service]
MCPIntegration --> |Publishes events| EventBus[Event Bus]
```

The architecture enables several key capabilities:
- **Tool Discovery**: Agents can discover tools available on other agents through the MCP protocol
- **Remote Execution**: Tools can be invoked on remote agents as if they were local
- **Dynamic Registration**: Tools can be registered and unregistered at runtime
- **Cross-Agent Orchestration**: Complex workflows can be orchestrated across multiple agents
- **Event-Driven Integration**: The system integrates with an event bus for monitoring and coordination

**Diagram sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)

## Detailed Component Analysis

### MCP Client Analysis
The MCPClient class is responsible for connecting to external MCP servers and managing the communication with them. It supports multiple transport protocols and provides automatic reconnection capabilities.

```mermaid
classDiagram
class MCPClient {
+servers : Dict[str, MCPServerConfig]
+transports : Dict[str, MCPTransport]
+discovered_tools : Dict[str, List[Dict[str, Any]]]
+connection_status : Dict[str, bool]
+reconnect_tasks : Dict[str, bool]
+running : bool
+add_server(config : MCPServerConfig)
+remove_server(name : str)
+start()
+stop()
+_connect_server(server_name : str)
+_create_transport(config : MCPServerConfig) MCPTransport
+_initialize_server(server_name : str, transport : MCPTransport)
+_discover_tools(server_name : str, transport : MCPTransport)
+_monitor_connection(server_name : str)
+_schedule_reconnection(server_name : str)
+call_tool(server_name : str, tool_name : str, arguments : Dict[str, Any]) Dict[str, Any]
+get_available_tools() Dict[str, List[Dict[str, Any]]]
+get_server_status() Dict[str, bool]
+list_resources(server_name : str) List[Dict[str, Any]]
+read_resource(server_name : str, uri : str) Dict[str, Any]
+is_server_connected(server_name : str) bool
+refresh_tools(server_name : str)
}
class MCPServerConfig {
+name : str
+transport_type : str
+endpoint : str
+enabled : bool
+reconnect_interval : int
+max_retries : int
}
class MCPTransport {
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close()
}
class HTTPTransport {
+endpoint : str
+client : httpx.AsyncClient
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close()
}
class SSETransport {
+endpoint : str
+client : httpx.AsyncClient
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close()
}
class SubprocessTransport {
+command : List[str]
+cwd : Optional[str]
+process : Optional[Process]
+stdin_stream : Optional[StreamWriter]
+stdout_stream : Optional[StreamReader]
+start()
+send_request(method : str, params : Dict[str, Any]) Dict[str, Any]
+close()
}
MCPClient --> MCPServerConfig : "uses"
MCPClient --> MCPTransport : "uses"
MCPTransport <|-- HTTPTransport : "implements"
MCPTransport <|-- SSETransport : "implements"
MCPTransport <|-- SubprocessTransport : "implements"
```

**Diagram sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L1-L392)

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L1-L392)

#### Client Initialization and Connection Management
The MCPClient follows a structured initialization and connection management process:

```mermaid
sequenceDiagram
participant Client as "MCPClient"
participant Config as "Configuration"
participant Transport as "MCPTransport"
participant Server as "MCP Server"
Client->>Config : add_server(config)
loop For each server
Config->>Client : Store server configuration
end
Client->>Client : start()
loop For each enabled server
Client->>Client : _connect_server(server_name)
Client->>Client : _create_transport(config)
alt HTTP Transport
Client->>HTTPTransport : Create with endpoint
else SSE Transport
Client->>SSETransport : Create with endpoint
else Subprocess Transport
Client->>SubprocessTransport : Create with command
SubprocessTransport->>SubprocessTransport : start()
end
Client->>Client : _initialize_server()
Client->>Transport : send_request("initialize")
Transport->>Server : POST /jsonrpc
Server-->>Transport : 200 OK
Transport-->>Client : Response
Client->>Client : _discover_tools()
Client->>Transport : send_request("tools/list")
Transport->>Server : POST /jsonrpc
Server-->>Transport : 200 OK
Transport-->>Client : Tool list
Client->>Client : Update discovered_tools
Client->>Client : _monitor_connection()
end
```

The client initialization process involves:
1. Adding server configurations via `add_server()`
2. Starting the client with `start()`
3. Connecting to each enabled server
4. Creating the appropriate transport based on configuration
5. Initializing the connection with the server
6. Discovering available tools
7. Starting connection monitoring

**Diagram sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L1-L392)

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L1-L392)

#### Tool Discovery and Capability Fetching
The MCPClient implements a robust tool discovery mechanism that fetches capabilities from remote servers:

```mermaid
flowchart TD
Start([Start]) --> DiscoverTools["_discover_tools(server_name, transport)"]
DiscoverTools --> SendRequest["Send tools/list request"]
SendRequest --> CheckResponse{"Response has error?"}
CheckResponse --> |Yes| LogError["Log error and return"]
CheckResponse --> |No| ExtractTools["Extract tools from response"]
ExtractTools --> StoreTools["Store in discovered_tools"]
StoreTools --> LogTools["Log discovered tools"]
LogTools --> End([End])
```

The tool discovery process:
1. Sends a "tools/list" JSON-RPC request to the server
2. Checks for errors in the response
3. Extracts the list of tools from the response
4. Stores the tools in the `discovered_tools` dictionary
5. Logs the discovered tools for debugging

**Diagram sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L1-L392)

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L1-L392)

#### Caching Strategies and Retry Logic
The MCPClient implements sophisticated caching and retry mechanisms to handle transient failures:

```mermaid
sequenceDiagram
participant Client as "MCPClient"
participant Transport as "MCPTransport"
participant Server as "MCP Server"
Client->>Client : _monitor_connection()
loop Every reconnect_interval seconds
Client->>Transport : send_request("ping")
alt Success
Transport->>Server : Send ping
Server-->>Transport : Response
Transport-->>Client : Success
else Failure
Transport->>Server : Request fails
Server-->>Transport : No response
Transport-->>Client : Exception
Client->>Client : _schedule_reconnection()
Client->>Client : Reconnection attempt 1
Client->>Client : Wait reconnect_interval
Client->>Client : Reconnection attempt 2
Client->>Client : Wait reconnect_interval
Client->>Client : Reconnection attempt max_retries
alt All attempts fail
Client->>Client : Log error
else Success
Client->>Client : Connection restored
end
end
end
```

The retry logic includes:
- Automatic reconnection attempts on connection failure
- Configurable retry intervals and maximum retry counts
- Background monitoring of connection health
- Prevention of duplicate reconnection tasks

**Diagram sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L1-L392)

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L1-L392)

### MCP Service Analysis
The MCPService provides a high-level interface to MCP functionality, integrating various components and providing statistics and monitoring capabilities.

```mermaid
classDiagram
class MCPService {
+registry : ToolRegistry
+servers : Dict[str, MCPServer]
+clients : Dict[str, MCPClient]
+started : bool
+stats : Dict[str, Any]
+start()
+stop()
+get_tools(category : Optional[str]) List[Dict[str, Any]]
+get_tool_schemas() List[Dict[str, Any]]
+get_tool_by_name(name : str) Optional[Dict[str, Any]]
+search_tools(query : str, category : Optional[str]) List[Dict[str, Any]]
+get_categories() Dict[str, List[str]]
+get_statistics() Dict[str, Any]
+execute_tool(name : str, arguments : Dict[str, Any]) Dict[str, Any]
+add_server(name : str, server : MCPServer)
+remove_server(name : str) bool
+add_client(name : str, client : MCPClient)
+remove_client(name : str) bool
+get_registry() ToolRegistry
}
class ToolRegistry {
+tools : Dict[str, ToolInfo]
+external_clients : Dict[str, Any]
+tool_categories : Dict[str, List[str]]
+_lock : trio.Lock
+register_tool(name : str, description : str, input_schema : Dict[str, Any], handler : Callable, category : str) bool
+register_external_tool(name : str, description : str, input_schema : Dict[str, Any], server_url : str, original_name : str, category : str) bool
+unregister_tool(name : str) bool
+get_tool(name : str) Optional[ToolInfo]
+list_tools(category : Optional[str]) List[ToolInfo]
+get_tool_schema(name : str) Optional[Dict[str, Any]]
+get_all_schemas() List[Dict[str, Any]]
+validate_arguments(tool_name : str, arguments : Dict[str, Any]) bool
+execute_tool(name : str, arguments : Dict[str, Any]) Dict[str, Any]
+_execute_external_tool(tool_info : ToolInfo, arguments : Dict[str, Any]) Dict[str, Any]
+set_external_client(server_url : str, client : Any)
+remove_external_client(server_url : str)
+get_tools_by_category() Dict[str, List[str]]
+get_tool_statistics() Dict[str, Any]
+search_tools(query : str, category : Optional[str]) List[ToolInfo]
+batch_register_tools(tools_config : List[Dict[str, Any]]) Dict[str, bool]
+export_tools_config() List[Dict[str, Any]]
+clear_registry()
}
class ToolInfo {
+name : str
+description : str
+input_schema : Dict[str, Any]
+handler : Optional[Callable]
+is_external : bool
+server_url : Optional[str]
+original_name : Optional[str]
+registered_at : str
+last_used : Optional[str]
+usage_count : int
+__post_init__()
}
MCPService --> ToolRegistry : "uses"
ToolRegistry --> ToolInfo : "contains"
```

**Diagram sources**
- [service.py](file://src/praxis_sdk/mcp/service.py#L1-L284)
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L463)

**Section sources**
- [service.py](file://src/praxis_sdk/mcp/service.py#L1-L284)
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L463)

#### Tool Registry and Management
The ToolRegistry is the central component for managing all MCP tools, both local and external:

```mermaid
flowchart TD
Start([Start]) --> RegisterTool["register_tool()"]
RegisterTool --> CheckName{"Name exists?"}
CheckName --> |Yes| LogWarning["Log warning, return False"]
CheckName --> |No| ValidateHandler{"Handler callable?"}
ValidateHandler --> |No| ThrowError["Throw ValueError"]
ValidateHandler --> |Yes| ValidateSchema{"Valid schema?"}
ValidateSchema --> |No| ThrowError
ValidateSchema --> |Yes| CreateToolInfo["Create ToolInfo object"]
CreateToolInfo --> AddToRegistry["Add to tools dictionary"]
AddToRegistry --> AddToCategory["Add to category list"]
AddToCategory --> LogSuccess["Log success"]
LogSuccess --> End([End])
```

The tool registration process ensures:
- Unique tool names
- Callable handlers
- Valid input schemas
- Proper categorization
- Usage statistics tracking

**Diagram sources**
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L463)

**Section sources**
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L463)

### MCP Server Analysis
The MCPServer component provides local tool execution capabilities and serves as an endpoint for other agents to connect to.

```mermaid
classDiagram
class MCPServer {
+config : MCPConfig
+event_bus : EventBus
+external_endpoints : List[Union[str, Dict[str, Any]]]
+builtin_tools : Dict[str, Any]
+external_clients : Dict[str, httpx.AsyncClient]
+external_tools : Dict[str, Dict[str, Any]]
+_running : bool
+_setup_builtin_tools()
+_setup_filesystem_tools()
+_setup_system_tools()
+_validate_path(root : Path, user_path : str) Path
+start()
+stop()
+_discover_external_servers()
+_connect_to_external_endpoint(endpoint : Union[str, Dict[str, Any]])
+_connect_to_mcp_server(server_config)
+_fetch_server_tools(server_id : str)
+invoke_tool(tool_name : str, arguments : Dict[str, Any]) Dict[str, Any]
+_invoke_external_tool(server_id : str, tool_name : str, arguments : Dict[str, Any]) Dict[str, Any]
+get_available_tools() List[Dict[str, Any]]
+register_dagger_tool(name : str, image : str, command : List[str], mounts : Dict[str, str], env : Dict[str, str], description : str, agent) ToolContract
+register_local_tool(name : str, command : List[str])
}
class MCPTransport {
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close()
}
class HTTPTransport {
+endpoint : str
+client : httpx.AsyncClient
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close()
}
class SSETransport {
+endpoint : str
+client : httpx.AsyncClient
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close()
}
MCPServer --> MCPTransport : "uses"
MCPTransport <|-- HTTPTransport : "implements"
MCPTransport <|-- SSETransport : "implements"
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L983)

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L983)

#### Built-in Tools and External Integration
The MCPServer supports both built-in tools and integration with external MCP servers:

```mermaid
flowchart TD
Start([Start]) --> SetupTools["_setup_builtin_tools()"]
SetupTools --> CheckFilesystem{"Filesystem enabled?"}
CheckFilesystem --> |Yes| SetupFilesystem["_setup_filesystem_tools()"]
CheckFilesystem --> |No| SetupSystem["_setup_system_tools()"]
SetupSystem --> SetupOther["Add other built-in tools"]
SetupOther --> End1([Built-in tools ready])
Start --> StartServer["start()"]
StartServer --> CheckDiscovery{"Auto-discovery enabled?"}
CheckDiscovery --> |Yes| DiscoverServers["_discover_external_servers()"]
CheckDiscovery --> |No| ConnectConfigured["Connect to configured servers"]
ConnectConfigured --> ConnectEndpoints["Connect to external endpoints"]
ConnectEndpoints --> End2([Server ready])
```

The server initialization process:
1. Sets up built-in tools based on configuration
2. Starts the server
3. Discovers external servers if auto-discovery is enabled
4. Connects to configured MCP servers
5. Connects to explicitly configured external endpoints

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L983)

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L983)

### MCP Integration Analysis
The MCPIntegration component coordinates between MCP functionality and P2P protocols, enabling seamless tool invocation across the agent network.

```mermaid
classDiagram
class MCPIntegration {
+mcp_server : Optional[MCPServer]
+mcp_client : Optional[MCPClient]
+p2p_service : Optional[P2PService]
+running : bool
+remote_tools : Dict[str, str]
+peer_tools : Dict[str, List[str]]
+initialize(p2p_service)
+_create_server_config(endpoint : str, index : int) MCPServerConfig
+_register_external_tools()
+_setup_event_handlers()
+_on_peer_discovered(event_type : str, data : Dict[str, Any])
+_on_peer_connected(event_type : str, data : Dict[str, Any])
+_on_peer_disconnected(event_type : str, data : Dict[str, Any])
+_on_p2p_tool_request(event_type : str, data : Dict[str, Any])
+_on_p2p_mcp_request(event_type : str, data : Dict[str, Any])
+_on_mcp_tool_registered(event_type : str, data : Dict[str, Any])
+_on_mcp_tool_unregistered(event_type : str, data : Dict[str, Any])
+_on_external_server_connected(event_type : str, data : Dict[str, Any])
+_on_external_server_disconnected(event_type : str, data : Dict[str, Any])
+_on_tool_execution_start(event_type : str, data : Dict[str, Any])
+_on_tool_execution_complete(event_type : str, data : Dict[str, Any])
+_on_tool_execution_error(event_type : str, data : Dict[str, Any])
+_request_peer_tools(peer_id : str)
+_broadcast_tool_update()
+invoke_remote_tool(peer_id : str, tool_name : str, arguments : Dict[str, Any]) Dict[str, Any]
+get_available_tools() Dict[str, Any]
+execute_tool(tool_name : str, arguments : Dict[str, Any]) Dict[str, Any]
+start()
+stop()
+get_statistics() Dict[str, Any]
}
MCPIntegration --> MCPServer : "uses"
MCPIntegration --> MCPClient : "uses"
MCPIntegration --> P2PService : "uses"
```

**Diagram sources**
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L480)

**Section sources**
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L480)

#### Event-Driven Integration
The MCPIntegration uses an event-driven architecture to coordinate between components:

```mermaid
sequenceDiagram
participant EventBus as "Event Bus"
participant Integration as "MCPIntegration"
participant P2P as "P2P Service"
participant Server as "MCPServer"
participant Client as "MCPClient"
EventBus->>Integration : p2p.peer_discovered
Integration->>Integration : _on_peer_discovered()
Integration->>P2P : send_mcp_request(tools/list)
P2P->>Remote : MCP Request
Remote-->>P2P : MCP Response
P2P-->>Integration : Response
Integration->>Integration : Update peer_tools
Integration->>Integration : _broadcast_tool_update()
Integration->>P2P : broadcast_to_peers()
EventBus->>Integration : mcp.tool_registered
Integration->>Integration : _on_mcp_tool_registered()
Integration->>Integration : _broadcast_tool_update()
Integration->>P2P : broadcast_to_peers()
P2P->>Integration : p2p.tool_request
Integration->>Integration : _on_p2p_tool_request()
Integration->>Server : call_tool()
Server-->>Integration : Result
Integration->>P2P : send_tool_response()
P2P->>Requester : Response
```

The event-driven integration enables:
- Automatic discovery of tools on newly connected peers
- Broadcasting of tool availability changes
- Handling of remote tool execution requests
- Coordination between MCP and P2P components

**Diagram sources**
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L480)

**Section sources**
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L480)

### LLM Integration Analysis
The MCP Client integrates with the LLM planner to enable dynamic tool selection based on natural language requests.

```mermaid
classDiagram
class WorkflowPlanner {
+p2p_service : P2PService
+mcp_registry : ToolRegistry
+dsl_orchestrator : Optional[DSLOrchestrator]
+llm_client : Optional[WorkflowPlannerClient]
+context_builder : NetworkContextBuilder
+plan_optimizer : WorkflowPlanOptimizer
+stats : Dict[str, Any]
+_initialized : bool
+initialize()
+generate_from_natural_language(user_request : str, user_id : Optional[str], optimization_goals : Optional[List[OptimizationGoal]], constraints : Optional[Dict[str, Any]]) PlanningResult
+execute_workflow_plan(workflow_plan : WorkflowPlan, execution_plan : Optional[ExecutionPlan]) Dict[str, Any]
+get_planning_suggestions(partial_request : str) List[str]
+_generate_with_llm(user_request : str, network_context : NetworkContext) WorkflowPlan
+_generate_with_fallback(user_request : str, network_context : NetworkContext) WorkflowPlan
+_update_average_processing_time(processing_time : float)
+get_network_status() Dict[str, Any]
+get_statistics() Dict[str, Any]
}
class NetworkContextBuilder {
+p2p_service : P2PService
+mcp_registry : ToolRegistry
+_agent_cache : Dict[str, AgentInfo]
+_tool_cache : Dict[str, ToolInfo]
+_metrics_cache : Optional[NetworkMetrics]
+_last_update : datetime
+_performance_history : Dict[str, List[float]]
+_success_history : Dict[str, List[bool]]
+build_network_context(include_performance_history : bool, max_age_seconds : int) NetworkContext
+get_agent_recommendations(tool_name : str, requirements : Optional[Dict[str, Any]]) List[Dict[str, Any]]
+get_network_health() Dict[str, Any]
+_discover_agents() List[AgentInfo]
+_discover_tools() List[ToolInfo]
+_calculate_network_metrics() NetworkMetrics
+_is_cache_valid(max_age_seconds : int) bool
+_build_context_from_cache() NetworkContext
+_update_caches(agents : List[AgentInfo], tools : List[ToolInfo], metrics : NetworkMetrics)
+_format_agents_for_context(agents : List[AgentInfo]) List[Dict[str, Any]]
+_format_tools_for_context(tools : List[ToolInfo]) List[Dict[str, Any]]
+_build_capability_map(agents : List[AgentInfo]) Dict[str, List[str]]
+_build_tool_routing(tools : List[ToolInfo]) Dict[str, List[str]]
+_calculate_agent_suitability(agent_info : AgentInfo, tool_name : str, requirements : Optional[Dict[str, Any]]) float
+_get_recommendation_reason(agent_info : AgentInfo, score : float) str
+_get_health_recommendations(health_score : float, metrics : NetworkMetrics) List[str]
+_get_avg_execution_time(peer_id : str, tool_name : str) float
+_get_tool_success_rate(peer_id : str, tool_name : str) float
+_get_avg_response_time(peer_id : str) float
+_get_agent_success_rate(peer_id : str) float
+_get_tool_avg_execution_time(tool_name : str) float
+_get_tool_overall_success_rate(tool_name : str) float
+_get_tool_usage_count(tool_name : str) int
}
class WorkflowPlanOptimizer {
+context_builder : NetworkContextBuilder
+dsl_patterns : Dict[str, str]
+tool_performance : Dict[str, Dict[str, Any]]
+validate_workflow_plan(workflow_plan : WorkflowPlan, network_context : Optional[NetworkContext]) List[ValidationIssue]
+optimize_workflow_plan(workflow_plan : WorkflowPlan, goal : OptimizationGoal, constraints : Optional[Dict[str, Any]]) OptimizationResult
+create_execution_plan(workflow_plan : WorkflowPlan, optimization_result : Optional[OptimizationResult]) ExecutionPlan
+_validate_dsl_syntax(dsl : str) List[ValidationIssue]
+_validate_tool_availability(dsl : str, network_context : NetworkContext) List[ValidationIssue]
+_validate_agent_assignments(agents_used : List[str], network_context : NetworkContext) List[ValidationIssue]
+_validate_resource_requirements(dsl : str, network_context : NetworkContext) List[ValidationIssue]
+_check_performance_concerns(dsl : str) List[ValidationIssue]
+_optimize_for_performance(commands : List[Dict[str, Any]], network_context : NetworkContext, constraints : Dict[str, Any]) Tuple[List[Dict[str, Any]], List[str]]
+_optimize_for_reliability(commands : List[Dict[str, Any]], network_context : NetworkContext, constraints : Dict[str, Any]) Tuple[List[Dict[str, Any]], List[str]]
+_optimize_for_cost(commands : List[Dict[str, Any]], network_context : NetworkContext, constraints : Dict[str, Any]) Tuple[List[Dict[str, Any]], List[str]]
+_parse_dsl(dsl : str) List[Dict[str, Any]]
+_build_dsl_from_commands(commands : List[Dict[str, Any]]) str
+_estimate_execution_timeline(commands : List[Dict[str, Any]]) Dict[str, float]
+_calculate_speedup(original_commands : List[Dict[str, Any]], optimized_commands : List[Dict[str, Any]]) float
+_calculate_reliability_score(commands : List[Dict[str, Any]], network_context : NetworkContext) float
+_calculate_resource_requirements(commands : List[Dict[str, Any]]) Dict[str, Any]
+_identify_bottlenecks(commands : List[Dict[str, Any]], timeline : Dict[str, float]) List[str]
+_get_tool_resources(tool_name : str) Dict[str, float]
+_estimate_step_duration(tool_name : str) float
}
WorkflowPlanner --> NetworkContextBuilder : "uses"
WorkflowPlanner --> WorkflowPlanOptimizer : "uses"
WorkflowPlanner --> WorkflowPlannerClient : "uses"
NetworkContextBuilder --> P2PService : "uses"
NetworkContextBuilder --> ToolRegistry : "uses"
WorkflowPlanOptimizer --> NetworkContextBuilder : "uses"
```

**Diagram sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L491)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L609)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L738)

**Section sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L491)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L609)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L738)

#### Natural Language to Tool Execution Flow
The integration between the MCP Client and LLM planner enables natural language requests to be converted into tool executions:

```mermaid
sequenceDiagram
participant User as "User"
participant Planner as "WorkflowPlanner"
participant Context as "NetworkContextBuilder"
participant Registry as "ToolRegistry"
participant Optimizer as "WorkflowPlanOptimizer"
participant LLM as "LLM Client"
participant Executor as "DSL Orchestrator"
participant MCP as "MCP Client/Server"
User->>Planner : generate_from_natural_language()
Planner->>Context : build_network_context()
Context->>Registry : list_tools()
Context->>P2P : get_all_agent_cards()
Registry-->>Context : Available tools
P2P-->>Context : Agent cards
Context-->>Planner : NetworkContext
alt LLM Available
Planner->>LLM : generate_workflow_from_natural_language()
LLM->>LLM : Process request with context
LLM-->>Planner : WorkflowPlan
else LLM Unavailable
Planner->>Planner : _generate_with_fallback()
Planner-->>Planner : Rule-based WorkflowPlan
end
Planner->>Optimizer : validate_workflow_plan()
Optimizer-->>Planner : Validation issues
Planner->>Optimizer : optimize_workflow_plan()
Optimizer-->>Planner : OptimizationResult
Planner->>Optimizer : create_execution_plan()
Optimizer-->>Planner : ExecutionPlan
Planner->>Executor : execute_workflow_plan()
Executor->>MCP : invoke_tool() for each step
MCP->>Local : Execute local tool
MCP->>Remote : Execute remote tool via MCPClient
Local-->>MCP : Result
Remote-->>MCP : Result
MCP-->>Executor : Results
Executor-->>Planner : Execution result
Planner-->>User : PlanningResult
```

The natural language processing flow:
1. User submits a natural language request
2. WorkflowPlanner builds network context with available tools and agents
3. LLM generates a workflow plan (or falls back to rule-based)
4. Plan is validated and optimized
5. Execution plan is created
6. DSL Orchestrator executes the workflow
7. MCP Client/Server invokes tools (local or remote)
8. Results are returned to the user

**Diagram sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L491)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L609)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L738)

**Section sources**
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py#L1-L491)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py#L1-L609)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py#L1-L738)

## Dependency Analysis
The MCP Client system has a complex dependency structure that enables its distributed functionality:

```mermaid
graph TD
MCPClient --> MCPTransport
MCPTransport <|-- HTTPTransport
MCPTransport <|-- SSETransport
MCPTransport <|-- SubprocessTransport
MCPClient --> MCPServerConfig
MCPService --> ToolRegistry
MCPService --> MCPServer
MCPService --> MCPClient
ToolRegistry --> ToolInfo
MCPServer --> MCPTransport
MCPServer --> EventBus
MCPIntegration --> MCPServer
MCPIntegration --> MCPClient
MCPIntegration --> P2PService
MCPIntegration --> EventBus
WorkflowPlanner --> NetworkContextBuilder
WorkflowPlanner --> WorkflowPlanOptimizer
WorkflowPlanner --> WorkflowPlannerClient
NetworkContextBuilder --> P2PService
NetworkContextBuilder --> ToolRegistry
WorkflowPlanOptimizer --> NetworkContextBuilder
MCPClient --> ToolRegistry
MCPServer --> ToolRegistry
MCPIntegration --> ToolRegistry
WorkflowPlanner --> ToolRegistry
```

Key dependency relationships:
- **MCPClient depends on MCPTransport**: For communication with external servers
- **MCPService depends on ToolRegistry**: For tool management
- **MCPIntegration depends on P2PService**: For peer-to-peer communication
- **WorkflowPlanner depends on NetworkContextBuilder**: For network context
- **Multiple components depend on ToolRegistry**: Central tool management

**Diagram sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py)

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py)

## Performance Considerations
The MCP Client system incorporates several performance optimizations:

- **Connection Pooling**: HTTP and SSE transports use connection pooling to reduce connection overhead
- **Caching**: Network context and tool information are cached to reduce redundant queries
- **Asynchronous Execution**: All operations are implemented asynchronously using trio and asyncio
- **Batch Operations**: Multiple tool registrations can be performed in batch
- **Efficient Data Structures**: Dictionaries are used for O(1) lookups of tools and servers
- **Connection Monitoring**: Background tasks monitor connection health to enable quick recovery
- **Retry Logic**: Configurable retry intervals and maximum retries balance reliability and resource usage

The system is designed to handle transient failures gracefully while maintaining responsiveness. The use of asynchronous programming ensures that I/O operations do not block other operations, enabling high concurrency.

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)

## Troubleshooting Guide
Common issues and their solutions:

1. **Connection failures to external servers**:
   - Verify the server endpoint is correct
   - Check network connectivity
   - Ensure the server is running and accessible
   - Review the transport type configuration

2. **Tool discovery not working**:
   - Verify the server supports the "tools/list" method
   - Check that the server has tools registered
   - Review server logs for errors
   - Ensure proper initialization has completed

3. **Authentication issues**:
   - Verify credentials if required
   - Check that the client info is properly configured
   - Review server authentication requirements

4. **Performance issues**:
   - Monitor connection latency
   - Check for network bottlenecks
   - Review server resource usage
   - Consider connection pooling settings

5. **Serialization errors**:
   - Verify JSON formatting
   - Check for special characters in payloads
   - Review encoding settings

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)

## Conclusion
The MCP Client is a sophisticated system that enables distributed agents to discover and invoke tools across a network. Its modular architecture, robust error handling, and integration with LLM planning make it a powerful component for building intelligent agent systems. The system's design emphasizes reliability, performance, and ease of integration, making it suitable for complex workflows that span multiple agents and systems.

The MCP Client's ability to seamlessly integrate local and remote tools, combined with its event-driven architecture and natural language processing capabilities, positions it as a key enabler for next-generation agent-based systems. Its comprehensive tool management, caching strategies, and retry logic ensure reliable operation in dynamic network environments.

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py)

**Referenced Files in This Document**   
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [workflow_planner.py](file://src/praxis_sdk/llm/workflow_planner.py)
- [openai_client.py](file://src/praxis_sdk/llm/openai_client.py)
- [context_builder.py](file://src/praxis_sdk/llm/context_builder.py)
- [plan_optimizer.py](file://src/praxis_sdk/llm/plan_optimizer.py)
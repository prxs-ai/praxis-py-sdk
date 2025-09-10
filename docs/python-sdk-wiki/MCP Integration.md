# MCP Integration



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
The Model Context Protocol (MCP) integration enables tools to expose their capabilities to Large Language Models (LLMs) and intelligent agents. This document provides a comprehensive analysis of the MCP implementation within the Praxis SDK, detailing how the system exposes tool metadata, handles execution requests, manages client-server communication, and integrates with workflow orchestration systems. The implementation supports both local tool execution and discovery of external MCP servers, providing a unified interface for tool capability discovery and invocation.

## Project Structure
The MCP implementation is organized within the `src/praxis_sdk/mcp` directory, with supporting components in the `docker/mcp_filesystem` directory for external server examples. The structure follows a modular design pattern with clear separation of concerns between server, client, registry, and integration components.

```mermaid
graph TD
subgraph "MCP Core Components"
server[server.py]
client[client.py]
registry[registry.py]
service[service.py]
integration[integration.py]
end
subgraph "MCP Tools"
tools[tools/]
filesystem[tools/filesystem.py]
end
subgraph "External MCP Server"
docker[Docker/mcp_filesystem/]
docker_server[docker/mcp_filesystem/server.py]
end
server --> registry
client --> registry
integration --> server
integration --> client
service --> server
service --> client
service --> registry
filesystem --> server
docker_server -.-> client
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py)
- [docker/mcp_filesystem/server.py](file://docker/mcp_filesystem/server.py)

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py)
- [docker/mcp_filesystem/server.py](file://docker/mcp_filesystem/server.py)

## Core Components
The MCP integration consists of several core components that work together to provide tool discovery, registration, and execution capabilities. The `MCPServer` class exposes local tools to LLMs and agents, while the `MCPClient` discovers and connects to external MCP servers. The `ToolRegistry` maintains a central repository of all available tools, and the `MCPService` provides a high-level interface for tool discovery and execution. The `MCPIntegration` class coordinates between MCP components and the P2P protocol for distributed tool invocation.

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)

## Architecture Overview
The MCP architecture follows a client-server model with a central registry that maintains information about all available tools, both local and external. The MCPServer exposes built-in tools and connects to external MCP servers, while the MCPClient discovers and manages connections to external servers. The ToolRegistry provides a unified interface for tool discovery and execution, and the MCPService exposes these capabilities through HTTP endpoints. The MCPIntegration component bridges the MCP functionality with the P2P network for distributed agent communication.

```mermaid
graph TD
subgraph "Agent"
MCPServer[MCPServer]
MCPClient[MCPClient]
ToolRegistry[ToolRegistry]
MCPService[MCPService]
MCPIntegration[MCPIntegration]
end
subgraph "External Systems"
ExternalMCP[External MCP Server]
P2PNetwork[P2P Network]
end
MCPServer --> ToolRegistry
MCPClient --> ToolRegistry
MCPService --> MCPServer
MCPService --> MCPClient
MCPService --> ToolRegistry
MCPIntegration --> MCPServer
MCPIntegration --> MCPClient
MCPIntegration --> P2PNetwork
MCPClient --> ExternalMCP
MCPServer --> ExternalMCP
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)

## Detailed Component Analysis

### MCPServer Analysis
The MCPServer class serves as the primary interface for exposing tool capabilities to LLMs and agents. It manages both built-in tools and connections to external MCP servers, providing a unified API for tool discovery and execution.

#### MCPServer Class Diagram
```mermaid
classDiagram
class MCPServer {
+config : MCPConfig
+event_bus : EventBus
+external_endpoints : List[Union[str, Dict]]
+builtin_tools : Dict[str, Any]
+external_clients : Dict[str, httpx.AsyncClient]
+external_tools : Dict[str, Dict[str, Any]]
+_running : bool
+__init__(config : MCPConfig, event_bus : EventBus, external_endpoints : Optional[List])
+start() void
+stop() void
+invoke_tool(tool_name : str, arguments : Dict[str, Any]) Dict[str, Any]
+get_available_tools() List[Dict[str, Any]]
+register_dagger_tool(name : str, image : str, command : List[str], mounts : Dict[str, str], env : Dict[str, Any], description : str, agent : Any) ToolContract
+_setup_builtin_tools() void
+_setup_filesystem_tools() void
+_setup_system_tools() void
+_validate_path(root : Path, user_path : str) Path
+_discover_external_servers() void
+_connect_to_external_endpoint(endpoint : Union[str, Dict]) void
+_connect_to_mcp_server(server_config : ServerConfig) void
+_fetch_server_tools(server_id : str) void
+_invoke_external_tool(server_id : str, tool_name : str, arguments : Dict[str, Any]) Dict[str, Any]
}
class MCPTransport {
<<interface>>
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close() void
}
class HTTPTransport {
-endpoint : str
-client : httpx.AsyncClient
+__init__(endpoint : str)
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close() void
}
class SSETransport {
-endpoint : str
-client : httpx.AsyncClient
+__init__(endpoint : str)
+send_request(request : Dict[str, Any]) Dict[str, Any]
+close() void
}
MCPServer --> MCPTransport : "uses"
HTTPTransport --|> MCPTransport
SSETransport --|> MCPTransport
MCPServer --> ToolRegistry : "maintains"
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L15-L983)

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L15-L983)

### MCPClient Analysis
The MCPClient class provides functionality for connecting to external MCP servers, discovering available tools, and invoking them remotely. It supports multiple transport mechanisms and includes automatic reconnection logic for robust operation.

#### MCPClient Class Diagram
```mermaid
classDiagram
class MCPClient {
+servers : Dict[str, MCPServerConfig]
+transports : Dict[str, MCPTransport]
+discovered_tools : Dict[str, List[Dict[str, Any]]]
+connection_status : Dict[str, bool]
+reconnect_tasks : Dict[str, bool]
+running : bool
+__init__()
+add_server(config : MCPServerConfig) void
+remove_server(name : str) void
+start() void
+stop() void
+_connect_server(server_name : str) void
+_create_transport(config : MCPServerConfig) MCPTransport
+_initialize_server(server_name : str, transport : MCPTransport) void
+_discover_tools(server_name : str, transport : MCPTransport) void
+_monitor_connection(server_name : str) void
+_schedule_reconnection(server_name : str) void
+call_tool(server_name : str, tool_name : str, arguments : Dict[str, Any]) Dict[str, Any]
+get_available_tools() Dict[str, List[Dict[str, Any]]]
+get_server_status() Dict[str, bool]
+list_resources(server_name : str) List[Dict[str, Any]]
+read_resource(server_name : str, uri : str) Dict[str, Any]
+is_server_connected(server_name : str) bool
+refresh_tools(server_name : str) void
}
class MCPServerConfig {
+name : str
+transport_type : str
+endpoint : str
+enabled : bool
+reconnect_interval : int
+max_retries : int
+__init__(name : str, transport_type : str, endpoint : str, enabled : bool, reconnect_interval : int, max_retries : int)
}
class SubprocessTransport {
-command : List[str]
-cwd : Optional[str]
-process : Optional[Process]
-stdin_stream : Optional[Stream]
-stdout_stream : Optional[Stream]
+__init__(command : List[str], cwd : Optional[str])
+start() void
+send_request(method : str, params : Dict[str, Any]) Dict[str, Any]
+close() void
}
MCPClient --> MCPServerConfig
MCPClient --> SubprocessTransport
SubprocessTransport --|> MCPTransport
```

**Diagram sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L15-L392)

**Section sources**
- [client.py](file://src/praxis_sdk/mcp/client.py#L15-L392)

### ToolRegistry Analysis
The ToolRegistry class serves as the central repository for all MCP tools, both local and external. It manages tool registration, schema validation, and execution coordination, providing a unified interface for tool discovery and invocation.

#### ToolRegistry Class Diagram
```mermaid
classDiagram
class ToolRegistry {
+tools : Dict[str, ToolInfo]
+external_clients : Dict[str, Any]
+tool_categories : Dict[str, List[str]]
+_lock : trio.Lock
+__init__()
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
+set_external_client(server_url : str, client : Any) void
+remove_external_client(server_url : str) void
+get_tools_by_category() Dict[str, List[str]]
+get_tool_statistics() Dict[str, Any]
+search_tools(query : str, category : Optional[str]) List[ToolInfo]
+batch_register_tools(tools_config : List[Dict[str, Any]]) Dict[str, bool]
+export_tools_config() List[Dict[str, Any]]
+clear_registry() void
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
+__post_init__() void
}
ToolRegistry --> ToolInfo
```

**Diagram sources**
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L15-L463)

**Section sources**
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L15-L463)

### MCPIntegration Analysis
The MCPIntegration class provides the bridge between MCP functionality and the P2P network, enabling distributed tool invocation across agents. It coordinates between the MCPServer, MCPClient, and P2P service to provide seamless tool discovery and execution.

#### MCPIntegration Sequence Diagram
```mermaid
sequenceDiagram
participant P2P as P2P Service
participant Integration as MCPIntegration
participant Server as MCPServer
participant Client as MCPClient
participant Registry as ToolRegistry
P2P->>Integration : peer_discovered event
Integration->>Integration : _on_peer_discovered()
Integration->>P2P : send_mcp_request(tools/list)
P2P->>RemotePeer : MCP Request
RemotePeer-->>P2P : MCP Response
P2P-->>Integration : MCP Response
Integration->>Registry : register remote tools
Integration->>P2P : broadcast_tool_update
P2P->>Integration : p2p.tool_request
Integration->>Integration : _on_p2p_tool_request()
Integration->>Server : call_tool()
Server->>Registry : execute_tool()
Registry->>Registry : validate_arguments()
alt Local Tool
Registry->>Registry : execute local handler
else External Tool
Registry->>Client : call_tool()
end
Registry-->>Server : execution result
Server-->>Integration : tool result
Integration->>P2P : send_tool_response()
P2P-->>RemotePeer : Tool Response
```

**Diagram sources**
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L15-L480)

**Section sources**
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L15-L480)

### MCPService Analysis
The MCPService class provides a high-level interface to MCP functionality, exposing tools discovery, statistics, and execution capabilities through a simple API. It serves as the primary interface for HTTP endpoint integration.

#### MCPService Class Diagram
```mermaid
classDiagram
class MCPService {
+registry : ToolRegistry
+servers : Dict[str, MCPServer]
+clients : Dict[str, MCPClient]
+started : bool
+stats : Dict[str, Any]
+__init__()
+start() void
+stop() void
+get_tools(category : Optional[str]) List[Dict[str, Any]]
+get_tool_schemas() List[Dict[str, Any]]
+get_tool_by_name(name : str) Optional[Dict[str, Any]]
+search_tools(query : str, category : Optional[str]) List[Dict[str, Any]]
+get_categories() Dict[str, List[str]]
+get_statistics() Dict[str, Any]
+execute_tool(name : str, arguments : Dict[str, Any]) Dict[str, Any]
+add_server(name : str, server : MCPServer) void
+remove_server(name : str) bool
+add_client(name : str, client : MCPClient) void
+remove_client(name : str) bool
+get_registry() ToolRegistry
}
MCPService --> ToolRegistry
MCPService --> MCPServer
MCPService --> MCPClient
```

**Diagram sources**
- [service.py](file://src/praxis_sdk/mcp/service.py#L15-L284)

**Section sources**
- [service.py](file://src/praxis_sdk/mcp/service.py#L15-L284)

### Filesystem Tools Analysis
The filesystem.py module implements MCP-compliant tools for filesystem operations with security validation and integration with the shared directory system. These tools provide basic file operations while enforcing security constraints.

#### Filesystem Tools Flowchart
```mermaid
flowchart TD
Start([Function Entry]) --> ValidatePath["Validate Path Security"]
ValidatePath --> PathValid{"Path Valid?"}
PathValid --> |No| ReturnSecurityError["Return Security Error"]
PathValid --> |Yes| ExecuteOperation["Execute File Operation"]
ExecuteOperation --> OperationType{"Operation Type?"}
OperationType --> |read_file| ReadFile["Read File Content"]
OperationType --> |write_file| WriteFile["Write File Content"]
OperationType --> |list_directory| ListDirectory["List Directory Contents"]
OperationType --> |create_directory| CreateDirectory["Create Directory"]
OperationType --> |delete_file| DeleteFile["Delete File"]
OperationType --> |move_file| MoveFile["Move/Rename File"]
OperationType --> |get_file_info| GetFileInfo["Get File Information"]
OperationType --> |search_files| SearchFiles["Search Files"]
OperationType --> |copy_file| CopyFile["Copy File"]
ReadFile --> CheckBinary["Check for Binary Content"]
CheckBinary --> ReturnContent["Return File Content"]
WriteFile --> CreateParents["Create Parent Directories"]
CreateParents --> WriteContent["Write Content to File"]
WriteContent --> ReturnSuccess["Return Success"]
ListDirectory --> FilterHidden["Filter Hidden Files"]
FilterHidden --> SortEntries["Sort Entries"]
SortEntries --> ReturnEntries["Return Directory Entries"]
CreateDirectory --> CheckExists["Check if Directory Exists"]
CheckExists --> |Yes| ReturnExists["Return Already Exists"]
CheckExists --> |No| CreateDir["Create Directory"]
CreateDir --> ReturnSuccess
DeleteFile --> CheckExists["Check if File Exists"]
CheckExists --> |No| ReturnNotFound["Return Not Found"]
CheckExists --> |Yes| Delete["Delete File"]
Delete --> ReturnSuccess
MoveFile --> CheckSource["Check Source Exists"]
CheckSource --> |No| ReturnSourceError["Return Source Error"]
CheckSource --> |Yes| CheckDest["Check Destination Exists"]
CheckDest --> |Yes| ReturnDestError["Return Destination Error"]
CheckDest --> |No| Move["Move File"]
Move --> ReturnSuccess
GetFileInfo --> GetStats["Get File Statistics"]
GetStats --> ReturnInfo["Return File Information"]
SearchFiles --> BuildPattern["Build Search Pattern"]
BuildPattern --> FindMatches["Find Matching Files"]
FindMatches --> FilterResults["Filter Results"]
FilterResults --> SortResults["Sort Results"]
SortResults --> ReturnMatches["Return Matches"]
CopyFile --> CheckSource["Check Source Exists"]
CheckSource --> |No| ReturnSourceError
CheckSource --> |Yes| CheckSourceIsFile["Check Source is File"]
CheckSourceIsFile --> |No| ReturnNotFile["Return Not File"]
CheckSourceIsFile --> |Yes| CreateDestParents["Create Destination Parents"]
CreateDestParents --> Copy["Copy File"]
Copy --> ReturnSuccess
ReturnSecurityError --> End([Function Exit])
ReturnContent --> End
ReturnSuccess --> End
ReturnExists --> End
ReturnNotFound --> End
ReturnSourceError --> End
ReturnDestError --> End
ReturnNotFile --> End
ReturnInfo --> End
ReturnEntries --> End
ReturnMatches --> End
```

**Diagram sources**
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py#L15-L679)

**Section sources**
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py#L15-L679)

## Dependency Analysis
The MCP components have a well-defined dependency structure that enables modular development and testing. The core dependencies flow from the service layer down to the implementation details, with proper separation of concerns.

```mermaid
graph TD
MCPService --> MCPServer
MCPService --> MCPClient
MCPService --> ToolRegistry
MCPIntegration --> MCPServer
MCPIntegration --> MCPClient
MCPServer --> ToolRegistry
MCPClient --> ToolRegistry
MCPServer --> HTTPTransport
MCPServer --> SSETransport
MCPClient --> HTTPTransport
MCPClient --> SSETransport
MCPClient --> SubprocessTransport
MCPServer --> FilesystemTools
ToolRegistry --> ToolInfo
MCPIntegration --> P2PNetwork
FilesystemTools --> SecurityValidation
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py)

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py)

## Performance Considerations
The MCP implementation includes several performance considerations to ensure efficient operation in distributed environments. The system uses asynchronous I/O for all network operations, preventing blocking during tool execution and server communication. Connection pooling is implemented through the use of persistent HTTP clients, reducing the overhead of establishing new connections for each request. The tool registry maintains an in-memory cache of available tools, eliminating the need for repeated discovery operations. For filesystem operations, the implementation includes size limits and binary file detection to prevent excessive resource consumption. The P2P integration uses event-driven architecture to minimize polling and reduce network traffic. Error handling is designed to be non-blocking, allowing the system to continue operating even when individual tool invocations fail.

## Troubleshooting Guide
Common issues with MCP integration typically fall into several categories: connectivity problems, tool discovery failures, and execution errors. For connectivity issues, verify that external MCP servers are running and accessible from the agent environment. Check firewall settings and network configuration, particularly when running in containerized environments. For tool discovery failures, ensure that the MCP server has been properly initialized and that the external endpoints are correctly configured in the agent configuration. Execution errors may occur due to invalid arguments or security restrictions; check the logs for specific error messages and validate that the tool parameters match the expected schema. When debugging, enable verbose logging to capture detailed information about MCP requests and responses. For P2P-related issues, verify that the P2P service is running and that peers are properly discovered and connected. Use the MCP service endpoints to inspect the current state of registered tools and server connections.

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)

## Conclusion
The MCP integration in the Praxis SDK provides a comprehensive framework for exposing tool capabilities to LLMs and agents. The system supports both local tool execution and discovery of external MCP servers, providing a unified interface for tool capability discovery and invocation. The modular architecture with clear separation of concerns enables flexible deployment and integration with various agent systems. Security is prioritized throughout the implementation, particularly in filesystem operations where path validation prevents directory traversal attacks. The integration with P2P protocols enables distributed agent networks to share tool capabilities seamlessly. Future enhancements could include support for additional transport mechanisms, improved error handling and recovery strategies, and enhanced security features such as authentication and authorization for tool access.

**Referenced Files in This Document**   
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [client.py](file://src/praxis_sdk/mcp/client.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py)
- [docker/mcp_filesystem/server.py](file://docker/mcp_filesystem/server.py)
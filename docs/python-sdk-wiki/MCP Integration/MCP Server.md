# MCP Server



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
The MCP (Model Context Protocol) Server is a core component of the Praxis Agent ecosystem, designed to expose tool capabilities to agents and LLMs through standardized endpoints. It enables seamless integration of both local and external tools, providing a unified interface for tool discovery, registration, and execution. Built on FastAPI, the server supports JSON-RPC 2.0 protocol for communication and integrates with the PraxisAgent event bus for real-time monitoring and coordination. The architecture supports dynamic tool registration, including Docker-based tools via Dagger, and provides robust security features such as path validation and input sanitization. This document provides a comprehensive analysis of the MCP Server implementation, covering its architecture, component relationships, data flows, and integration patterns.

## Project Structure
The MCP Server implementation is organized within the `src/praxis_sdk/mcp` directory, with supporting components in the `docker/mcp_filesystem` directory for external tool execution. The structure follows a modular design pattern, separating concerns into distinct components for transport, server logic, registry management, and service integration.

```mermaid
graph TD
subgraph "MCP Core"
server[server.py]
registry[registry.py]
service[service.py]
integration[integration.py]
end
subgraph "Tools"
tools[tools/]
filesystem[tools/filesystem.py]
end
subgraph "External"
docker[docker/mcp_filesystem]
docker_server[docker/mcp_filesystem/server.py]
end
server --> registry
service --> server
integration --> server
integration --> service
filesystem --> server
docker_server --> server
style server fill:#f9f,stroke:#333
style registry fill:#bbf,stroke:#333
style service fill:#f96,stroke:#333
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py)
- [server.py](file://docker/mcp_filesystem/server.py)

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)

## Core Components
The MCP Server architecture consists of several core components that work together to provide tool management and execution capabilities. The `MCPServer` class serves as the main entry point, handling incoming requests and coordinating tool execution. The `ToolRegistry` maintains a centralized catalog of available tools, both local and external, with metadata and schema information. The `MCPService` provides a high-level interface for HTTP endpoint integration, exposing tool capabilities through RESTful APIs. The `MCPIntegration` class bridges the MCP functionality with the P2P network and event bus, enabling distributed tool discovery and execution. Each component follows the single responsibility principle, ensuring maintainability and testability.

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L50)
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L50)
- [service.py](file://src/praxis_sdk/mcp/service.py#L1-L50)
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L50)

## Architecture Overview
The MCP Server architecture follows a layered design pattern, with clear separation between transport, business logic, and service layers. The system exposes standardized endpoints for tool discovery and execution, enabling seamless integration with LLMs and agent frameworks. The architecture supports both local tool execution and delegation to external MCP servers, providing flexibility in deployment scenarios.

```mermaid
graph TD
Client[LLM/Agent Client] --> |HTTP/SSE| API[FastAPI Endpoint]
API --> Service[MCPService]
Service --> Registry[ToolRegistry]
Service --> Server[MCPServer]
subgraph "Local Tools"
Server --> BuiltIn[Filesystem Tools]
Server --> System[get_system_info]
Server --> Python[execute_python]
Server --> Dagger[Dagger Tools]
end
subgraph "External Tools"
Server --> External[External MCP Servers]
External --> Filesystem[Filesystem Server]
External --> Custom[Custom Tools]
end
Registry --> EventBus[(Event Bus)]
Server --> EventBus
Service --> EventBus
style API fill:#9f9,stroke:#333
style Service fill:#f96,stroke:#333
style Registry fill:#bbf,stroke:#333
style Server fill:#f9f,stroke:#333
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L100)
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L50)
- [service.py](file://src/praxis_sdk/mcp/service.py#L1-L50)

## Detailed Component Analysis

### MCPServer Analysis
The `MCPServer` class is the central component responsible for handling tool execution requests and managing connections to external servers. It implements both HTTP and SSE (Server-Sent Events) transports for MCP communication, providing flexibility in deployment scenarios. The server supports automatic discovery of external MCP servers on configured ports and can connect to explicitly specified endpoints.

```mermaid
classDiagram
class MCPServer {
+config : MCPConfig
+event_bus : EventBus
+external_endpoints : List[Union[str, Dict]]
+builtin_tools : Dict[str, Any]
+external_clients : Dict[str, httpx.AsyncClient]
+external_tools : Dict[str, Dict]
+_running : bool
+__init__(config, event_bus, external_endpoints)
+start() void
+stop() void
+_setup_builtin_tools() void
+_setup_filesystem_tools() void
+_setup_system_tools() void
+_validate_path(root, user_path) Path
+invoke_tool(tool_name, arguments) Dict
+_invoke_external_tool(server_id, tool_name, arguments) Dict
+get_available_tools() List[Dict]
+register_dagger_tool(name, image, command, mounts, env, description, agent) ToolContract
+register_local_tool(name, command, description, input_schema, handler) void
}
class MCPTransport {
<<interface>>
+send_request(request) Dict
+close() void
}
class HTTPTransport {
+endpoint : str
+client : httpx.AsyncClient
+send_request(request) Dict
+close() void
}
class SSETransport {
+endpoint : str
+client : httpx.AsyncClient
+send_request(request) Dict
+close() void
}
MCPServer --> MCPTransport : "uses"
HTTPTransport --|> MCPTransport
SSETransport --|> MCPTransport
MCPServer --> EventBus : "publishes events"
MCPServer --> ToolRegistry : "registers tools"
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L400)

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L983)

### ToolRegistry Analysis
The `ToolRegistry` class provides a centralized catalog for all MCP tools, both local and external. It manages tool metadata, input schemas, and execution handlers, ensuring consistent validation and execution across different tool types. The registry supports categorization of tools and maintains usage statistics for monitoring and optimization.

```mermaid
classDiagram
class ToolRegistry {
+tools : Dict[str, ToolInfo]
+external_clients : Dict[str, Any]
+tool_categories : Dict[str, List[str]]
+_lock : trio.Lock
+register_tool(name, description, input_schema, handler, category) bool
+register_external_tool(name, description, input_schema, server_url, original_name, category) bool
+unregister_tool(name) bool
+get_tool(name) Optional[ToolInfo]
+list_tools(category) List[ToolInfo]
+get_tool_schema(name) Optional[Dict]
+get_all_schemas() List[Dict]
+validate_arguments(tool_name, arguments) bool
+execute_tool(name, arguments) Dict
+_execute_external_tool(tool_info, arguments) Dict
+set_external_client(server_url, client) void
+remove_external_client(server_url) void
+get_tools_by_category() Dict[str, List[str]]
+get_tool_statistics() Dict[str, Any]
+search_tools(query, category) List[ToolInfo]
+batch_register_tools(tools_config) Dict[str, bool]
+export_tools_config() List[Dict]
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
}
ToolRegistry --> ToolInfo : "contains"
```

**Diagram sources**
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L463)

**Section sources**
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L463)

### MCPService Analysis
The `MCPService` class provides a high-level interface for HTTP endpoint integration, exposing tool capabilities through RESTful APIs. It acts as a facade for the underlying MCP components, handling request routing, statistics collection, and resource management. The service maintains comprehensive statistics on tool usage and system performance.

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
+get_tools(category) List[Dict]
+get_tool_schemas() List[Dict]
+get_tool_by_name(name) Optional[Dict]
+search_tools(query, category) List[Dict]
+get_categories() Dict[str, List[str]]
+get_statistics() Dict[str, Any]
+execute_tool(name, arguments) Dict
+add_server(name, server) void
+remove_server(name) bool
+add_client(name, client) void
+remove_client(name) bool
+get_registry() ToolRegistry
}
MCPService --> ToolRegistry : "uses"
MCPService --> MCPServer : "manages"
MCPService --> MCPClient : "manages"
```

**Diagram sources**
- [service.py](file://src/praxis_sdk/mcp/service.py#L1-L284)

**Section sources**
- [service.py](file://src/praxis_sdk/mcp/service.py#L1-L284)

### MCPIntegration Analysis
The `MCPIntegration` class bridges the MCP functionality with the P2P network and event bus, enabling distributed tool discovery and execution. It coordinates between the MCP server, client, and P2P protocols, providing seamless integration across the agent network.

```mermaid
classDiagram
class MCPIntegration {
+mcp_server : Optional[MCPServer]
+mcp_client : Optional[MCPClient]
+p2p_service : Optional[Any]
+running : bool
+remote_tools : Dict[str, str]
+peer_tools : Dict[str, List[str]]
+__init__()
+initialize(p2p_service) void
+_create_server_config(endpoint, index) MCPServerConfig
+_register_external_tools() void
+_setup_event_handlers() void
+_on_peer_discovered(event_type, data) void
+_on_peer_connected(event_type, data) void
+_on_peer_disconnected(event_type, data) void
+_on_p2p_tool_request(event_type, data) void
+_on_p2p_mcp_request(event_type, data) void
+_on_mcp_tool_registered(event_type, data) void
+_on_mcp_tool_unregistered(event_type, data) void
+_on_external_server_connected(event_type, data) void
+_on_external_server_disconnected(event_type, data) void
+_on_tool_execution_start(event_type, data) void
+_on_tool_execution_complete(event_type, data) void
+_on_tool_execution_error(event_type, data) void
+_request_peer_tools(peer_id) void
+_broadcast_tool_update() void
+invoke_remote_tool(peer_id, tool_name, arguments) Dict
+get_available_tools() Dict[str, Any]
+execute_tool(tool_name, arguments) Dict
+start() void
+stop() void
+get_statistics() Dict[str, Any]
}
MCPIntegration --> MCPServer : "uses"
MCPIntegration --> MCPClient : "uses"
MCPIntegration --> P2PService : "integrates"
MCPIntegration --> EventBus : "subscribes"
```

**Diagram sources**
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L480)

**Section sources**
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L480)

### Filesystem Tools Analysis
The `FilesystemTools` class implements secure filesystem operations with comprehensive validation and error handling. It enforces security policies by restricting operations to allowed directories and validating all paths to prevent directory traversal attacks.

```mermaid
classDiagram
class FilesystemTools {
+shared_dir : Path
+allowed_paths : List[Path]
+__init__()
+_validate_path(path_str) Path
+add_allowed_path(path_str) void
+read_file(path, encoding) Dict
+write_file(path, content, encoding, create_dirs) Dict
+list_directory(path, show_hidden) Dict
+create_directory(path, parents) Dict
+delete_file(path) Dict
+move_file(source, destination) Dict
+get_file_info(path) Dict
+search_files(directory, pattern, recursive) Dict
+copy_file(source, destination) Dict
}
class SecurityError {
<<exception>>
}
FilesystemTools --> SecurityError : "raises"
```

**Diagram sources**
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py#L1-L679)

**Section sources**
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py#L1-L679)

### External Filesystem Server Analysis
The external MCP Filesystem Server is implemented as a FastAPI application, providing filesystem operations through the Model Context Protocol. It runs in a Docker container and exposes standardized endpoints for file operations, with security features such as path validation and size limits.

```mermaid
sequenceDiagram
participant Client
participant FastAPI
participant Server
participant Filesystem
Client->>FastAPI : POST /mcp
FastAPI->>Server : handle_mcp_request()
Server->>Server : Validate method
alt tools/list
Server->>Server : Return capabilities
Server->>FastAPI : MCPResponse
FastAPI->>Client : 200 OK
else tools/call
Server->>Server : Extract tool name
alt write_file
Server->>Server : validate WriteFileParams
Server->>Filesystem : write_file()
Filesystem->>Server : result
Server->>FastAPI : MCPResponse
FastAPI->>Client : 200 OK
else read_file
Server->>Server : validate ReadFileParams
Server->>Filesystem : read_file()
Filesystem->>Server : result
Server->>FastAPI : MCPResponse
FastAPI->>Client : 200 OK
else list_directory
Server->>Server : validate ListDirectoryParams
Server->>Filesystem : list_directory()
Filesystem->>Server : result
Server->>FastAPI : MCPResponse
FastAPI->>Client : 200 OK
else create_directory
Server->>Server : validate CreateDirectoryParams
Server->>Filesystem : create_directory()
Filesystem->>Server : result
Server->>FastAPI : MCPResponse
FastAPI->>Client : 200 OK
else
Server->>FastAPI : MCPResponse with error
FastAPI->>Client : 200 OK
end
else
Server->>FastAPI : MCPResponse with error
FastAPI->>Client : 200 OK
end
```

**Diagram sources**
- [server.py](file://docker/mcp_filesystem/server.py#L1-L367)

**Section sources**
- [server.py](file://docker/mcp_filesystem/server.py#L1-L367)

## Dependency Analysis
The MCP Server implementation has a well-defined dependency structure, with clear separation between components. The core dependencies flow from the service layer down to the registry and server components, with integration components bridging to external systems.

```mermaid
graph TD
MCPService --> MCPServer
MCPService --> ToolRegistry
MCPIntegration --> MCPServer
MCPIntegration --> MCPClient
MCPIntegration --> P2PService
MCPServer --> ToolRegistry
MCPServer --> EventBus
FilesystemTools --> MCPServer
DockerServer --> MCPServer
style MCPService fill:#f96,stroke:#333
style MCPServer fill:#f9f,stroke:#333
style ToolRegistry fill:#bbf,stroke:#333
style MCPClient fill:#69f,stroke:#333
style P2PService fill:#6f9,stroke:#333
style EventBus fill:#999,stroke:#333
```

**Diagram sources**
- [service.py](file://src/praxis_sdk/mcp/service.py#L1-L50)
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L50)
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L50)
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L50)

**Section sources**
- [service.py](file://src/praxis_sdk/mcp/service.py#L1-L50)
- [server.py](file://src/praxis_sdk/mcp/server.py#L1-L50)
- [registry.py](file://src/praxis_sdk/mcp/registry.py#L1-L50)
- [integration.py](file://src/praxis_sdk/mcp/integration.py#L1-L50)

## Performance Considerations
The MCP Server implementation includes several performance optimizations and considerations. The use of asynchronous programming with asyncio and trio enables efficient handling of concurrent requests without blocking. The registry maintains an in-memory catalog of tools, providing O(1) lookup performance for tool discovery. The server implements connection pooling for external MCP servers through persistent HTTP clients, reducing connection overhead. For filesystem operations, the implementation uses buffered I/O and validates paths efficiently using Path.resolve() and string prefix matching. The architecture supports horizontal scaling through external MCP servers, allowing compute-intensive operations to be distributed across multiple containers or hosts. Rate limiting and input validation prevent denial-of-service attacks and ensure system stability under load.

## Troubleshooting Guide
Common issues with the MCP Server typically fall into several categories: connectivity problems, tool registration issues, and execution errors. For connectivity issues, verify that the server is running and accessible at the configured address and port. Check the logs for error messages related to HTTP client connections or SSE streaming. For tool registration problems, ensure that the tool metadata includes required fields such as name, description, and input schema. Verify that handlers are properly defined and accessible. For execution errors, check the input validation against the tool's schema and ensure that all required parameters are provided. Security-related errors often stem from path validation failures, so verify that file operations are within allowed directories. When integrating with external MCP servers, confirm that the server is properly initialized with the correct endpoint and that the capabilities endpoint returns the expected tools. Use the /health endpoint to verify server status and the /capabilities endpoint to inspect available tools.

**Section sources**
- [server.py](file://src/praxis_sdk/mcp/server.py#L330-L372)
- [service.py](file://src/praxis_sdk/mcp/service.py#L60-L99)
- [worker_filesystem.yaml](file://configs/worker_filesystem.yaml)

## Conclusion
The MCP Server implementation provides a robust and flexible framework for exposing tool capabilities to agents and LLMs through standardized endpoints. Its modular architecture, built on FastAPI and integrated with the PraxisAgent event bus, enables seamless tool discovery, registration, and execution. The system supports both local and external tools, with comprehensive security features and performance optimizations. The detailed analysis of core components reveals a well-designed system with clear separation of concerns and efficient data flows. The implementation demonstrates best practices in asynchronous programming, error handling, and security validation, making it suitable for production deployment in agent-based systems.

**Referenced Files in This Document**   
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [registry.py](file://src/praxis_sdk/mcp/registry.py)
- [service.py](file://src/praxis_sdk/mcp/service.py)
- [integration.py](file://src/praxis_sdk/mcp/integration.py)
- [filesystem.py](file://src/praxis_sdk/mcp/tools/filesystem.py)
- [server.py](file://docker/mcp_filesystem/server.py)
- [worker_filesystem.yaml](file://configs/worker_filesystem.yaml)
# Tool Execution Testing



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
This document provides a comprehensive analysis of tool execution testing in the Praxis Py SDK, focusing on validating containerized tool invocation via MCP (Model Context Protocol) contracts and execution engine orchestration. The analysis covers how `test_tool_execution.py` verifies correct tool discovery, input validation against contract schemas, and sandboxed runtime execution using Docker or Dagger. It includes examples of asserting output formatting, error propagation, and resource limits enforcement, along with integration points with `mcp/server.py` for capability registration and `execution/engine.py` for runtime selection. The document also addresses testing edge cases such as dependency resolution, timeout handling, and filesystem isolation, and provides guidance on extending tests for custom tool types.

## Project Structure
The project structure is organized into several key directories:
- `configs/`: Configuration files for agents, orchestrators, and workers.
- `docker/mcp_filesystem/`: Docker configuration for the MCP filesystem server.
- `src/praxis_sdk/`: Core source code including modules for A2A communication, API, cache, DSL, execution, LLM, MCP, P2P, tools, and workflow management.
- `tests/`: Integration and unit tests, including `test_tool_execution.py`.
- `tools/`: Various tool implementations with their contract files.

This structure supports a modular architecture where different components can be developed and tested independently.

## Core Components
The core components involved in tool execution testing include:
- **MCP Server**: Manages tool registration and invocation via JSON-RPC.
- **Execution Engines**: Handle the actual execution of tools using different backends (Dagger, Docker SDK, local subprocess).
- **Tool Contracts**: Define the schema and execution parameters for tools.

These components work together to ensure that tools are discovered, validated, and executed correctly in a secure and isolated environment.

**Section sources**
- [test_tool_execution.py](file://tests/integration/test_tool_execution.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [engine.py](file://src/praxis_sdk/execution/engine.py)

## Architecture Overview
The architecture for tool execution testing involves several key components interacting through well-defined interfaces. The MCP server acts as the central hub for tool discovery and invocation, while the execution engines handle the actual execution of tools in isolated environments.

```mermaid
graph TB
subgraph "Testing Framework"
TestScript[test_tool_execution.py]
end
subgraph "MCP Server"
MCPServer[mcp/server.py]
ToolRegistry[Tool Registry]
end
subgraph "Execution Engines"
DaggerEngine[execution/engine.py<br>DaggerExecutionEngine]
DockerSDK[DockerSDKExecutionEngine]
LocalEngine[LocalExecutionEngine]
end
TestScript --> MCPServer
MCPServer --> ToolRegistry
ToolRegistry --> DaggerEngine
ToolRegistry --> DockerSDK
ToolRegistry --> LocalEngine
DaggerEngine --> Container[Docker Container]
DockerSDK --> Container
LocalEngine --> HostSystem[Host System]
style TestScript fill:#f9f,stroke:#333
style MCPServer fill:#bbf,stroke:#333
style ToolRegistry fill:#bbf,stroke:#333
style DaggerEngine fill:#f96,stroke:#333
style DockerSDK fill:#f96,stroke:#333
style LocalEngine fill:#f96,stroke:#333
style Container fill:#9f9,stroke:#333
style HostSystem fill:#9f9,stroke:#333
```

**Diagram sources**
- [test_tool_execution.py](file://tests/integration/test_tool_execution.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [engine.py](file://src/praxis_sdk/execution/engine.py)

## Detailed Component Analysis

### MCP Server Analysis
The MCP server is responsible for managing tool registration and invocation. It uses JSON-RPC over HTTP to communicate with clients and supports both built-in and external tools.

#### Class Diagram for MCP Server
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
+__init__(config : MCPConfig, event_bus : EventBus, external_endpoints : Optional[List[Union[str, Dict[str, Any]]]])
+start()
+stop()
+_setup_builtin_tools()
+_setup_filesystem_tools()
+_setup_system_tools()
+_validate_path(root : Path, user_path : str) -> Path
+_discover_external_servers()
+_connect_to_external_endpoint(endpoint : Union[str, Dict[str, Any]])
+_connect_to_mcp_server(server_config)
+_fetch_server_tools(server_id : str)
+invoke_tool(tool_name : str, arguments : Dict[str, Any]) -> Dict[str, Any]
+_invoke_external_tool(server_id : str, tool_name : str, arguments : Dict[str, Any]) -> Dict[str, Any]
+get_available_tools() -> List[Dict[str, Any]]
+register_dagger_tool(name : str, image : str, command : List[str], mounts : Dict[str, str], env : Dict[str, str], description : str, agent) -> ToolContract
+register_local_tool(name : str, command : List[str])
}
class MCPConfig {
+filesystem_enabled : bool
+filesystem_root : str
+auto_discovery : bool
+discovery_ports : List[int]
+servers : List[ServerConfig]
+external_endpoints : List[Union[str, Dict[str, Any]]]
}
class EventBus {
+publish_data(event_type : EventType, data : Dict[str, Any])
}
class EventType {
+LOG_ENTRY
}
MCPServer --> MCPConfig : "uses"
MCPServer --> EventBus : "uses"
MCPServer --> EventType : "uses"
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/mcp/server.py)

### Execution Engine Analysis
The execution engines are responsible for running tools in isolated environments. The main engines are `DaggerExecutionEngine`, `DockerSDKExecutionEngine`, and `LocalExecutionEngine`.

#### Sequence Diagram for Tool Execution
```mermaid
sequenceDiagram
participant Test as "test_tool_execution.py"
participant MCPServer as "MCPServer"
participant Engine as "ExecutionEngine"
participant Container as "Docker Container"
Test->>MCPServer : invoke_tool(tool_name, arguments)
MCPServer->>MCPServer : validate tool_name in builtin_tools
alt Built-in Tool
MCPServer->>Engine : execute(contract, arguments)
Engine->>Engine : validate_contract(contract)
Engine->>Engine : prepare_environment_variables()
Engine->>Container : create container with image and mounts
Engine->>Container : set working directory
Engine->>Container : apply environment variables
Engine->>Container : execute command
Container-->>Engine : return stdout/stderr
Engine-->>MCPServer : return output
else External Tool
MCPServer->>MCPServer : find server_id in external_tools
MCPServer->>MCPServer : _invoke_external_tool(server_id, tool_name, arguments)
MCPServer->>ExternalServer : POST /mcp with JSON-RPC request
ExternalServer-->>MCPServer : JSON-RPC response
MCPServer-->>Test : return result
end
MCPServer-->>Test : return result
```

**Diagram sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py)

### Tool Contract Analysis
Tool contracts define the schema and execution parameters for tools. They are used by the execution engines to validate and execute tools.

#### Flowchart for Tool Contract Validation
```mermaid
flowchart TD
Start([Start]) --> ValidateContract["Validate Contract"]
ValidateContract --> ContractValid{"Contract Valid?"}
ContractValid --> |No| ReturnError["Return ValidationError"]
ContractValid --> |Yes| ParseSpec["Parse Engine Spec"]
ParseSpec --> SpecType{"Spec Type?"}
SpecType --> |DaggerEngineSpec| UseDaggerEngine["Use DaggerExecutionEngine"]
SpecType --> |LocalEngineSpec| UseLocalEngine["Use LocalExecutionEngine"]
SpecType --> |RemoteMCPEngineSpec| UseRemoteEngine["Use RemoteMCPEngine"]
UseDaggerEngine --> ExecuteTool["Execute Tool"]
UseLocalEngine --> ExecuteTool
UseRemoteEngine --> ExecuteTool
ExecuteTool --> ExecutionResult{"Execution Successful?"}
ExecutionResult --> |No| HandleError["Handle ExecutionError"]
ExecutionResult --> |Yes| ReturnOutput["Return Output"]
HandleError --> ReturnError
ReturnOutput --> End([End])
ReturnError --> End
```

**Diagram sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py)

## Dependency Analysis
The components in the tool execution testing framework have the following dependencies:
- `test_tool_execution.py` depends on `mcp/server.py` and `execution/engine.py`.
- `mcp/server.py` depends on `execution/contracts.py` for tool contracts.
- `execution/engine.py` depends on `docker` and `dagger` libraries for containerized execution.

These dependencies ensure that the framework can handle both local and remote tool execution in a secure and isolated manner.

```mermaid
graph TD
A[test_tool_execution.py] --> B[mcp/server.py]
A --> C[execution/engine.py]
B --> D[execution/contracts.py]
C --> E[docker]
C --> F[dagger]
B --> G[httpx]
B --> H[loguru]
style A fill:#f9f,stroke:#333
style B fill:#bbf,stroke:#333
style C fill:#f96,stroke:#333
style D fill:#f96,stroke:#333
style E fill:#9f9,stroke:#333
style F fill:#9f9,stroke:#333
style G fill:#9f9,stroke:#333
style H fill:#9f9,stroke:#333
```

**Diagram sources**
- [test_tool_execution.py](file://tests/integration/test_tool_execution.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [engine.py](file://src/praxis_sdk/execution/engine.py)

## Performance Considerations
The performance of tool execution testing is influenced by several factors:
- **Container Startup Time**: The time taken to start a Docker container can impact the overall execution time.
- **Network Latency**: For remote MCP servers, network latency can affect the response time.
- **Resource Limits**: The execution engines should enforce resource limits to prevent resource exhaustion.

To optimize performance, consider the following:
- Use caching for frequently used Docker images.
- Minimize the number of external tool invocations.
- Use efficient data serialization formats.

## Troubleshooting Guide
Common issues in tool execution testing include:
- **Tool Not Found**: Ensure that the tool is registered with the MCP server.
- **Invalid Arguments**: Validate the arguments against the tool contract schema.
- **Container Execution Failure**: Check the container logs for errors.
- **Network Issues**: Verify the network connectivity to remote MCP servers.

For debugging, enable verbose logging in the MCP server and execution engines to get detailed information about the execution process.

**Section sources**
- [test_tool_execution.py](file://tests/integration/test_tool_execution.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [engine.py](file://src/praxis_sdk/execution/engine.py)

## Conclusion
This document has provided a comprehensive analysis of tool execution testing in the Praxis Py SDK. It covers the key components, architecture, and dependencies involved in validating containerized tool invocation via MCP contracts and execution engine orchestration. By following the guidelines and best practices outlined in this document, developers can ensure that their tools are discovered, validated, and executed correctly in a secure and isolated environment.

**Referenced Files in This Document**   
- [test_tool_execution.py](file://tests/integration/test_tool_execution.py)
- [server.py](file://src/praxis_sdk/mcp/server.py)
- [engine.py](file://src/praxis_sdk/execution/engine.py)
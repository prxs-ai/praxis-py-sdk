# Dagger Engine



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
The Dagger Engine is a core component of the Praxis framework, providing secure, reproducible, and containerized execution of CI/CD pipelines. It leverages the Dagger Python SDK to execute tools within isolated container environments, ensuring consistent behavior across different execution contexts. This document details the implementation, integration, and operational characteristics of the Dagger execution engine within the Praxis ecosystem, focusing on its role in enabling reproducible builds and secure execution workflows.

## Project Structure
The project structure reveals a modular architecture with clear separation of concerns. The execution engine components are located under `src/praxis_sdk/execution/`, with core functionality implemented in `engine.py` and `contracts.py`. The `tools/` directory contains sample tools with contract definitions, while `tests/` includes comprehensive test coverage for the Dagger engine. Configuration files in `configs/` suggest a distributed agent architecture, and the presence of MCP (Multi-Component Protocol) modules indicates integration with external tooling systems.

```mermaid
graph TB
subgraph "Core Execution"
E[engine.py]
C[contracts.py]
end
subgraph "Testing"
T[test_dagger_engine.py]
end
subgraph "Configuration"
CFG[configs/]
end
subgraph "Tools"
TOOLS[tools/]
end
E --> C
T --> E
CFG --> E
TOOLS --> E
```

**Diagram sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py)
- [contracts.py](file://src/praxis_sdk/execution/contracts.py)
- [test_dagger_engine.py](file://tests/test_dagger_engine.py)

**Section sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py)
- [contracts.py](file://src/praxis_sdk/execution/contracts.py)

## Core Components
The core components of the Dagger engine implementation include the `DaggerExecutionEngine` class, the `ToolContract` model, and the execution lifecycle management system. These components work together to provide containerized execution with proper input/output mapping, resource isolation, and error handling. The engine supports multiple execution backends, with the primary implementation using the official Dagger Python SDK for maximum compatibility with the Dagger ecosystem.

**Section sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)
- [contracts.py](file://src/praxis_sdk/execution/contracts.py#L1-L378)

## Architecture Overview
The Dagger engine architecture follows a modular design with clear separation between contract definition, execution logic, and resource management. The system uses the Dagger Python SDK to create containerized execution environments, with tool contracts defining the execution parameters. The architecture supports multiple engine types, including Dagger, local, and remote execution, with automatic capability detection and engine selection.

```mermaid
graph TD
A[Tool Contract] --> B[DaggerExecutionEngine]
B --> C[Dagger SDK]
C --> D[Docker Engine]
E[Arguments] --> B
F[Context] --> B
B --> G[Execution Result]
H[LocalExecutionEngine] --> I[Subprocess]
J[DockerSDKExecutionEngine] --> D
B --> H
B --> J
```

**Diagram sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)
- [contracts.py](file://src/praxis_sdk/execution/contracts.py#L1-L378)

## Detailed Component Analysis

### DaggerExecutionEngine Analysis
The `DaggerExecutionEngine` class provides the primary implementation for containerized tool execution using the Dagger Python SDK. It handles the complete execution lifecycle from contract validation to result retrieval, with comprehensive logging and error handling.

#### For Object-Oriented Components:
```mermaid
classDiagram
class DaggerExecutionEngine {
+configure_connection(**options)
+execute(contract, args, context)
+validate_contract(contract)
+get_capabilities()
+cleanup()
-_prepare_environment_variables(spec, args, context)
-_export_modified_directories_dagger(exec_container, spec, client)
}
class ExecutionEngine {
<<abstract>>
+execute(contract, args, context)
+validate_contract(contract)
+get_capabilities()
+cleanup()
}
class LocalExecutionEngine {
+execute(contract, args, context)
+validate_contract(contract)
+get_capabilities()
+cleanup()
}
class DockerSDKExecutionEngine {
+execute(contract, args, context)
+validate_contract(contract)
+get_capabilities()
+cleanup()
}
class RemoteMCPEngine {
+execute(contract, args, context)
+validate_contract(contract)
+get_capabilities()
+cleanup()
}
DaggerExecutionEngine --|> ExecutionEngine
LocalExecutionEngine --|> ExecutionEngine
DockerSDKExecutionEngine --|> ExecutionEngine
RemoteMCPEngine --|> ExecutionEngine
```

**Diagram sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)

#### For API/Service Components:
```mermaid
sequenceDiagram
participant Client
participant Engine as DaggerExecutionEngine
participant Dagger as Dagger SDK
participant Docker as Docker Engine
Client->>Engine : execute(contract, args, context)
Engine->>Engine : validate_contract()
Engine->>Engine : get_typed_spec()
Engine->>Engine : _prepare_environment_variables()
Engine->>Dagger : dagger.Connection()
Dagger->>Docker : Connect to Docker daemon
Dagger->>Dagger : container().from_(image)
Engine->>Dagger : with_directory() for mounts
Engine->>Dagger : with_workdir()
Engine->>Dagger : with_env_variable()
Engine->>Dagger : with_exec(command)
Dagger->>Docker : Execute container
Docker->>Dagger : Return stdout/stderr
Dagger->>Engine : stdout()
Engine->>Engine : _export_modified_directories_dagger()
Engine->>Client : Return execution result
```

**Diagram sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)

### ToolContract Analysis
The `ToolContract` class defines the interface between the Praxis framework and executable tools, specifying execution parameters and requirements. It uses Pydantic models for validation and type safety, ensuring that contracts are properly structured before execution.

#### For Object-Oriented Components:
```mermaid
classDiagram
class ToolContract {
+engine : EngineType
+name : str
+engine_spec : Dict[str, Any]
+parameters : List[ToolParameter]
+description : Optional[str]
+version : Optional[str]
+get_typed_spec()
+create_dagger_tool()
+create_local_tool()
}
class DaggerEngineSpec {
+image : str
+command : List[str]
+mounts : Dict[str, str]
+env : Dict[str, str]
+env_passthrough : List[str]
+working_dir : Optional[str]
+timeout : int
+memory_limit : Optional[str]
+cpu_limit : Optional[float]
+network : Optional[str]
+privileged : bool
}
class LocalEngineSpec {
+command : List[str]
+shell : bool
+cwd : Optional[str]
+env : Dict[str, str]
+timeout : int
+capture_output : bool
}
class RemoteMCPEngineSpec {
+address : str
+timeout : int
+headers : Dict[str, str]
+auth_token : Optional[str]
}
class ToolParameter {
+name : str
+type : str
+description : str
+required : bool
+default : Any
}
ToolContract --> DaggerEngineSpec : "engine_spec"
ToolContract --> LocalEngineSpec : "engine_spec"
ToolContract --> RemoteMCPEngineSpec : "engine_spec"
ToolContract --> ToolParameter : "parameters"
```

**Diagram sources**
- [contracts.py](file://src/praxis_sdk/execution/contracts.py#L1-L378)

### Execution Lifecycle Analysis
The execution lifecycle follows a structured process from initialization to cleanup, with each step providing visibility through comprehensive logging. The engine implements a step-by-step execution process that ensures reproducibility and facilitates debugging.

#### For Complex Logic Components:
```mermaid
flowchart TD
Start([Execute Tool]) --> Validate["Validate Contract"]
Validate --> Parse["Parse Engine Spec"]
Parse --> PrepareEnv["Prepare Environment Variables"]
PrepareEnv --> Connect["Connect to Dagger Engine"]
Connect --> CreateContainer["Create Container from Image"]
CreateContainer --> Mount["Mount Directories"]
Mount --> SetWorkdir["Set Working Directory"]
SetWorkdir --> SetEnv["Apply Environment Variables"]
SetEnv --> Exec["Execute Command"]
Exec --> GetOutput["Retrieve Stdout/Stderr"]
GetOutput --> Export["Export Modified Directories"]
Export --> Return["Return Execution Result"]
Exec --> |Failure| HandleError["Handle Execution Error"]
HandleError --> Raise["Raise ExecutionError"]
```

**Diagram sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)

**Section sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)
- [contracts.py](file://src/praxis_sdk/execution/contracts.py#L1-L378)

## Dependency Analysis
The Dagger engine has a well-defined dependency structure with clear separation between core functionality and external integrations. The primary dependencies include the Dagger SDK, Docker SDK, and HTTPX for remote execution. The system uses optional imports to handle missing dependencies gracefully, providing fallback execution mechanisms when necessary.

```mermaid
graph TD
A[Dagger Engine] --> B[Dagger SDK]
A --> C[Docker SDK]
A --> D[HTTPX]
A --> E[Pydantic]
A --> F[Loguru]
B --> G[Docker Engine]
C --> G
D --> H[Remote MCP Server]
E --> I[Data Validation]
F --> J[Logging]
```

**Diagram sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)
- [contracts.py](file://src/praxis_sdk/execution/contracts.py#L1-L378)

**Section sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)
- [contracts.py](file://src/praxis_sdk/execution/contracts.py#L1-L378)

## Performance Considerations
The Dagger engine provides several performance characteristics that impact execution efficiency. Container startup overhead is present but mitigated by Docker's layer caching mechanism. The engine supports parallel execution through asynchronous processing, allowing multiple tools to run concurrently. Network efficiency is optimized through streaming of container output and minimal data transfer between host and container. Configuration options such as cache settings and resource limits allow fine-tuning of performance characteristics for specific use cases.

The engine implements several optimizations to improve performance:
- Cache-busting timestamps to prevent unwanted caching
- Pip cache mounting for Python environments
- Direct streaming of container output
- Asynchronous execution with timeout handling
- Efficient resource cleanup

These features ensure that the engine maintains high performance while providing reproducible and secure execution environments.

## Troubleshooting Guide
Common issues with the Dagger engine typically fall into several categories: connection failures, build step errors, and resource limits. The comprehensive logging system provides detailed information for diagnosing and resolving these issues.

**Section sources**
- [engine.py](file://src/praxis_sdk/execution/engine.py#L1-L1052)
- [test_dagger_engine.py](file://tests/test_dagger_engine.py#L1-L472)

### Connection Failures
Connection failures can occur due to several reasons:
- Missing Dagger CLI installation
- Docker daemon not running
- Network connectivity issues
- Permission problems with Docker socket

Solutions include:
- Installing the Dagger CLI: `pip install dagger-io`
- Ensuring Docker is running and accessible
- Checking network connectivity to remote services
- Verifying Docker socket permissions

### Build Step Errors
Build step errors typically manifest as container execution failures with non-zero exit codes. These can be caused by:
- Invalid commands or arguments
- Missing dependencies in the container image
- File permission issues
- Resource constraints

Debugging steps:
- Check container logs for detailed error messages
- Verify the base image contains required tools
- Ensure mounted directories have proper permissions
- Increase resource limits if necessary

### Resource Limits
Resource limitations can cause timeouts or out-of-memory errors. The engine provides configuration options to address these:
- Timeout settings in the tool contract
- Memory and CPU limits for containers
- Custom network configurations

Monitoring execution duration and resource usage can help identify appropriate limits for specific tools.

## Conclusion
The Dagger engine provides a robust foundation for CI/CD pipeline execution within the Praxis framework, enabling reproducible builds and secure execution through containerization. Its integration with the Dagger Python SDK ensures compatibility with the broader Dagger ecosystem while providing the flexibility to support multiple execution backends. The comprehensive contract system, detailed logging, and robust error handling make it a reliable choice for complex workflow orchestration. With proper configuration and monitoring, the engine delivers high performance and reliability for continuous integration and deployment workflows.

**Referenced Files in This Document**   
- [engine.py](file://src/praxis_sdk/execution/engine.py)
- [contracts.py](file://src/praxis_sdk/execution/contracts.py)
- [test_dagger_engine.py](file://tests/test_dagger_engine.py)
# Changelog

## [0.2.3](https://github.com/prxs-ai/praxis-py-sdk/compare/praxis-py-sdk-v0.2.2...praxis-py-sdk-v0.2.3) (2025-10-09)


### Features

* : [PRXS-371] :: Add metrics to /health route and push them to Prometheus ([#18](https://github.com/prxs-ai/praxis-py-sdk/issues/18)) ([a3b2364](https://github.com/prxs-ai/praxis-py-sdk/commit/a3b236433aa8ac0f4b0c1f25754872e61a0b8580))

## [0.2.2](https://github.com/prxs-ai/praxis-py-sdk/compare/praxis-py-sdk-v0.2.1...praxis-py-sdk-v0.2.2) (2025-10-01)


### Features

* : [PRXS-34] :: Implement KV Store ([#16](https://github.com/prxs-ai/praxis-py-sdk/issues/16)) ([25f38e8](https://github.com/prxs-ai/praxis-py-sdk/commit/25f38e853018fce65bbec1f2d4978b1f5d807e8a))

## [0.2.1](https://github.com/prxs-ai/praxis-py-sdk/compare/praxis-py-sdk-v0.2.0...praxis-py-sdk-v0.2.1) (2025-09-22)

### Features

#### **WebSocket Communication Enhancements**
* **Improved WebSocket Handling**: Enhanced WebSocket communication layer with better connection management
  - Fixed WebSocket server integration with FastAPI
  - Better error handling and connection lifecycle management
  - Improved real-time communication between agents and clients
  - Enhanced message routing and event broadcasting

#### **MCP Server Streamable Support**
* **Enhanced MCP Integration**: Added streamable support for Model Context Protocol servers
  - Improved MCP server lifecycle management
  - Better integration with external MCP filesystem servers
  - Enhanced tool registry with dynamic server discovery
  - Streamable data processing support for large datasets

#### **Agent-to-Agent Protocol Improvements**
* **Enhanced A2A Communication**: Significant improvements to Agent-to-Agent protocol implementation
  - Better task delegation and management between agents
  - Improved agent capability broadcasting and discovery
  - Enhanced peer-to-peer communication reliability
  - Better error handling and fault tolerance in multi-agent scenarios

#### **API Server Architecture Enhancements**
* **Robust API Layer**: Major improvements to the HTTP API server implementation
  - Better request handling and response formatting
  - Enhanced endpoint security and validation
  - Improved server startup and shutdown procedures
  - Better integration with WebSocket and SSE endpoints

### Improvements

#### **Configuration Management**
* **Enhanced Config System**: Improved configuration handling across all components
  - Better environment variable management
  - Enhanced YAML configuration validation
  - Improved agent-specific configuration support
  - Better default value handling and overrides

#### **Event Bus System**
* **Event Handling Improvements**: Enhanced event bus for better component communication
  - Improved event routing and dispatching
  - Better error handling in event processing
  - Enhanced debugging and monitoring capabilities

#### **P2P Service Enhancements**
* **Peer-to-Peer Networking**: Improvements to libp2p service integration
  - Better peer discovery and connection management
  - Enhanced protocol handling and message routing
  - Improved service lifecycle management
  - Better integration with agent communication layer

### Bug Fixes

* **Tool Execution**: Fixed issues with GPT rewriter tool implementation
* **Docker Configuration**: Updated Docker Compose configuration for better multi-agent deployment
* **File Structure**: Cleaned up project structure by removing unnecessary placeholder files

### Technical Improvements

* **Code Quality**: Significant refactoring with improved code organization and structure
  - Better separation of concerns across modules
  - Enhanced error handling and logging
  - Improved type hints and documentation
  - Better async/await patterns implementation

### Infrastructure Changes

* **Release Process**: Removed hardcoded release-please configuration for better automation
* **Project Structure**: Cleaned up data and shared directories for better organization

### Documentation

* changelog 020 ([#9](https://github.com/prxs-ai/praxis-py-sdk/issues/9)) ([c254309](https://github.com/prxs-ai/praxis-py-sdk/commit/c2543099aec9966b15b2eba920c7be7baeb078d1))

---

**Technical Details:**
- **Key Components Modified**: API server, WebSocket handler, A2A protocol, MCP integration, agent core
- **Performance**: Improved WebSocket connection handling and MCP server communication
- **Reliability**: Enhanced error handling and fault tolerance across all communication layers

## [0.2.0](https://github.com/prxs-ai/praxis-py-sdk/compare/praxis-py-sdk-v0.2.0...praxis-py-sdk-v0.2.0) (2025-09-10)


### Documentation

* changelog 020 ([#9](https://github.com/prxs-ai/praxis-py-sdk/issues/9)) ([c254309](https://github.com/prxs-ai/praxis-py-sdk/commit/c2543099aec9966b15b2eba920c7be7baeb078d1))

## [0.2.0](https://github.com/prxs-ai/praxis-py-sdk/compare/praxis-py-sdk-v0.1.0...praxis-py-sdk-v0.2.0) (2025-09-10)

### Major New Features

#### **Agent-to-Agent (A2A) Protocol Implementation**
- **Distributed Task Management**: Complete A2A protocol for agent communication over libp2p network
  - Task delegation and handoff between autonomous agents
  - Agent capability advertisement and discovery
  - Secure peer-to-peer communication channels
  - Load balancing across agent network
- **Agent Cards Exchange**: Structured agent capability sharing
  - Automatic tool and skill broadcasting
  - Dynamic agent network topology
  - Fault-tolerant agent discovery

#### **Enhanced Dagger Execution Engine**
- **Container-Based Tool Execution**: Improved Dagger integration for secure tool execution
  - Full container isolation for tool processing
  - Environment variable pass-through for configuration
  - Shared volume support for data workflows
  - Better error handling and logging
- **Multi-Engine Support**: Flexible execution engine architecture
  - Dagger Engine for containerized execution
  - Docker SDK Engine for direct container management
  - Local Engine for lightweight in-process tools
  - Remote MCP Engine for external integrations

#### **Comprehensive Documentation System**
- **Developer Documentation**: Complete documentation overhaul with detailed guides
  - API reference documentation with examples
  - Architecture deep-dive explanations
  - Getting started tutorials and quick start guides
  - Tool development and integration guides
- **README Enhancement**: Extensive README with installation, configuration, and usage examples
  - Multi-agent deployment scenarios
  - Docker Compose configurations
  - Development workflow documentation

### Improvements

#### **P2P Networking & Communication**
- **Trio Async Framework**: Migration to structured concurrency with Trio
  - Better async/await patterns throughout codebase  
  - Improved error handling and cancellation
  - More reliable P2P service integration
  - Enhanced WebSocket and SSE communication
- **libp2p Integration**: Native peer-to-peer networking improvements
  - Better peer discovery with mDNS support
  - DHT integration for global agent discovery
  - Secure communication protocol handling

#### **Model Context Protocol (MCP) Enhancements**  
- **MCP Service Architecture**: Improved MCP server management and client pooling
  - Dynamic MCP server discovery and registration
  - Better tool registry with capability caching
  - External MCP server integration support
  - Improved transport layer reliability

#### **Developer Experience**
- **Pre-commit Integration**: Complete pre-commit hooks setup
  - Black code formatting enforcement
  - Ruff linting with comprehensive rule set
  - mypy type checking with strict mode
  - YAML validation and file consistency checks
- **Poetry Configuration**: Modern Python dependency management
  - Lock file management for reproducible builds
  - Development vs production dependency separation
  - CLI entry point configuration

### Technical Enhancements

#### **Configuration System**
- **YAML Configuration**: Comprehensive configuration management with Pydantic validation
  - Environment-specific configurations
  - Runtime configuration override support
  - Secure credential management
  - Multi-agent deployment configurations

#### **Event-Driven Architecture**
- **Event Bus Implementation**: Robust event system for component communication
  - Async event dispatching and routing
  - Event history and debugging support
  - Component lifecycle management
  - Real-time monitoring and health checks

#### **LLM Integration & Workflow Planning**
- **OpenAI Integration**: Enhanced LLM capabilities for intelligent agent behavior
  - GPT-4 and GPT-3.5 model support
  - Workflow planning and task decomposition
  - Context management for complex workflows
  - Function calling for structured tool invocation

### Bug Fixes

- **CI/CD Pipeline**: Fixed continuous integration and deployment issues
  - GitHub Actions workflow corrections
  - Automated testing and validation
  - Release automation with semantic versioning
- **Dependency Management**: Resolved Poetry lock file conflicts and version issues
  - Updated dependency versions for security
  - Fixed package resolution conflicts
  - Improved build reproducibility
- **Service Integration**: Fixed Ray service integration and deployment issues
  - Better service discovery and health monitoring
  - Improved container orchestration
  - Enhanced logging and debugging capabilities

### Documentation & Tooling

- **Comprehensive Docstrings**: Added detailed documentation for core utility functions
  - Type hints and parameter documentation
  - Usage examples and code samples
  - API reference generation ready
- **README Improvements**: Enhanced formatting and expanded Quick Start section
  - Docker deployment examples
  - Multi-agent setup instructions
  - Development workflow guidance
  - Troubleshooting and FAQ sections

### Infrastructure

- **Makefile Commands**: Complete set of development and deployment commands
  - Setup, build, and testing automation
  - Docker Compose orchestration shortcuts
  - Code quality and linting commands
  - Development environment management
- **Docker Configuration**: Production-ready containerization
  - Multi-stage builds for optimized images
  - Development and production Docker Compose files
  - Health checks and monitoring integration
  - Shared volume configurations for data processing

---

### Breaking Changes

- **Async Framework Migration**: Updated from asyncio to Trio for structured concurrency
  - Existing async code may need updates for Trio compatibility
  - Better cancellation and error handling patterns required
  - See migration guide for async code updates

---

### Technical Reference

**Commits included in this release:**
- feat: add A2A protocol implementation and fix bugs with Dagger execution ([b906597](https://github.com/prxs-ai/praxis-py-sdk/commit/b906597d83aded72c123235b7c380109e6e70bd8))
- feat: add docs for praxis-python-sdk ([62e2af4](https://github.com/prxs-ai/praxis-py-sdk/commit/62e2af4108ecee41d6b4192d5dfa8e5500ff36b0))
- feat: complete pre-commit setup per DoD requirement ([8766818](https://github.com/prxs-ai/praxis-py-sdk/commit/876681840f5a7d5297cc1f8849c4d7d529909afa))
- fix: cicd ([5a5ed1c](https://github.com/prxs-ai/praxis-py-sdk/commit/5a5ed1c08215514ce5b1070ccfdfb8dcaec58aa1))
- docs: Add comprehensive docstrings for core utility functions ([91fbdf6](https://github.com/prxs-ai/praxis-py-sdk/commit/91fbdf6ad23fac9deb08757ed5a722d854c1d892))

---

## 0.1.0 (Initial Release)

Initial release of Praxis Python SDK with core P2P networking, basic agent communication, and foundational distributed agent platform features.

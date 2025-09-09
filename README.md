# Praxis Python SDK

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Poetry](https://img.shields.io/badge/poetry-1.0+-blue.svg)](https://python-poetry.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Trio](https://img.shields.io/badge/async-trio-green.svg)](https://trio.readthedocs.io)

A comprehensive Python implementation of the Praxis distributed agent platform featuring peer-to-peer communication, agent-to-agent protocols, and seamless tool ecosystem integration.

## Overview

Praxis SDK is a sophisticated distributed agent framework designed for building autonomous, collaborative systems. It combines modern async Python with cutting-edge technologies like libp2p networking, MCP (Model Context Protocol) tool integration, and containerized execution engines to create a robust platform for multi-agent workflows.

The SDK enables agents to discover each other, communicate securely, share capabilities, and execute complex tasks through a unified interface while maintaining full autonomy and scalability.

## Key Features

### 🌐 **Distributed P2P Architecture**

- **libp2p Integration**: Native peer-to-peer networking with secure communication channels
- **mDNS Discovery**: Automatic agent discovery within local networks
- **DHT Support**: Distributed hash table for global agent discovery
- **Multi-Protocol Support**: Flexible protocol handling for different communication patterns

### 🤖 **Agent-to-Agent (A2A) Protocol**

- **Capability Broadcasting**: Agents automatically share their available tools and skills
- **Task Delegation**: Intelligent routing of tasks to the most suitable agents
- **Load Balancing**: Automatic distribution of workload across agent network
- **Fault Tolerance**: Graceful handling of agent failures and network partitions

### 🛠️ **Comprehensive Tool Ecosystem**

- **MCP Integration**: Seamless integration with Model Context Protocol servers
- **Dagger Execution**: Containerized tool execution with dependency isolation
- **Local Execution**: Direct Python tool execution for simple tasks
- **Remote Tools**: Integration with external HTTP-based tool services

### 🚀 **Multiple Execution Engines**

- **Dagger Engine**: Container-based execution with full isolation
- **Docker SDK Engine**: Direct Docker container management
- **Local Engine**: Fast in-process execution for lightweight tools
- **Remote MCP Engine**: Integration with external MCP servers

### 📡 **Rich Communication Interfaces**

- **HTTP API**: RESTful interface for external integration
- **WebSocket**: Real-time bidirectional communication
- **Server-Sent Events**: Streaming updates and notifications
- **P2P Protocols**: Direct agent-to-agent communication

### 🧠 **LLM Integration**

- **OpenAI Integration**: GPT-4, GPT-3.5, and other OpenAI models
- **Workflow Planning**: Intelligent task decomposition and planning
- **Context Management**: Smart context building for complex workflows
- **Function Calling**: Structured tool invocation through LLM

## Architecture Overview

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Praxis Agent  │    │   Event Bus     │    │  Config System  │
│                 │    │                 │    │                 │
│ - Lifecycle Mgmt│    │ - Event Routing │    │ - YAML Configs  │
│ - Component Coord│   │ - Async Dispatch│    │ - Env Variables │
│ - Health Monitor│    │ - Event History │    │ - Validation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   P2P Service   │    │   API Server    │    │  MCP Service    │
│                 │    │                 │    │                 │
│ - libp2p Core   │    │ - HTTP/WS API   │    │ - Tool Registry │
│ -               │    │ - SSE Streaming │    │ - Server Mgmt   │
│ - Protocol Mgmt │    │ - Health Checks │    │ - Client Pool   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  A2A Protocol   │    │ Execution Engines│    │   DSL Engine    │
│                 │    │                 │    │                 │
│ - Task Manager  │    │ - Dagger Engine │    │ - Workflow Parse│
│ - Agent Cards   │    │ - Docker Engine │    │ - Plan Execute  │
│ - Capabilities  │    │ - Local Engine  │    │ - LLM Integration│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Communication Flow

1. **Agent Discovery**: Agents use mDNS and DHT to discover peers
2. **Capability Exchange**: Agents share their tool capabilities via A2A protocol
3. **Task Distribution**: Complex tasks are decomposed and distributed to suitable agents
4. **Tool Execution**: Tools run in isolated environments using various execution engines
5. **Result Aggregation**: Results are collected and processed through the event bus

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry (recommended) or pip
- Docker (for containerized tool execution)
- Git

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/prxs-ai/praxis-py-sdk.git
cd praxis-py-sdk

# Install dependencies with Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/prxs-ai/praxis-py-sdk.git
cd praxis-py-sdk

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Docker Installation

```bash
# Build the Docker image
docker build -t praxis-sdk .

# Or use Docker Compose for multi-agent setup
docker-compose up
```

## Quick Start Guide

### 1. Basic Agent Setup

```python
from praxis_sdk import PraxisAgent, load_config

# Load configuration
config = load_config("configs/agent1.yaml")

# Create and start agent
agent = PraxisAgent(config, agent_name="my-agent")

# Run the agent
import trio
trio.run(agent.run)
```

### 2. Running with Docker Compose

```bash
# Start multi-agent environment
docker-compose up

# Access agent APIs
curl http://localhost:8000/health  # Agent 1
curl http://localhost:8001/health  # Agent 2
```

### 3. Executing Tools

```python
# Via HTTP API
import httpx

response = httpx.post("http://localhost:8000/api/tools/execute", json={
    "tool_name": "calculator",
    "params": {"expression": "2 + 2 * 3"}
})
print(response.json())
```

### 4. Agent-to-Agent Communication

```python
# Agents automatically discover and communicate
# Tasks are routed to agents with appropriate capabilities

# Example: Text analysis task routed to agent with text_analyzer tool
response = httpx.post("http://localhost:8000/api/tasks/execute", json={
    "task": "analyze the sentiment of this text: 'Hello world!'",
    "preferred_agent": "praxis-agent-1"
})
```

## Configuration

### Agent Configuration (`configs/agent1.yaml`)

```yaml
agent:
  name: "praxis-agent-1"
  version: "1.0.0"
  description: "Primary agent with full tool suite"
  tools:
    - name: "calculator"
      description: "Mathematical calculations"
      engine: "dagger"
      params:
        - name: "expression"
          type: "string"
          required: true

p2p:
  enabled: true
  port: 4001
  secure: true
  enable_mdns: true
  protocols:
    - "/praxis/a2a/1.0.0"

mcp:
  enabled: true
  servers:
    - name: "filesystem"
      command: ["npx", "@modelcontextprotocol/server-filesystem", "/shared"]

llm:
  provider: "openai"
  model: "gpt-4o-mini"
  max_tokens: 4096
  temperature: 0.1
```

### Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Agent Configuration
AGENT_NAME=praxis-agent-1
CONFIG_FILE=/app/configs/agent1.yaml

# P2P Configuration
PRAXIS_P2P__PORT=4001
PRAXIS_P2P__ENABLED=true

# API Configuration
PRAXIS_API__PORT=8000
PRAXIS_WEBSOCKET__PORT=8090

# Logging
PRAXIS_LOGGING__LEVEL=debug
```

## Tool Ecosystem

The Praxis SDK includes a rich ecosystem of pre-built tools:

### Text Processing Tools

- **text_analyzer**: Analyzes text files for character and word counts
- **word_counter**: Counts words, lines, and characters
- **gpt_rewriter**: Rewrites text using GPT-4 with specified tone/style
- **text_summarizer**: Generates concise summaries of long texts

### Data Processing Tools

- **json_formatter**: Formats and beautifies JSON data
- **file_merger**: Merges multiple text files with customizable separators
- **python_data_processor**: Processes data using custom Python scripts

### Utility Tools

- **calculator**: Performs mathematical calculations and expressions
- **system_info**: Provides detailed system information
- **keyword_extractor**: Extracts key terms and phrases from text

### External Integration Tools

- **twitter_scraper**: Scrapes Twitter/X using Apify API
- **web_search**: Searches the web and returns formatted results

### Creating Custom Tools

```python
# tools/my_tool/main.py
import os
import json

def main():
    # Get parameters from environment
    input_text = os.getenv('INPUT_TEXT', '')
  
    # Process the input
    result = process_text(input_text)
  
    # Return JSON result
    print(json.dumps({
        "status": "success",
        "result": result,
        "metadata": {"tool": "my_tool"}
    }))

def process_text(text):
    return text.upper()

if __name__ == "__main__":
    main()
```

```yaml
# tools/my_tool/contract.yaml
name: "my_tool"
description: "Converts text to uppercase"
engine: "dagger"
params:
  - name: "input_text"
    type: "string"
    description: "Text to convert"
    required: true
engineSpec:
  image: "python:3.11-slim"
  command: ["python", "/tools/my_tool/main.py"]
  mounts:
    ./tools: /tools
  env_passthrough: ["INPUT_TEXT"]
```

## Development Setup

### Local Development

```bash
# Clone and setup
git clone https://github.com/prxs-ai/praxis-py-sdk.git
cd praxis-py-sdk
poetry install

# Setup pre-commit hooks
poetry run pre-commit install

# Run linting
poetry run black src/ tests/
poetry run isort src/ tests/
poetry run mypy src/
poetry run ruff check src/
```

### Development with Docker

```bash
# Build development image
docker build -f Dockerfile.simple -t praxis-dev .

# Run development container
docker run -it --rm \
  -v $(pwd):/app \
  -p 8000:8000 \
  praxis-dev bash
```

### Hot Reload Development

```bash
# Use docker-compose for development with hot reload
docker-compose -f docker-compose.dev.yml up
```

## Testing

### Running Unit Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=praxis_sdk --cov-report=html

# Run specific test categories
poetry run pytest tests/test_event_bus.py
poetry run pytest tests/integration/
```

### Integration Tests

```bash
# Start test environment
docker-compose up -d

# Run integration tests
poetry run pytest tests/integration/ -v

# Test P2P connectivity
poetry run pytest tests/integration/test_p2p_connectivity.py

# Test multi-agent communication
poetry run pytest tests/integration/test_multi_agent_communication.py
```

### Load Testing

```bash
# Test agent performance under load
poetry run pytest tests/test_load_performance.py

# Test P2P network resilience
poetry run pytest tests/integration/test_network_resilience.py
```

## Docker Deployment

### Single Agent Deployment

```dockerfile
# Dockerfile.simple
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install poetry && poetry install --no-dev

EXPOSE 8000 8090 4001
CMD ["poetry", "run", "praxis-agent", "configs/agent1.yaml", "praxis-agent-1"]
```

```bash
# Build and run
docker build -f Dockerfile.simple -t praxis-agent .
docker run -p 8000:8000 -p 4001:4001 praxis-agent
```

### Multi-Agent Deployment

```bash
# Deploy full agent network
docker-compose up -d

# Scale agents
docker-compose up -d --scale praxis-agent-1=3

# Monitor logs
docker-compose logs -f praxis-agent-1
```

### Production Deployment

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  praxis-agent:
    image: praxis-sdk:latest
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    environment:
      - PRAXIS_ENVIRONMENT=production
      - PRAXIS_LOGGING__LEVEL=info
    networks:
      - praxis-production
    volumes:
      - praxis-data:/app/data
      - praxis-logs:/app/logs
```

## API Documentation

### REST API Endpoints

#### Health Check

```http
GET /health
```

#### Agent Information

```http
GET /api/agent/info
GET /api/agent/capabilities
```

#### Tool Execution

```http
POST /api/tools/execute
Content-Type: application/json

{
  "tool_name": "calculator",
  "params": {
    "expression": "2 + 2 * 3"
  }
}
```

#### Task Management

```http
POST /api/tasks/execute
GET /api/tasks/{task_id}
GET /api/tasks/{task_id}/status
```

#### P2P Network

```http
GET /api/p2p/peers
GET /api/p2p/protocols
POST /api/p2p/connect
```

### WebSocket API

```javascript
// Connect to agent WebSocket
const ws = new WebSocket('ws://localhost:8090');

// Subscribe to events
ws.send(JSON.stringify({
  type: 'subscribe',
  events: ['tool_execution', 'p2p_discovery', 'task_updates']
}));

// Execute tool via WebSocket
ws.send(JSON.stringify({
  type: 'tool_execute',
  tool_name: 'calculator',
  params: { expression: '2 + 2' }
}));
```

### Server-Sent Events

```javascript
// Subscribe to real-time updates
const eventSource = new EventSource('http://localhost:9000/api/events');

eventSource.addEventListener('tool_result', (event) => {
  const result = JSON.parse(event.data);
  console.log('Tool result:', result);
});

eventSource.addEventListener('p2p_peer_discovered', (event) => {
  const peer = JSON.parse(event.data);
  console.log('New peer discovered:', peer);
});
```

## Contributing

We welcome contributions to the Praxis SDK! Here's how to get started:

### Development Workflow

1. **Fork the repository** and create a feature branch
2. **Make your changes** following our coding standards
3. **Add tests** for any new functionality
4. **Run the test suite** to ensure everything works
5. **Submit a pull request** with a clear description

### Coding Standards

- **Python Style**: Follow PEP 8, enforced by Black and isort
- **Type Hints**: Use type hints for all public APIs
- **Documentation**: Add docstrings for all public functions and classes
- **Testing**: Maintain test coverage above 85%

### Pull Request Process

1. Ensure all tests pass: `poetry run pytest`
2. Check code formatting: `poetry run black --check src/`
3. Verify type checking: `poetry run mypy src/`
4. Update documentation as needed
5. Add entry to CHANGELOG.md

### Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [docs.praxis.ai](https://docs.praxis.ai)
- **GitHub Issues**: [Report bugs and request features](https://github.com/prxs-ai/praxis-py-sdk/issues)
- **Community**: [Join our Discord server](https://discord.gg/praxis-ai)
- **Email**: [team@praxis.ai](mailto:team@praxis.ai)

---

Built with ❤️ by the Praxis Team

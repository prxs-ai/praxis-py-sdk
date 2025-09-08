# Praxis Python SDK

A powerful Python SDK for building distributed AI agent networks with P2P communication, workflow orchestration, and tool sharing capabilities.

## 🚀 What is Praxis Python SDK?

The Praxis Python SDK enables developers to create **distributed multi-agent systems** where AI agents can:
- 🤝 **Discover each other** automatically through P2P networking
- 🔧 **Share tools and capabilities** using the Model Context Protocol (MCP)
- 💬 **Execute workflows** through natural language or Domain Specific Language (DSL)
- 📁 **Collaborate on tasks** like data processing, social media management, and financial analysis
- 🧠 **Integrate with LLMs** for intelligent decision-making and plan generation

## ✨ Key Features

- 🔗 **P2P Agent Network** - Automatic peer discovery and secure communication via libp2p
- 🧠 **LLM Integration** - Natural language to executable workflows with OpenAI GPT-4
- 🔧 **MCP Protocol** - Seamless tool sharing between agents
- ⚡ **Ray Serve Integration** - Scalable deployment with Ray framework
- 🐍 **Type-Safe** - Full type hints and MyPy support
- 📦 **Modular Architecture** - 25+ specialized packages for different domains
- 🔄 **Async-First** - Built for high-performance asynchronous operations
- 🧪 **Comprehensive Testing** - Full test coverage with pytest

## 🏃 Quick Start

### 1. Installation

```bash
# Install with uv (recommended)
uv add praxis-py-sdk

# Or with pip
pip install praxis-py-sdk
```

### 2. Create Your First Agent

```python
from praxis_sdk.agents import AbstractAgent
from praxis_sdk.agents.models import AgentModel, ToolModel

class MyAgent(AbstractAgent):
    """A simple example agent."""
    
    def __init__(self):
        super().__init__()
        self.name = "my-agent"
    
    async def execute_workflow(self, prompt: str) -> str:
        """Execute a workflow based on natural language prompt."""
        # Your agent logic here
        return f"Processed: {prompt}"

# Bootstrap and deploy
from praxis_sdk.agents.bootstrap import bootstrap_main
DeploymentClass = bootstrap_main(MyAgent)
```

### 3. Deploy with Ray Serve

```python
import ray
from ray import serve

# Start Ray
ray.init()
serve.start()

# Deploy your agent
serve.run(DeploymentClass.bind())
```

### 4. Test Your Agent

```bash
# Health check
curl http://localhost:8000/health

# Execute workflow
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analyze the latest market data"}'
```

## 🏗️ Architecture Overview

```
Frontend/API ←→ Agent Network ←→ P2P Discovery
     ↓              ↓                 ↓
  FastAPI      Ray Serve         libp2p Network
     ↓              ↓                 ↓
 Workflow      Agent Cards      MCP Protocol
 Executor      & Skills         Tool Sharing
     ↓              ↓                 ↓
  LLM Client   Task Planning   Remote Execution
```

### Core Components

**Agent Framework:**
- `AbstractAgent` - Base class for all agents
- `AbstractWorkflowRunner` - Workflow execution engine
- `AbstractAgentCard` - Agent capability description
- `AbstractAgentP2PManager` - P2P network management

**Tool Ecosystem:**
- `ToolModel` - Tool definition with parameters and specifications
- `Workflow` - Task execution pipeline
- `AgentModel` - Agent metadata and capabilities

## 📦 Available Packages

### Infrastructure & Core
```python
# Configuration and shared utilities
from praxis_sdk.packages.infra_configs import get_config
from praxis_sdk.packages.shared_utils import async_retry
from praxis_sdk.packages.redis_client import RedisClient
from praxis_sdk.packages.s3_service import S3Service
```

### AI & Machine Learning
```python
# AI tools and LLM integration
from praxis_sdk.packages.ai_tools import check_answer_is_needed
from praxis_sdk.packages.send_openai_request import send_openai_request
from praxis_sdk.packages.creativity_schemas import CreativeTask
```

### Social Media Integration
```python
# Twitter/X integration
from praxis_sdk.packages.twitter_follow import follow_user
from praxis_sdk.packages.tweetscout_utils import analyze_tweet
from praxis_sdk.packages.tik_tok_package import TikTokClient
```

### Financial & Trading
```python
# Cryptocurrency and trading data
from praxis_sdk.packages.coingecko_client import CoinGeckoClient
from praxis_sdk.packages.hyperliquid_client import HyperliquidClient
from praxis_sdk.packages.dexscreener_wrapper import get_token_data
from praxis_sdk.packages.rugcheck_wrapper import check_token_safety
```

### Data & Analytics
```python
# Vector database and analytics
from praxis_sdk.packages.qdrant_client_custom import QdrantClient
from praxis_sdk.packages.agents_tools_logger import setup_logger
```

## 🔧 Development Setup

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup Instructions

```bash
# Clone the repository
git clone https://github.com/prxs-ai/praxis-py-sdk.git
cd praxis-py-sdk

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy .
```

## 📋 Environment Variables

### Required
```bash
# Agent identification
AGENT_NAME=my-praxis-agent

# Optional but recommended
OPENAI_API_KEY=sk-your-openai-key-here
```

### Optional Configuration
```bash
# Networking
HTTP_PORT=8000
P2P_PORT=4000
WEBSOCKET_PORT=9100

# Logging
LOG_LEVEL=info

# Features
MCP_ENABLED=true
RAY_SERVE_ENABLED=true
```

## 🚀 Advanced Usage

### Creating Custom Tools

```python
from praxis_sdk.agents.models import ToolModel

# Define tool specification
weather_tool = ToolModel(
    name="get_weather@1.0.0",
    openai_function_spec={
        "name": "get_weather",
        "description": "Get weather information for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or coordinates"
                }
            },
            "required": ["location"]
        }
    }
)

# Register tool with agent
class WeatherAgent(AbstractAgent):
    def __init__(self):
        super().__init__()
        self.tools = [weather_tool]
    
    async def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        if tool_name == "get_weather":
            return await self.get_weather(parameters["location"])
```

### P2P Network Configuration

```python
from praxis_sdk.agents.p2p import p2p_builder

# Create P2P manager
p2p_manager = p2p_builder()

# Configure peer discovery
await p2p_manager.start_discovery()

# List connected peers
peers = await p2p_manager.get_peers()
print(f"Connected to {len(peers)} peers")

# Share tools with network
await p2p_manager.share_agent_card(my_agent.get_card())
```

### Workflow Orchestration

```python
from praxis_sdk.agents.orchestration import workflow_builder

# Create workflow runner
workflow_runner = workflow_builder()

# Execute natural language workflow
result = await workflow_runner.execute(
    prompt="Analyze the sentiment of recent tweets about Bitcoin and create a summary report",
    agent_context=my_agent
)
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=praxis_sdk --cov-report=html

# Run specific test categories
uv run pytest tests/agents/
uv run pytest tests/packages/
```

### Example Test
```python
import pytest
from praxis_sdk.agents import AbstractAgent

@pytest.mark.asyncio
async def test_agent_execution():
    agent = MyAgent()
    result = await agent.execute_workflow("Hello world")
    assert "Processed" in result
```

## 📊 Monitoring & Logging

### Structured Logging
```python
from praxis_sdk.packages.agents_tools_logger import setup_logger

logger = setup_logger("my-agent")
logger.info("Agent started", agent_id="agent-123")
logger.error("Failed to process workflow", error=str(e))
```

### Health Monitoring
```python
# Built-in health endpoints
GET /health        # Agent health status
GET /peers        # Connected P2P peers
GET /p2p/cards    # Available agent capabilities
GET /metrics      # Performance metrics
```

## 🔍 API Reference

### Core Classes

#### AbstractAgent
```python
class AbstractAgent(ABC):
    """Base class for all Praxis agents."""
    
    @abstractmethod
    async def execute_workflow(self, prompt: str) -> str:
        """Execute a workflow from natural language."""
    
    async def get_card(self) -> AgentModel:
        """Get agent capabilities and metadata."""
    
    async def register_tool(self, tool: ToolModel) -> None:
        """Register a new tool with the agent."""
```

#### ToolModel
```python
class ToolModel(BaseModel):
    """Represents a tool that agents can use."""
    
    name: str                                    # Tool identifier
    version: str | None                          # Tool version
    default_parameters: dict[str, Any] | None    # Default parameters
    parameters_spec: dict[str, Any] | None       # Parameter schema
    openai_function_spec: dict[str, Any]         # OpenAI function spec
```

### HTTP API Endpoints

#### Agent Management
- `GET /health` - Health check and status
- `POST /execute` - Execute workflow from prompt
- `GET /capabilities` - List agent capabilities

#### P2P Network
- `GET /peers` - List connected peers
- `GET /p2p/cards` - Get peer agent cards
- `POST /p2p/message` - Send message to peer

#### Tools & Workflows
- `GET /tools` - List available tools
- `POST /tools/execute` - Execute specific tool
- `GET /workflows` - List workflow history

## 🚀 Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync --frozen

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "my_agent.main"]
```

### Ray Cluster Setup
```bash
# Start Ray head node
ray start --head --port=6379

# Deploy agents
uv run python deploy_agents.py

# Monitor cluster
ray dashboard
```

### Environment Configuration
```yaml
# docker-compose.yml
version: '3.8'
services:
  praxis-agent:
    build: .
    environment:
      - AGENT_NAME=praxis-agent-1
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - RAY_ADDRESS=ray://ray-cluster:10001
    ports:
      - "8000:8000"
      - "4000:4000"
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](docs/CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes following our code style
4. Run tests: `uv run pytest`
5. Run linting: `uv run ruff check . --fix`
6. Submit a pull request

### Code Style
- **Type Safety**: All code must have type hints
- **Testing**: New features require tests
- **Documentation**: Update docstrings for new APIs
- **Linting**: Code must pass ruff and mypy checks

## 📚 Documentation

- 📖 [API Documentation](docs/api/) - Comprehensive API reference
- 🏗️ [Architecture Guide](docs/ARCHITECTURE.md) - System design details
- 🧪 [Testing Guide](docs/TESTING.md) - Testing best practices
- 🚀 [Deployment Guide](docs/DEPLOYMENT.md) - Production setup
- 💡 [Examples](examples/) - Sample implementations

## 🆘 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/prxs-ai/praxis-py-sdk/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/prxs-ai/praxis-py-sdk/discussions)
- 📖 **Documentation**: [docs.prxs.ai](https://docs.prxs.ai)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

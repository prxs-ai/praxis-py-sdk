# BaseAgent

`BaseAgent` is a foundational agent implementation designed to be used in a modular Multi-Agent System (MAS) environment. It supports planning, execution, memory, intent recognition, and agent/tool coordination.

## Features

- Goal-oriented planning and execution
- Integration with AI Registry and LightRAG for knowledge retrieval
- Redis-based memory storage for interactions and chat sessions
- Support for tool and agent discovery
- Reconfigurable via chat prompts
- Supports contextual chat with memory
- Can add knowledge to its internal knowledge base

## Components

- **Executor**: Generates plans and classifies intents
- **Prompt Builder**: Generates prompts for various internal tasks
- **AI Registry Client**: Finds relevant agents and tools
- **LightRAG Client**: Provides domain-specific insights
- **Memory Client**: Stores and retrieves historical data

## Key Methods

- `handle(goal, plan, context)`: Main entrypoint to process goals
- `generate_plan(...)`: Creates a workflow based on available resources
- `chat(user_prompt, action, session_uuid)`: Handles interactive chat with optional configuration or knowledge update actions
- `store_knowledge(filename, content)`: Adds new information to the knowledge base

## Usage

The agent is intended to be deployed as part of a Ray Serve application and can be extended with custom workflows, tools, and domain knowledge.

## Requirements

- Python 3.10+
- Ray Serve
- Redis
- LightRAG and AI Registry services

## License

Proprietary / Internal Use Only (modify as appropriate)

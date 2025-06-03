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

## Development Setup

### Installing & Running Pre-commit

This repository uses pre-commit hooks to ensure code quality and consistency. Pre-commit automatically runs formatting, linting, and type checking before each commit.

#### Installation

1. **Install dependencies** (includes pre-commit, ruff, and mypy):
   ```bash
   poetry install --with dev
   ```

2. **Install pre-commit hooks**:
   ```bash
   poetry run pre-commit install
   ```

3. **Optional: Install pre-push hooks** (recommended):
   ```bash
   poetry run pre-commit install --hook-type pre-push
   ```

#### Usage

- **Automatic**: Pre-commit runs automatically on `git commit`
- **Manual**: Run on all files with:
  ```bash
  poetry run pre-commit run --all-files
  ```
- **Skip hooks** (not recommended):
  ```bash
  git commit --no-verify
  ```

#### What it checks

- **YAML syntax** and file formatting
- **Trailing whitespace** and end-of-file fixes
- **Merge conflict** markers
- **Large files** prevention
- **Ruff linting & formatting** (replaces black, flake8, isort)
- **MyPy type checking** with strict mode

#### Configuration

Pre-commit configuration is in `.pre-commit-config.yaml`. Ruff and MyPy settings are in `pyproject.toml`.

The configuration allows `print()` and `pprint()` statements and is tuned to work well with this project's style.

## License

Proprietary / Internal Use Only (modify as appropriate)

# Praxis SDK Agents

`BaseAgent` is a foundational agent implementation designed to be used in a modular Multi-Agent System (MAS) environment. It supports planning, execution, memory, intent recognition, and agent/tool coordination.

## Project Structure

```
agents/
├── agents/           # Base agent template
└── pyproject.toml        # Project configuration
```

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

## Requirements

* Python 3.10+
* [uv](https://astral.sh/uv) for dependency management
* Ray Serve
* Redis
* LightRAG and AI Registry services

## Installation

```bash
uv sync
```

## Running Tests

```bash
uv run pytest
```

## Development Setup

### Installing & Running Pre-commit

This repository uses pre-commit hooks to ensure code quality and consistency. Pre-commit automatically runs formatting, linting, and type checking before each commit.

#### Installation

1. **Install dependencies** (includes pre-commit, ruff, and mypy):
   ```bash
   uv sync --with dev
   ```

2. **Install pre-commit hooks**:
   ```bash
   uv run pre-commit install
   ```

3. **Optional: Install pre-push hooks** (recommended):
   ```bash
   uv run pre-commit install --hook-type pre-push
   ```

#### Usage

- **Automatic**: Pre-commit runs automatically on `git commit`
- **Manual**: Run on all files with:
  ```bash
  uv run pre-commit run --all-files
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

## Adding New Packages

The agent is intended to be deployed as part of a Ray Serve application and can be extended with custom workflows, tools, and domain knowledge.

To add a new agent package:
1. Create a new directory under `src/`
2. Follow the BaseAgent structure and patterns
3. Add tests under `tests/`
4. Update dependencies in `pyproject.toml` if needed

## Support

### Getting Help

If you need help or have questions about the Praxis SDK Agents:

- **GitHub Issues**: For bug reports and feature requests, please use our [issue templates](https://github.com/prxs-ai/praxis-sdk-agents/issues/new/choose)
- **GitHub Discussions**: For general questions and community discussions, visit our [discussions page](https://github.com/prxs-ai/praxis-sdk-agents/discussions)
- **Documentation**: Check our [contributing guide](docs/CONTRIBUTING.md) for development workflows

### Response Time

We aim to respond to issues and discussions within **48 hours** during business days. Please be patient as our maintainers are volunteers.

### Breaking Changes Policy

We follow semantic versioning and maintain backward compatibility:

- **MAJOR version bumps**: We will maintain backward compatibility for at least **6 months** before removing deprecated features
- **MINOR version bumps**: Only add new features, no breaking changes
- **PATCH version bumps**: Bug fixes and security updates only

All breaking changes will be clearly documented in our [CHANGELOG.md](CHANGELOG.md) and announced in advance.

## Maintainers

This project is maintained by:

- **Technical Lead**: [@hyp0cr4t](https://github.com/hyp0cr4t)
- **Primary Maintainer**: [@0xDevZip](https://github.com/0xDevZip)
- **Core Maintainer**: [@ruthuwjwb](https://github.com/ruthuwjwb)
- **Infrastructure Maintainer**: [@hexavor](https://github.com/hexavor)

### Maintainer Responsibilities

- Review and merge pull requests
- Triage and respond to issues
- Release new versions
- Maintain project roadmap and direction

### Becoming a Maintainer

We welcome new maintainers! If you're interested in helping maintain this project:

1. **Contribute regularly**: Submit quality PRs and help with issue triage
2. **Show commitment**: Demonstrate sustained involvement over 3+ months
3. **Express interest**: Reach out to existing maintainers via GitHub Discussions
4. **Onboarding**: Current maintainers will provide access and guidance

### Maintainer Rotation

- Maintainers may step down at any time by notifying the team
- Inactive maintainers (6+ months) will be asked about their continued involvement
- New maintainers require approval from at least 2 existing maintainers

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

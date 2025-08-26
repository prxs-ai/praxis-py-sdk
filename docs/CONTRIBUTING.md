# Contributing to Praxis Py SDK

Thank you for your interest in contributing to Praxis Py SDK!

## GitHub Flow

We use GitHub Flow for our development process. This is a lightweight, branch-based workflow that supports teams and projects where deployments are made regularly.

### Workflow Steps

1. **Create a branch**: Create a new branch from `main` for your feature or bugfix
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. **Make changes**: Develop your feature or fix, committing changes regularly
   ```bash
   git add .
   git commit -m "feat: add new feature" # or "fix: resolve issue"
   ```

3. **Push to GitHub**: Push your branch to the repository
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Open a Pull Request**: Create a PR from your branch to `main`
   - Use our PR template
   - Link related issues
   - Request reviews from maintainers

5. **Code Review**: Address feedback from reviewers
   - Make requested changes
   - Push additional commits
   - Respond to comments

6. **Merge**: Once approved and all checks pass, a maintainer will merge your PR

### Branch Naming Conventions

- `feature/` - for new features
- `fix/` - for bug fixes
- `docs/` - for documentation updates
- `chore/` - for maintenance tasks
- `refactor/` - for code refactoring

### Important Notes

- The `main` branch is protected and requires PR reviews
- All PRs must pass CI checks before merging
- Direct commits to `main` are not allowed

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a new branch for your feature
4. Make your changes
5. Submit a pull request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-username/praxis-py-sdk.git
cd praxis-py-sdk

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy .
```

## Code Style

- Follow PEP 8
- Use type hints where possible
- Write descriptive commit messages
- Add tests for new features

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the CHANGELOG.md with your changes
3. The PR will be merged once you have the sign-off of at least one maintainer
